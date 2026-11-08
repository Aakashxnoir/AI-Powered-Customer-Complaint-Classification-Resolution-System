"""Runs every model over a batch of complaints and stores the results."""
from datetime import datetime

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Complaint
from .ml import classifier, duplicates, entities, rules, sentiment
from .ml.embeddings import embed
from .ml.preprocess import normalize


def _pool(db: Session):
    rows = db.execute(select(Complaint.id, Complaint.embedding, Complaint.entities, Complaint.customer, Complaint.duplicate_group)).all()
    vecs = np.stack([np.frombuffer(r.embedding, dtype=np.float32) for r in rows]) if rows else np.zeros((0, 384), np.float32)
    return rows, vecs, [duplicates.identity_keys(r.entities, r.customer) for r in rows]


def process(db: Session, items: list[dict]) -> list[Complaint]:
    """items: [{"text", "channel", "customer", "created_at"}] -> stored Complaint rows."""
    texts = [normalize(i["text"]) for i in items]
    vecs = embed(texts)
    cls = classifier.predict(texts, vecs)
    sent = sentiment.analyse(texts)
    ents = entities.extract_many(texts)
    rows, pool_vecs, pool_keys = _pool(db)
    pool_ids = [r.id for r in rows]
    pool_groups = [r.duplicate_group for r in rows]

    out = []
    for item, text, vec, c, s, e in zip(items, texts, vecs, cls, sent, ents):
        keys = duplicates.identity_keys(e, item.get("customer"))
        match = duplicates.find_match(vec, keys, pool_vecs, pool_keys)
        pr = rules.priority(text, c["category"], s, e, repeat=match is not None)
        rt = rules.route(text, c["category"], c["confidence"], pr["priority"])
        row = Complaint(
            text=item["text"], clean_text=text, channel=item.get("channel", "form"),
            customer=item.get("customer"), created_at=item.get("created_at") or datetime.now(),
            category=c["category"], category_confidence=c["confidence"], category_scores=c["scores"],
            sentiment=s["sentiment"], sentiment_confidence=s["sentiment_confidence"],
            analysis={**{k: s[k] for k in ("sentiment_scores", "emotion", "emotion_scores", "frustration", "intensity_markers")},
                      "original": {"category": c["category"], "priority": pr["priority"],
                                   "department": rt["department"], "sentiment": s["sentiment"]}},
            **pr, **rt, entities=e,
            product=(e["products"] or [None])[0], location=(e["locations"] or [None])[0],
            embedding=vec.tobytes(),
        )
        db.add(row)
        db.flush()
        if match:
            idx, sim = match
            group = pool_groups[idx] or pool_ids[idx]
            if pool_groups[idx] is None:  # first duplicate: original becomes group root
                orig = db.get(Complaint, pool_ids[idx])
                orig.duplicate_group = group
                pool_groups[idx] = group
            row.duplicate_group, row.duplicate_of = group, pool_ids[idx]
            row.duplicate_similarity, row.duplicate_status = round(sim, 4), "pending"
        # newly stored complaint joins the pool for the rest of the batch
        pool_vecs = np.vstack([pool_vecs, vec[None]])
        pool_keys.append(keys)
        pool_ids.append(row.id)
        pool_groups.append(row.duplicate_group)
        out.append(row)
    db.commit()
    return out
