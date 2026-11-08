"""Evaluate the non-classifier components and write backend/artifacts/evaluation.json.

- Sentiment: 4-level labels vs the tone used to generate synthetic test complaints
- Entities: order ID / product / amount / location vs generator ground truth
- Duplicates: precision/recall on the injected near-duplicates in the live stream
- Trends: whether the injected spikes are detected (and any false alarms)
- Priority: distribution and sample factor explanations
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.ml import duplicates, entities, rules, sentiment, trends  # noqa: E402
from app.ml.embeddings import embed  # noqa: E402

DATA = ROOT / "data" / "processed"
ART = ROOT / "backend" / "artifacts"
LABELS = ["positive", "neutral", "negative", "highly_negative"]


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": round(p, 4), "recall": round(r, 4),
            "f1": round(2 * p * r / (p + r), 4) if p + r else 0.0, "support": tp + fn}


def eval_sentiment(te):
    s = te[te.source == "synthetic"].sample(500, random_state=0)
    preds = sentiment.analyse(s.text.tolist())
    y, p = s.sentiment_label.tolist(), [x["sentiment"] for x in preds]
    # Coarse 3-way view (highly_negative folded into negative)
    fold = lambda v: "negative" if v == "highly_negative" else v  # noqa: E731
    return {
        "n": len(s), "accuracy": round(accuracy_score(y, p), 4), "macro_f1": round(f1_score(y, p, average="macro"), 4),
        "accuracy_3class": round(accuracy_score([fold(v) for v in y], [fold(v) for v in p]), 4),
        "per_class": {k: {m: round(v, 4) for m, v in d.items()}
                      for k, d in classification_report(y, p, output_dict=True, zero_division=0).items() if k in LABELS},
        "confusion_matrix": {"labels": LABELS, "matrix": confusion_matrix(y, p, labels=LABELS).tolist()},
    }, s.assign(pred=p), preds


def eval_entities(te):
    s = te[te.source == "synthetic"]
    ext = entities.extract_many(s.text.tolist())
    fields = {"order_id": "order_ids", "product": "products", "amount": "amounts", "location": "locations"}
    out = {}
    for gold_col, key in fields.items():
        tp = fp = fn = 0
        for gold, e in zip(s[gold_col].fillna(""), ext):
            gold = str(gold)
            pred = [str(int(v)) if isinstance(v, float) else v for v in e[key]]
            g = {gold} if gold and gold != "nan" else set()
            if key == "amounts":
                g = {str(int(float(x))) for x in g}
            tp += len(g & set(pred))
            fp += len(set(pred) - g)
            fn += len(g - set(pred))
        out[gold_col] = prf(tp, fp, fn)
    return out


def eval_duplicates(live):
    vecs = embed(live.text.tolist())
    ext = entities.extract_many(live.text.tolist())
    orders = [duplicates.identity_keys(e, c) for e, c in zip(ext, live.customer)]
    pred = {}
    for i in range(len(live)):
        m = duplicates.find_match(vecs[i], orders[i], vecs[:i], orders[:i])
        if m:
            pred[i] = m[0]
    pos = {i: int(d) for i, d in enumerate(live.duplicate_of) if d >= 0}
    # live rows are re-indexed by time order; map original row_id -> position
    pos_by_row = {r: i for i, r in enumerate(live.row_id)}
    gold = {i: pos_by_row[d] for i, d in pos.items() if d in pos_by_row}
    tp = sum(1 for i, j in pred.items() if gold.get(i) == j)
    sweep = {}
    for th in [0.5, 0.6, 0.7, 0.8, 0.9]:  # threshold for complaints sharing a customer / order
        old, duplicates.SAME_ORDER_SIM = duplicates.SAME_ORDER_SIM, th
        pr = {i: m[0] for i in range(len(live))
              if (m := duplicates.find_match(vecs[i], orders[i], vecs[:i], orders[:i]))}
        duplicates.SAME_ORDER_SIM = old
        t = sum(1 for i, j in pr.items() if gold.get(i) == j)
        sweep[str(th)] = prf(t, len(pr) - t, len(gold) - t)
    return {"pairs_in_stream": len(gold), "predicted_pairs": len(pred), **prf(tp, len(pred) - tp, len(gold) - tp),
            "threshold_same_identity": duplicates.SAME_ORDER_SIM, "threshold_sweep": sweep}


def eval_trends(live):
    ext = entities.extract_many(live.text.tolist())
    df = pd.DataFrame({"created_at": pd.to_datetime(live.created_at), "category": live.category,
                       "product": [(e["products"] or [None])[0] for e in ext],
                       "location": [(e["locations"] or [None])[0] for e in ext]})
    alerts = trends.detect(df)
    # The injected Chennai-delivery and SmartWatch-defect spikes also raise their categories.
    expected = {("location", "Chennai"), ("product", "SmartWatch X2"), ("category", "delivery"), ("category", "product")}
    found = {(a["dimension"], a["value"]) for a in alerts}
    return {"expected_spikes": sorted(map(list, expected)), "detected": alerts,
            "recall": len(expected & found) / len(expected), "false_alarms": sorted(map(list, found - expected))}


def main():
    te = pd.read_csv(DATA / "test.csv")
    live = pd.read_csv(DATA / "live_complaints.csv").sort_values("created_at").reset_index(drop=True)
    res = {}
    res["sentiment"], s, preds = eval_sentiment(te)
    print("sentiment", res["sentiment"]["accuracy"], res["sentiment"]["accuracy_3class"])
    res["entities"] = eval_entities(te)
    print("entities", res["entities"])
    res["duplicates"] = eval_duplicates(live)
    print("duplicates", {k: res["duplicates"][k] for k in ("precision", "recall", "f1")})
    res["trends"] = eval_trends(live)
    print("trends recall", res["trends"]["recall"], "false alarms", res["trends"]["false_alarms"])

    ents = entities.extract_many(s.text.tolist())
    pri = [rules.priority(t, c, p, e, repeat=False) for t, c, p, e in zip(s.text, s.category, preds, ents)]
    res["priority"] = {"distribution": pd.Series([p["priority"] for p in pri]).value_counts().to_dict(),
                       "samples": [{"text": t, **p} for t, p in list(zip(s.text, pri))[:5]]}
    res["sentiment_samples"] = s[["text", "sentiment_label", "pred"]].head(8).to_dict("records")
    (ART / "evaluation.json").write_text(json.dumps(res, indent=2, default=lambda o: o.item() if isinstance(o, np.generic) else str(o)))
    print("saved", ART / "evaluation.json")


if __name__ == "__main__":
    main()
