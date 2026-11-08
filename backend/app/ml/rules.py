"""Business rules: priority scoring and department routing. Every point of score
and every routing decision carries a human-readable reason."""
import re

from .catalog import DEPARTMENTS

FRAUD_RE = re.compile(r"\b(unauthori[sz]ed|fraud|without my (permission|knowledge)|hacked|someone else logged|scam)\b", re.I)
SAFETY_RE = re.compile(r"\b(overheat\w*|burning|smoke|fire|shock|explod\w*)\b", re.I)
URGENT_RE = re.compile(r"\b(urgent|immediately|asap|today|right now|emergency)\b", re.I)
LEGAL_RE = re.compile(r"\b(lawyer|legal action|consumer (court|complaint|forum))\b", re.I)
HIGH_AMOUNT = 10000

LEVELS = [(8, "critical"), (5, "high"), (3, "medium"), (0, "low")]


def priority(text: str, category: str, sentiment: dict, entities: dict, repeat: bool) -> dict:
    factors = []

    def add(points, reason):
        factors.append({"points": points, "reason": reason})

    if FRAUD_RE.search(text):
        add(4, "Possible fraud / unauthorised access")
    if SAFETY_RE.search(text):
        add(4, "Product safety hazard mentioned")
    if LEGAL_RE.search(text):
        add(2, "Legal / consumer-forum escalation threatened")
    if URGENT_RE.search(text):
        add(2, "Customer states urgency")
    amt = max(entities.get("amounts") or [0])
    if amt >= HIGH_AMOUNT:
        add(2, f"High amount involved (₹{amt:,.0f} ≥ ₹{HIGH_AMOUNT:,})")
    if category in ("payment", "refund") and amt:
        add(1, "Money is held / owed to the customer")
    s = sentiment["sentiment"]
    if s == "highly_negative":
        add(3, "Highly negative sentiment")
    elif s == "negative":
        add(1, "Negative sentiment")
    if sentiment.get("frustration", 0) > 0.6:
        add(1, f"High frustration ({sentiment['frustration']:.2f})")
    if repeat:
        add(2, "Repeat complaint (similar complaint already logged)")
    score = sum(f["points"] for f in factors)
    level = next(lvl for t, lvl in LEVELS if score >= t)
    if not factors:
        factors.append({"points": 0, "reason": "No risk factors detected"})
    return {"priority": level, "priority_score": score, "priority_factors": factors}


def route(text: str, category: str, confidence: float, priority_level: str) -> dict:
    if FRAUD_RE.search(text):
        return {"department": "Fraud & Security",
                "routing_reason": "Text mentions unauthorised access/charges; fraud cases override category routing."}
    if SAFETY_RE.search(text) and category == "product":
        return {"department": "Product Safety",
                "routing_reason": "Product complaint mentions a safety hazard (overheating/burning)."}
    dept = DEPARTMENTS[category]
    reason = f"Category '{category}' ({confidence:.0%} confidence) maps to {dept}."
    if confidence < 0.5:
        reason += " Low confidence: flagged for manual triage."
    if priority_level == "critical":
        reason += " Critical priority: escalation team is copied."
    return {"department": dept, "routing_reason": reason}
