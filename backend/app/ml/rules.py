"""Business rules: priority scoring and department routing. Every point of score
and every routing decision carries a human-readable reason."""
import re

from .catalog import DEPARTMENTS

FRAUD_RE = re.compile(r"\b(unauthori[sz]ed|fraud|without my (permission|knowledge)|hacked|someone else logged|scam)\b", re.I)
SAFETY_RE = re.compile(r"\b(overheat\w*|burning|smoke|fire(?!\s*tv)|shock|explod\w*)\b", re.I)
URGENT_RE = re.compile(r"\b(urgent|immediately|asap|right now|emergency|(?:by|before|fix (?:this|it)) today)\b", re.I)
LEGAL_RE = re.compile(r"\b(lawyer|legal action|consumer (court|complaint|forum))\b", re.I)
NEGATION_RE = re.compile(r"\b(not|no|never|isn't|wasn't|isnt|wasnt)\W+(?:\w+\W+){0,2}$", re.I)
HIGH_AMOUNT = 10000

LEVELS = [(8, "critical"), (5, "high"), (3, "medium"), (0, "low")]

# Which reasons speak to how soon (urgency) vs how bad (severity). Keyed by reason prefix,
# so rows stored before this split still get both scores.
URGENCY_REASONS = ("Customer states urgency", "Legal", "High frustration", "Repeat complaint")
URGENCY_MAX, SEVERITY_MAX = 7, 14  # sum of all points each side can reach


def _hit(regex, text: str) -> bool:
    """A keyword match that is not negated by 'not/no/never' in the 3 words before it."""
    # ponytail: 3-word negation window, no parser; misses "I'd hardly call it fraud".
    return any(not NEGATION_RE.search(text[:m.start()]) for m in regex.finditer(text))


def level(score: int) -> str:
    return next(lvl for t, lvl in LEVELS if score >= t)


def priority(text: str, category: str, sentiment: dict, entities: dict, repeat: bool) -> dict:
    factors = []

    def add(points, reason):
        factors.append({"points": points, "reason": reason})

    if _hit(FRAUD_RE, text):
        add(4, "Possible fraud / unauthorised access")
    if _hit(SAFETY_RE, text):
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
    if not factors:
        factors.append({"points": 0, "reason": "No risk factors detected"})
    return {"priority": level(score), "priority_score": score, "priority_factors": factors}


def urgency_severity(factors: list[dict]) -> dict:
    """Split priority factors into a 0-1 urgency score (how soon) and severity score (how bad).
    Rule-based scores, not model probabilities."""
    urg = sum(f["points"] for f in factors if f["reason"].startswith(URGENCY_REASONS))
    sev = sum(f["points"] for f in factors) - urg

    def band(x):
        return {"score": round(x, 2), "level": "high" if x >= 0.5 else "medium" if x >= 0.2 else "low"}
    return {"urgency": band(min(urg / URGENCY_MAX, 1)), "severity": band(min(sev / SEVERITY_MAX, 1))}


def route(text: str, category: str, confidence: float, priority_level: str) -> dict:
    if _hit(FRAUD_RE, text):
        return {"department": "Fraud & Security",
                "routing_reason": "Text mentions unauthorised access/charges; fraud cases override category routing."}
    if _hit(SAFETY_RE, text) and category == "product":
        return {"department": "Product Safety",
                "routing_reason": "Product complaint mentions a safety hazard (overheating/burning)."}
    dept = DEPARTMENTS[category]
    reason = f"Category '{category}' ({confidence:.0%} confidence) maps to {dept}."
    if confidence < 0.5:
        reason += " Low confidence: flagged for manual triage."
    if priority_level == "critical":
        reason += " Critical priority: escalation team is copied."
    return {"department": dept, "routing_reason": reason}
