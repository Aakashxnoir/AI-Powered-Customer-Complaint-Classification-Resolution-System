"""API tests on a throwaway SQLite DB. Rows are inserted directly, so no transformer
models load (TestClient without `with` skips the startup warm-up)."""
import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ.pop("GEMINI_API_KEY", None)

from unittest.mock import patch  # noqa: E402

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, Complaint, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.ml import resolver  # noqa: E402

client = TestClient(app, base_url="http://localhost")


def make(db, **kw):
    row = dict(text="My parcel never arrived at all", clean_text="My parcel never arrived at all", channel="form",
               category="delivery", category_confidence=0.9, category_scores={}, sentiment="negative",
               sentiment_confidence=0.9, analysis={"original": {"category": kw.get("category", "delivery")}},
               priority="medium", priority_score=3,
               priority_factors=[{"points": 1, "reason": "Negative sentiment"},
                                 {"points": 2, "reason": "Repeat complaint (similar complaint already logged)"}],
               department="Logistics", routing_reason="x", entities={}, embedding=np.zeros(384, np.float32).tobytes())
    row.update(kw)
    c = Complaint(**row)
    db.add(c)
    db.flush()
    return c


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def test_duplicates_list_ignores_ungrouped():
    with SessionLocal() as db:
        root = make(db)
        dup = make(db, duplicate_of=root.id, duplicate_status="pending")
        root.duplicate_group = dup.duplicate_group = root.id
        make(db)  # unrelated complaint
        db.commit()
        dup_id = dup.id
    assert client.post("/api/duplicates/resolve", json={"complaint_id": dup_id, "decision": "reject"}).status_code == 200
    groups = client.get("/api/duplicates?status=rejected").json()
    assert all(g["group"] is not None for g in groups)


def test_reject_duplicate_clears_link_repeat_points_and_empty_group():
    with SessionLocal() as db:
        root = make(db)
        dup = make(db, duplicate_of=root.id, duplicate_status="pending")
        root.duplicate_group = dup.duplicate_group = root.id
        db.commit()
        root_id, dup_id = root.id, dup.id
    client.post("/api/duplicates/resolve", json={"complaint_id": dup_id, "decision": "reject"})
    with SessionLocal() as db:
        d, r = db.get(Complaint, dup_id), db.get(Complaint, root_id)
        assert d.duplicate_of is None and d.duplicate_group is None
        assert d.priority_score == 1 and d.priority == "low"
        assert not any(f["reason"].startswith("Repeat") for f in d.priority_factors)
        assert r.duplicate_group is None


def test_resolve_only_pending_duplicates():
    with SessionLocal() as db:
        cid = make(db).id
        db.commit()
    assert client.post("/api/duplicates/resolve", json={"complaint_id": cid, "decision": "confirm"}).status_code == 409


def test_second_category_correction_keeps_department_in_sync():
    with SessionLocal() as db:
        cid = make(db, category="refund", department="Refunds & Returns",
                   analysis={"original": {"category": "refund"}}).id
        db.commit()
    client.post(f"/api/complaints/{cid}/review", json={"field": "category", "value": "delivery"})
    body = client.post(f"/api/complaints/{cid}/review", json={"field": "category", "value": "refund"}).json()
    assert body["department"] == "Refunds & Returns"


def test_review_rejects_unknown_values():
    with SessionLocal() as db:
        cid = make(db).id
        db.commit()
    assert client.post(f"/api/complaints/{cid}/review", json={"field": "priority", "value": "banana"}).status_code == 422
    assert client.post(f"/api/complaints/{cid}/review", json={"field": "category", "value": "nope"}).status_code == 422


def test_gemini_reply_without_response_falls_back_to_template():
    os.environ["GEMINI_API_KEY"] = "test"
    try:
        with patch.object(resolver, "_call_gemini", return_value={"next_action": "x"}), \
             patch.object(resolver, "retrieve", return_value=[{"id": "delivery-delayed", "title": "t", "category": "delivery",
                                                               "next_action": "n", "body": "Do X.", "score": 0.9}]):
            d = resolver.draft({"text": "late", "category": "delivery", "priority": "low", "sentiment": "neutral", "entities": {}})
    finally:
        os.environ.pop("GEMINI_API_KEY")
    assert d["generator"] == "template" and "Do X." in d["response"] and "llm_error" in d


def test_gemini_used_guidance_limited_to_retrieved_docs():
    os.environ["GEMINI_API_KEY"] = "test"
    try:
        with patch.object(resolver, "_call_gemini", return_value={"response": "ok", "used_guidance": ["delivery-delayed", "made-up"]}), \
             patch.object(resolver, "retrieve", return_value=[{"id": "delivery-delayed", "title": "t", "category": "delivery",
                                                               "next_action": "n", "body": "b", "score": 0.9}]):
            d = resolver.draft({"text": "late", "category": "delivery", "priority": "low", "sentiment": "neutral", "entities": {}})
    finally:
        os.environ.pop("GEMINI_API_KEY")
    assert d["used_guidance"] == ["delivery-delayed"]


def test_response_decisions():
    with SessionLocal() as db:
        cid = make(db, draft={"response": "Hello", "generator": "template"}).id
        db.commit()
    assert client.post(f"/api/complaints/{cid}/response", json={"action": "approve", "text": "   "}).status_code == 422
    assert client.post(f"/api/complaints/{cid}/response", json={"action": "approve"}).json()["final_response"] == "Hello"
    assert client.post(f"/api/complaints/{cid}/response", json={"action": "reject"}).status_code == 409


def test_evaluation_counts_latest_review_once_and_skips_non_corrections():
    with SessionLocal() as db:
        cid = make(db, draft={"response": "Hello", "generator": "template"}).id
        db.commit()
    client.post(f"/api/complaints/{cid}/review", json={"field": "category", "value": "refund"})
    client.post(f"/api/complaints/{cid}/review", json={"field": "category", "value": "delivery"})
    client.post(f"/api/complaints/{cid}/response", json={"action": "approve"})
    fb = client.get("/api/evaluation").json()["feedback"]
    assert fb["fields"]["category"]["reviewed"] == 1 and fb["fields"]["category"]["corrected"] == 0
    assert all(r["field"] not in ("response", "duplicate") for r in fb["recent_corrections"])


def test_list_limits_and_literal_search():
    with SessionLocal() as db:
        make(db, text="100% broken")
        make(db, text="fine")
        db.commit()
    assert client.get("/api/complaints?limit=100000").status_code == 422
    assert client.get("/api/complaints", params={"q": "%"}).json()["total"] == 1


def test_detail_survives_category_outside_model():
    with SessionLocal() as db:
        cid = make(db, category="legacy").id
        db.commit()
    assert client.get(f"/api/complaints/{cid}").status_code == 200


def test_urgency_and_severity_scores_in_detail():
    with SessionLocal() as db:
        cid = make(db, priority_factors=[{"points": 4, "reason": "Possible fraud / unauthorised access"},
                                         {"points": 2, "reason": "Customer states urgency"}]).id
        db.commit()
    with patch("app.main.classifier.explain", return_value=[]):
        d = client.get(f"/api/complaints/{cid}").json()
    assert 0 < d["urgency"]["score"] <= 1 and 0 < d["severity"]["score"] <= 1


def test_local_only_guards():
    assert TestClient(app, base_url="http://rebind.attacker.example").get("/api/health").status_code == 400
    r = client.post("/api/model/retrain", headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
    assert client.post("/api/model/retrain", headers={"Origin": "http://localhost:5173"}).status_code == 409  # no feedback yet


def test_huge_text_rejected_before_regex():
    import time
    from app.ml.preprocess import validate
    t = time.perf_counter()
    assert validate("<" * 160_000) is not None
    assert time.perf_counter() - t < 0.5
