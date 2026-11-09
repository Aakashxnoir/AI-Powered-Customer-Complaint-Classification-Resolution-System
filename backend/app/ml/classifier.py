"""Complaint category classifier: MiniLM sentence embeddings + logistic regression.

Explanations use word occlusion: drop each word, re-score, and report how much the
predicted class probability falls. Model-agnostic and faithful to the real model.
"""
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

from .embeddings import embed

ARTIFACTS = Path(__file__).resolve().parents[2] / "artifacts"
MODEL_PATH = ARTIFACTS / "classifier.joblib"                 # trained by ml/train.py (tracked)
RETRAINED_PATH = ARTIFACTS / "classifier_retrained.joblib"   # written by /api/model/retrain (git-ignored)


@lru_cache
def load():
    return joblib.load(RETRAINED_PATH if RETRAINED_PATH.exists() else MODEL_PATH)


def reload():
    load.cache_clear()


def predict(texts: list[str], vectors: np.ndarray | None = None) -> list[dict]:
    clf = load()
    vectors = embed(texts) if vectors is None else vectors
    probs = clf.predict_proba(vectors)
    out = []
    for p in probs:
        i = int(np.argmax(p))
        out.append({"category": clf.classes_[i], "confidence": float(p[i]),
                    "scores": {c: round(float(s), 4) for c, s in zip(clf.classes_, p)}})
    return out


def explain(text: str, category: str, top_k: int = 6) -> list[dict]:
    """Words whose removal most reduces the probability of `category`."""
    clf = load()
    if category not in clf.classes_:
        return []
    words = text.split()
    if len(words) > 80:  # keep latency bounded
        words = words[:80]
    ci = list(clf.classes_).index(category)
    variants = [" ".join(words)] + [" ".join(words[:i] + words[i + 1:]) for i in range(len(words))]
    probs = clf.predict_proba(embed(variants))[:, ci]
    base = probs[0]
    impact = [(words[i], float(base - probs[i + 1])) for i in range(len(words))]
    impact.sort(key=lambda x: -x[1])
    return [{"word": w.strip(".,!?"), "impact": round(v, 4)} for w, v in impact[:top_k] if v > 0]
