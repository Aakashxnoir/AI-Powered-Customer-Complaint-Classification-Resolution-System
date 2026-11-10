import io
import json
import os
from pathlib import Path
from collections import Counter, defaultdict
from contextlib import asynccontextmanager

import joblib
import numpy as np
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Request, UploadFile
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, Field
from sklearn.linear_model import LogisticRegression
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db import Complaint, Feedback, SessionLocal, init_db
from .ml import classifier, duplicates, resolver, rules, trends
from .ml.catalog import CATEGORIES, DEPARTMENTS
from .ml.preprocess import validate
from .pipeline import process

MAX_CSV_ROWS = 2000
MAX_CSV_BYTES = 5_000_000
MAX_ACCURACY_DROP = 0.01  # retrained model must stay within 1 point of the ORIGINAL model on the test set
ALLOWED = {
    "category": set(CATEGORIES),
    "priority": {lvl for _, lvl in rules.LEVELS},
    "sentiment": {"positive", "neutral", "negative", "highly_negative"},
    "department": set(DEPARTMENTS.values()) | {"Fraud & Security", "Product Safety"},
}


@asynccontextmanager
async def lifespan(_app):
    init_db()
    # Load every model once so the first complaint is not slow.
    from .ml import entities, sentiment
    classifier.predict(["warm up"])
    sentiment.analyse(["warm up"])
    entities.extract("warm up")
    yield


app = FastAPI(title="Complaint Intelligence API", lifespan=lifespan)
# ponytail: no auth and no CORS; the UI reaches /api through the Vite proxy (same origin).
# Put it behind SSO / a reverse proxy before real use.
# Local-only guards: refuse DNS-rebinding hosts, and refuse writes a foreign web page sends from the browser.
# Deployed: set ALLOWED_HOSTS to the public hostname(s), comma-separated.
app.add_middleware(TrustedHostMiddleware,
                   allowed_hosts=[h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()])
CONSOLE_ORIGINS = {"http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173", "http://127.0.0.1:4173"}


@app.middleware("http")
async def same_origin_writes(request: Request, call_next):
    origin = request.headers.get("origin")
    same_host = origin is not None and origin.split("://", 1)[-1] == request.headers.get("host")
    if request.method not in ("GET", "HEAD", "OPTIONS") and origin and origin not in CONSOLE_ORIGINS and not same_host:
        return JSONResponse({"detail": "cross-origin write refused"}, status_code=403)
    return await call_next(request)


def get_db():
    with SessionLocal() as db:
        yield db


def summary(c: Complaint) -> dict:
    return {k: getattr(c, k) for k in (
        "id", "text", "channel", "customer", "created_at", "category", "category_confidence", "sentiment",
        "priority", "priority_score", "department", "product", "location", "status", "reviewed",
        "duplicate_group", "duplicate_status")}


def detail(c: Complaint) -> dict:
    d = summary(c)
    d.update({k: getattr(c, k) for k in (
        "clean_text", "category_scores", "sentiment_confidence", "analysis", "priority_factors",
        "routing_reason", "entities", "duplicate_of", "duplicate_similarity", "draft", "final_response")})
    d.update(rules.urgency_severity(c.priority_factors))
    return d


def get_or_404(db, cid) -> Complaint:
    c = db.get(Complaint, cid)
    if not c:
        raise HTTPException(404, "complaint not found")
    return c


# ------------------------------------------------------------------ intake --
class ComplaintIn(BaseModel):
    text: str = Field(max_length=20_000)
    customer: str | None = Field(None, max_length=120)


@app.post("/api/complaints")
def create(body: ComplaintIn, db: Session = Depends(get_db)):
    if err := validate(body.text):
        raise HTTPException(422, err)
    [c] = process(db, [{"text": body.text, "customer": body.customer, "channel": "form"}])
    return detail(c)


@app.post("/api/complaints/upload")
async def upload(file: UploadFile, db: Session = Depends(get_db)):
    try:
        raw = await file.read(MAX_CSV_BYTES + 1)
        if len(raw) > MAX_CSV_BYTES:
            raise HTTPException(413, f"CSV larger than {MAX_CSV_BYTES // 1_000_000} MB")
        df = pd.read_csv(io.BytesIO(raw), dtype=str)  # str keeps IDs like 00123 / 12345 as typed
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"could not parse CSV: {e}")
    df.columns = [c.strip().lower() for c in df.columns]
    col = next((c for c in ("text", "complaint", "complaint_text", "description", "message") if c in df.columns), None)
    if col is None:
        raise HTTPException(422, f"CSV needs a 'text' (or complaint/description/message) column; got {list(df.columns)}")
    if len(df) > MAX_CSV_ROWS:
        raise HTTPException(422, f"max {MAX_CSV_ROWS} rows per upload")

    items, errors, seen = [], [], set()
    for i, row in df.iterrows():
        text = row[col] if pd.notna(row[col]) else ""
        if err := validate(text):
            errors.append({"row": int(i) + 2, "error": err})
            continue
        key = " ".join(str(text).lower().split())
        if key in seen:
            errors.append({"row": int(i) + 2, "error": "exact duplicate row in file (skipped)"})
            continue
        seen.add(key)
        created = pd.to_datetime(row.get("created_at"), errors="coerce") if "created_at" in df.columns else None
        items.append({"text": str(text), "channel": "csv",
                      "customer": str(row["customer"]).strip()[:120] if "customer" in df.columns and pd.notna(row["customer"]) else None,
                      "created_at": None if created is None or pd.isna(created) else created.to_pydatetime()})
    rows = process(db, items) if items else []
    return {"received": len(df), "processed": len(rows), "errors": errors,
            "by_category": Counter(r.category for r in rows), "by_priority": Counter(r.priority for r in rows),
            "duplicates_found": sum(1 for r in rows if r.duplicate_of), "ids": [r.id for r in rows]}


# ------------------------------------------------------------------- read ---
@app.get("/api/complaints")
def list_complaints(category: str | None = None, priority: str | None = None, status: str | None = None,
                    department: str | None = None, q: str | None = None,
                    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                    db: Session = Depends(get_db)):
    stmt = select(Complaint)
    for col, val in ((Complaint.category, category), (Complaint.priority, priority),
                     (Complaint.status, status), (Complaint.department, department)):
        if val:
            stmt = stmt.where(col == val)
    if q:
        q = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(Complaint.text.ilike(f"%{q}%", escape="\\"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(Complaint.created_at.desc()).limit(limit).offset(offset)).all()
    return {"total": total, "items": [summary(c) for c in rows]}


@app.get("/api/complaints/{cid}")
def get_complaint(cid: int, db: Session = Depends(get_db)):
    c = get_or_404(db, cid)
    d = detail(c)
    d["explanation"] = classifier.explain(c.clean_text, c.category)
    others = db.execute(select(Complaint.id, Complaint.embedding).where(Complaint.id != c.id)).all()
    if others:
        pool = np.stack([np.frombuffer(o.embedding, dtype=np.float32) for o in others])
        hits = duplicates.similar(np.frombuffer(c.embedding, dtype=np.float32), pool)
        rows = {x.id: x for x in db.scalars(select(Complaint).where(Complaint.id.in_([others[i].id for i, _ in hits])))}
        d["similar"] = [{**summary(rows[others[i].id]), "similarity": round(s, 3)} for i, s in hits]
    if c.duplicate_group:
        d["duplicates"] = [summary(x) for x in db.scalars(
            select(Complaint).where(Complaint.duplicate_group == c.duplicate_group, Complaint.id != c.id))]
    return d


@app.get("/api/stats")
def stats(db: Session = Depends(get_db)):
    def count(col):
        return dict(db.execute(select(col, func.count()).group_by(col)).all())
    return {"total": db.scalar(select(func.count(Complaint.id))), "by_category": count(Complaint.category),
            "by_priority": count(Complaint.priority), "by_sentiment": count(Complaint.sentiment),
            "by_department": count(Complaint.department), "by_status": count(Complaint.status),
            "pending_duplicates": db.scalar(select(func.count()).where(Complaint.duplicate_status == "pending"))}


# ------------------------------------------------------- review & feedback --
class Review(BaseModel):
    field: str           # category / priority / department / sentiment
    value: str
    comment: str | None = None


@app.post("/api/complaints/{cid}/review")
def review(cid: int, body: Review, db: Session = Depends(get_db)):
    if body.field not in ALLOWED:
        raise HTTPException(422, "invalid field")
    if body.value not in ALLOWED[body.field]:
        raise HTTPException(422, f"invalid {body.field}: {body.value!r}")
    c = get_or_404(db, cid)
    predicted = c.analysis.get("original", {}).get(body.field, getattr(c, body.field))
    previous = getattr(c, body.field)
    setattr(c, body.field, body.value)
    # Follow the new category only if the department was still the default for the previous one.
    if body.field == "category" and c.department == DEPARTMENTS.get(previous):
        c.department = DEPARTMENTS[body.value]
    c.reviewed = True
    db.add(Feedback(complaint_id=cid, field=body.field, predicted=predicted, corrected=body.value, comment=body.comment))
    db.commit()
    return detail(c)


@app.post("/api/complaints/{cid}/draft")
def make_draft(cid: int, db: Session = Depends(get_db)):
    c = get_or_404(db, cid)
    c.draft = resolver.draft({"text": c.clean_text, "category": c.category, "priority": c.priority,
                              "sentiment": c.sentiment, "entities": c.entities})
    db.commit()
    return c.draft


class Decision(BaseModel):
    action: str          # approve / reject
    text: str | None = None
    comment: str | None = None


@app.post("/api/complaints/{cid}/response")
def decide_response(cid: int, body: Decision, db: Session = Depends(get_db)):
    c = get_or_404(db, cid)
    if not c.draft:
        raise HTTPException(409, "generate a draft first")
    if c.status != "new":
        raise HTTPException(409, f"response already {c.status}")
    if body.action == "approve":
        if body.text is not None and not body.text.strip():
            raise HTTPException(422, "response text is empty")
        edited = body.text is not None and body.text.strip() != c.draft["response"].strip()
        c.final_response, c.status = body.text.strip() if edited else c.draft["response"], "approved"
        outcome = "edited" if edited else "approved"
    elif body.action == "reject":
        c.status, outcome = "rejected", "rejected"
    else:
        raise HTTPException(422, "action must be approve or reject")
    db.add(Feedback(complaint_id=cid, field="response", predicted=c.draft.get("generator", ""),
                    corrected=outcome, comment=body.comment))
    db.commit()
    return detail(c)


# -------------------------------------------------------------- duplicates --
@app.get("/api/duplicates")
def duplicate_groups(status: str = "pending", db: Session = Depends(get_db)):
    groups = db.scalars(select(Complaint.duplicate_group).where(
        Complaint.duplicate_status == status, Complaint.duplicate_group.is_not(None)).distinct()).all()
    out = []
    for g in groups:
        members = db.scalars(select(Complaint).where(Complaint.duplicate_group == g).order_by(Complaint.created_at)).all()
        out.append({"group": g, "members": [{**summary(m), "duplicate_of": m.duplicate_of,
                                             "similarity": m.duplicate_similarity} for m in members]})
    return sorted(out, key=lambda x: -len(x["members"]))


class DupDecision(BaseModel):
    complaint_id: int
    decision: str        # confirm / reject


@app.post("/api/duplicates/resolve")
def resolve_duplicate(body: DupDecision, db: Session = Depends(get_db)):
    c = get_or_404(db, body.complaint_id)
    if body.decision not in ("confirm", "reject"):
        raise HTTPException(422, "decision must be confirm or reject")
    if c.duplicate_status != "pending":
        raise HTTPException(409, "complaint is not a pending duplicate")
    c.duplicate_status = "confirmed" if body.decision == "confirm" else "rejected"
    if body.decision == "reject":
        group, c.duplicate_group, c.duplicate_of = c.duplicate_group, None, None
        # The repeat-complaint points came from the rejected match; take them back.
        c.priority_factors = [f for f in c.priority_factors if not f["reason"].startswith("Repeat complaint")] \
            or [{"points": 0, "reason": "No risk factors detected"}]
        c.priority_score = sum(f["points"] for f in c.priority_factors)
        c.priority = rules.level(c.priority_score)
        db.flush()
        left = db.scalars(select(Complaint).where(Complaint.duplicate_group == group)).all()
        if len(left) == 1:  # only the root is left: dissolve the group
            left[0].duplicate_group = None
    db.add(Feedback(complaint_id=c.id, field="duplicate", predicted="duplicate", corrected=c.duplicate_status))
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ trends --
@app.get("/api/trends")
def get_trends(db: Session = Depends(get_db)):
    df = pd.read_sql(select(Complaint.created_at, Complaint.category, Complaint.product, Complaint.location,
                            Complaint.priority), db.bind)
    if df.empty:
        return {"alerts": [], "daily": [], "by_category": [], "top_products": {}, "top_locations": {}}
    df["created_at"] = pd.to_datetime(df.created_at)
    return {
        "alerts": trends.detect(df),
        "daily": trends.daily_series(df),
        "by_category": trends.daily_series(df, "category"),
        "top_products": df["product"].value_counts().head(8).to_dict(),
        "top_locations": df["location"].value_counts().head(10).to_dict(),
    }


# -------------------------------------------------------------- evaluation --
@app.get("/api/evaluation")
def evaluation(db: Session = Depends(get_db)):
    offline = {}
    for name in ("classifier_metrics", "evaluation"):
        p = classifier.ARTIFACTS / f"{name}.json"
        if p.exists():
            offline[name] = json.loads(p.read_text())

    fb = db.scalars(select(Feedback).order_by(Feedback.id)).all()
    latest = {(f.complaint_id, f.field): f for f in fb}  # a re-review replaces the earlier verdict
    fields = defaultdict(lambda: {"reviewed": 0, "corrected": 0})
    confusion = Counter()
    per_cat = defaultdict(lambda: {"reviewed": 0, "correct": 0})
    per_value = defaultdict(lambda: {"reviewed": 0, "correct": 0})
    responses = Counter()
    for f in latest.values():
        if f.field == "response":
            responses[f.corrected] += 1
            continue
        if f.field == "duplicate":
            fields["duplicate"]["reviewed"] += 1
            fields["duplicate"]["corrected"] += f.corrected == "rejected"
            continue
        fields[f.field]["reviewed"] += 1
        fields[f.field]["corrected"] += f.predicted != f.corrected
        per_value[(f.field, f.predicted)]["reviewed"] += 1
        per_value[(f.field, f.predicted)]["correct"] += f.predicted == f.corrected
        if f.field == "category":
            confusion[(f.predicted, f.corrected)] += 1
            per_cat[f.predicted]["reviewed"] += 1
            per_cat[f.predicted]["correct"] += f.predicted == f.corrected
    for v in fields.values():
        v["accuracy"] = round(1 - v["corrected"] / v["reviewed"], 3) if v["reviewed"] else None
    for v in (*per_cat.values(), *per_value.values()):
        v["accuracy"] = round(v["correct"] / v["reviewed"], 3)
    weak = sorted(((k, v) for k, v in per_value.items() if v["reviewed"] >= 2), key=lambda kv: kv[1]["accuracy"])
    low_conf = db.scalar(select(func.count()).where(Complaint.category_confidence < 0.6))
    total = db.scalar(select(func.count(Complaint.id))) or 1
    return {
        "offline": offline,
        "feedback": {
            "total": len(latest), "fields": fields, "category_by_predicted": per_cat,
            "confusion": [{"predicted": p, "corrected": c, "count": n} for (p, c), n in confusion.items()],
            "responses": responses,
            "weak_spots": [{"field": fld, "value": val, **v} for (fld, val), v in weak if v["accuracy"] < 0.9],
            "low_confidence_share": round(low_conf / total, 3),
            "recent_corrections": [{"complaint_id": f.complaint_id, "field": f.field, "predicted": f.predicted,
                                    "corrected": f.corrected, "comment": f.comment}
                                   for f in [f for f in fb if f.field not in ("response", "duplicate")
                                             and f.predicted != f.corrected][-10:][::-1]],
        },
    }


@app.post("/api/model/retrain")
def retrain(db: Session = Depends(get_db)):
    """Refit the classifier on the original training embeddings plus reviewer-corrected
    complaints (weighted x3). Deploy only if held-out test accuracy does not drop."""
    data = np.load(classifier.ARTIFACTS / "train_embeddings.npz", allow_pickle=True)
    latest = {}
    for f in db.scalars(select(Feedback).where(Feedback.field == "category").order_by(Feedback.id)):
        latest[f.complaint_id] = f.corrected
    ids = [i for i, lab in latest.items() if lab in CATEGORIES]
    if not ids:
        raise HTTPException(409, "no category feedback to learn from yet")
    rows = {c.id: c for c in db.scalars(select(Complaint).where(Complaint.id.in_(ids)))}
    Xf = np.stack([np.frombuffer(rows[i].embedding, dtype=np.float32) for i in ids])
    yf = np.array([latest[i] for i in ids])
    X, y = np.vstack([data["X"], Xf]), np.concatenate([data["y"], yf])
    w = np.concatenate([np.ones(len(data["y"])), np.full(len(yf), 3.0)])
    # Gate against the ORIGINAL model, so repeated retrains cannot each shave off a point.
    # ponytail: the gate reuses the offline test set; a separate gate split would be stricter.
    before = float((joblib.load(classifier.MODEL_PATH).predict(data["X_test"]) == data["y_test"]).mean())
    clf = LogisticRegression(C=float(data["C"]), max_iter=3000, class_weight="balanced").fit(X, y, sample_weight=w)
    after = float((clf.predict(data["X_test"]) == data["y_test"]).mean())
    deployed = after >= before - MAX_ACCURACY_DROP  # guard against bad / adversarial feedback
    if deployed:
        joblib.dump(clf, classifier.RETRAINED_PATH)
        classifier.reload()
    return {"feedback_examples": len(ids), "test_accuracy_before": round(before, 4),
            "test_accuracy_after": round(after, 4), "deployed": deployed}


@app.get("/api/health")
def health():
    import os
    return {"ok": True, "llm": resolver.MODEL if os.environ.get("GEMINI_API_KEY") else "template-fallback"}


# Production: serve the built frontend (landing at /, console at /app) from the same origin as the API.
DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


class SPA(StaticFiles):
    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as e:
            if e.status_code == 404 and (path == "app" or path.startswith("app/")) and "." not in path:
                return await super().get_response("app/index.html", scope)
            raise


if DIST.is_dir():
    app.mount("/", SPA(directory=DIST, html=True), name="web")
