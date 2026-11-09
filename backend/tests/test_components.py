"""Fast unit tests for the rule-based / lightweight components (no transformer models)."""
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from app.ml import duplicates, entities, rules, trends
from app.ml.preprocess import normalize, validate

NEG = {"sentiment": "negative", "frustration": 0.2}
HNEG = {"sentiment": "highly_negative", "frustration": 0.9}


def test_normalize_and_validate():
    assert normalize("<b>Hi</b>   there https://x.com  ok") == "Hi there ok"
    assert validate("") == "empty complaint text"
    assert validate("short") is not None
    assert validate("12345678901234") == "text has no words"
    assert validate("My order has not arrived yet") is None


def test_entities():
    e = entities.extract("I was charged ₹12,499 twice for order ORD-554210 in Chennai for my SmartWatch X2 on 5 Nov 2026.")
    assert e["order_ids"] == ["ORD-554210"]
    assert e["amounts"] == [12499.0]
    assert "Chennai" in e["locations"]
    assert e["products"] == ["SmartWatch X2"]
    assert e["dates"]


def test_entity_edge_cases():
    assert entities.extract("I placed 3 orders 15000 times over two years 12000")["amounts"] == []
    assert entities.extract("Paid Rs.2,500 and INR 300")["amounts"] == [2500.0, 300.0]
    assert entities.extract("Where is order no. 123456?")["order_ids"] == ["ORD-123456"]
    assert entities.extract("Where is order number 554210?")["order_ids"] == ["ORD-554210"]
    assert entities.extract("Order ORD-9876543210 is late")["phones"] == []


def test_keyword_rules_respect_context():
    neg = {"sentiment": "neutral", "frustration": 0}
    t = "This is not fraud, just a late delivery of my parcel."
    assert rules.route(t, "delivery", 0.9, "low")["department"] == "Logistics"
    t = "My Fire TV remote stopped pairing."
    assert not any("safety" in f["reason"] for f in rules.priority(t, "product", neg, {}, False)["priority_factors"])
    t = "I ordered today and want to change the address."
    assert rules.priority(t, "delivery", neg, {}, False)["priority"] == "low"


def test_priority_and_routing():
    text = "Unauthorized charge of ₹15000 on my card, fix it immediately or I go to my lawyer!"
    ents = entities.extract(text)
    p = rules.priority(text, "payment", HNEG, ents, repeat=True)
    assert p["priority"] == "critical"
    assert any("fraud" in f["reason"].lower() for f in p["priority_factors"])
    assert rules.route(text, "payment", 0.9, p["priority"])["department"] == "Fraud & Security"

    calm = "The app search returns no results."
    p2 = rules.priority(calm, "technical", {"sentiment": "neutral", "frustration": 0}, entities.extract(calm), False)
    assert p2["priority"] == "low"
    assert rules.route(calm, "technical", 0.95, "low")["department"] == "Technical Support"


def test_duplicates_rules():
    assert duplicates.is_duplicate(0.85, {"ORD-1"}, {"ORD-1"})
    assert not duplicates.is_duplicate(0.99, {"ORD-1"}, {"ORD-2"})
    assert not duplicates.is_duplicate(0.95, {"cust:a", "ORD-1"}, {"cust:a", "ORD-9"})
    assert duplicates.is_duplicate(0.85, {"cust:a", "ORD-1"}, {"cust:a"})
    assert duplicates.is_duplicate(0.9, set(), set())
    v = np.eye(3, dtype=np.float32)
    assert duplicates.find_match(v[0], set(), v[1:], [set(), set()]) is None
    assert duplicates.find_match(v[0], set(), v, [set()] * 3) == (0, 1.0)


def test_trend_spike_detected():
    end = datetime(2026, 11, 7)
    rows = [{"created_at": end - timedelta(days=d), "category": "delivery", "product": None, "location": "Pune"}
            for d in range(20) for _ in range(2)]
    rows += [{"created_at": end - timedelta(days=d), "category": "delivery", "product": None, "location": "Chennai"}
             for d in range(3) for _ in range(10)]
    alerts = trends.detect(pd.DataFrame(rows))
    assert ("location", "Chennai") in {(a["dimension"], a["value"]) for a in alerts}
    assert ("location", "Pune") not in {(a["dimension"], a["value"]) for a in alerts}
    # one future-dated row must not hide the spike
    future = pd.DataFrame([{"created_at": datetime(2030, 1, 1), "category": "delivery", "product": None, "location": "Pune"}])
    alerts = trends.detect(pd.concat([pd.DataFrame(rows), future]), now=end + timedelta(hours=1))
    assert ("location", "Chennai") in {(a["dimension"], a["value"]) for a in alerts}


def test_trend_needs_a_baseline():
    end = datetime(2026, 11, 7)
    rows = [{"created_at": end - timedelta(days=d), "category": "delivery", "product": None, "location": "Pune"}
            for d in range(3) for _ in range(3)]
    assert trends.detect(pd.DataFrame(rows), now=end) == []
