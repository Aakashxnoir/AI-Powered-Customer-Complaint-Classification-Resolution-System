"""Train the category classifier.

Compares a TF-IDF + LogisticRegression baseline with MiniLM embeddings +
LogisticRegression, tunes C on the validation split, reports both on the test
split, and saves the embedding model (used by the app) plus cached training
embeddings (used for fast retraining with reviewer feedback).
"""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.ml.catalog import CATEGORIES  # noqa: E402
from app.ml.embeddings import embed  # noqa: E402

DATA = ROOT / "data" / "processed"
ART = ROOT / "backend" / "artifacts"


def report(y, pred):
    return {
        "accuracy": round(accuracy_score(y, pred), 4),
        "macro_f1": round(f1_score(y, pred, average="macro"), 4),
        "per_class": {k: {m: round(v, 4) for m, v in d.items()}
                      for k, d in classification_report(y, pred, output_dict=True).items() if k in CATEGORIES},
        "confusion_matrix": {"labels": CATEGORIES, "matrix": confusion_matrix(y, pred, labels=CATEGORIES).tolist()},
    }


def best_c(make, Xtr, ytr, Xva, yva):
    scores = {c: f1_score(yva, make(c).fit(Xtr, ytr).predict(Xva), average="macro") for c in [0.3, 1, 3, 10, 30]}
    return max(scores, key=scores.get), scores


def main():
    ART.mkdir(exist_ok=True)
    tr, va, te = (pd.read_csv(DATA / f"{s}.csv") for s in ["train", "val", "test"])
    results = {"splits": {s: len(d) for s, d in zip(["train", "val", "test"], [tr, va, te])}}

    # Baseline: TF-IDF + LR
    mk_tfidf = lambda c: make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),  # noqa: E731
                                       LogisticRegression(C=c, max_iter=2000, class_weight="balanced"))
    c, _ = best_c(mk_tfidf, tr.text, tr.category, va.text, va.category)
    base = mk_tfidf(c).fit(tr.text, tr.category)
    results["tfidf_logreg"] = {"C": c, **report(te.category, base.predict(te.text))}
    print("TF-IDF test", results["tfidf_logreg"]["accuracy"], results["tfidf_logreg"]["macro_f1"])

    # Main: MiniLM embeddings + LR
    Etr, Eva, Ete = embed(tr.text.tolist()), embed(va.text.tolist()), embed(te.text.tolist())
    mk_lr = lambda c: LogisticRegression(C=c, max_iter=3000, class_weight="balanced")  # noqa: E731
    c, _ = best_c(mk_lr, Etr, tr.category, Eva, va.category)
    clf = mk_lr(c).fit(np.vstack([Etr, Eva]), pd.concat([tr.category, va.category]))
    pred = clf.predict(Ete)
    results["minilm_logreg"] = {"C": c, **report(te.category, pred)}
    print("MiniLM test", results["minilm_logreg"]["accuracy"], results["minilm_logreg"]["macro_f1"])

    # Per-source breakdown (synthetic held-out templates vs real-style Bitext text)
    results["minilm_by_source"] = {
        src: round(accuracy_score(te.category[te.source == src], pred[te.source == src]), 4)
        for src in te.source.unique()}

    # Sample predictions (incl. errors) for the report
    probs = clf.predict_proba(Ete).max(1)
    te = te.assign(predicted=pred, confidence=probs.round(3))
    wrong = te[te.category != te.predicted].head(8)
    right = te[te.category == te.predicted].sample(8, random_state=1)
    results["samples"] = pd.concat([right, wrong])[["text", "category", "predicted", "confidence", "source"]].to_dict("records")

    joblib.dump(clf, ART / "classifier.joblib")
    np.savez_compressed(ART / "train_embeddings.npz", X=np.vstack([Etr, Eva]),
                        y=np.array(pd.concat([tr.category, va.category])), C=c,
                        X_test=Ete, y_test=np.array(te.category))
    (ART / "classifier_metrics.json").write_text(json.dumps(results, indent=2))
    print("saved", ART)


if __name__ == "__main__":
    main()
