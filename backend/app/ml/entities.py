"""Entity extraction: regex for structured IDs/amounts, gazetteer for products and
cities, spaCy NER for dates and any locations/money the rules miss."""
import re
from functools import lru_cache

from .catalog import CITIES, PRODUCTS

ORDER_RE = re.compile(r"\b(?:ORD|ORDER)[-#\s]?(\d{5,10})\b", re.I)
AMOUNT_RE = re.compile(r"(?:₹|rs\.?|inr|\$)\s?(\d[\d,]*(?:\.\d{1,2})?)", re.I)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE_RE = re.compile(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)")


@lru_cache
def _nlp():
    import spacy
    return spacy.load("en_core_web_sm", disable=["lemmatizer"])


def extract(text: str, doc=None) -> dict:
    doc = doc if doc is not None else _nlp()(text)
    low = text.lower()
    ents = {
        "order_ids": [f"ORD-{m}" for m in ORDER_RE.findall(text)],
        "amounts": [float(a.replace(",", "")) for a in AMOUNT_RE.findall(text)],
        "products": [p for p in PRODUCTS if p.lower() in low],
        "locations": [c for c in CITIES if re.search(rf"\b{c.lower()}\b", low)],
        "dates": [],
        "emails": EMAIL_RE.findall(text),
        "phones": PHONE_RE.findall(text),
    }
    for e in doc.ents:
        if e.label_ == "DATE":
            ents["dates"].append(e.text)
        elif (e.label_ == "GPE" and e.text not in ents["locations"] and e.text.lower() != "india"
              and not any(ch.isdigit() for ch in e.text)):
            ents["locations"].append(e.text)
        elif e.label_ == "MONEY" and not ents["amounts"]:
            num = re.sub(r"[^\d.]", "", e.text)
            if num:
                ents["amounts"].append(float(num))
    return {k: list(dict.fromkeys(v)) for k, v in ents.items()}


def extract_many(texts: list[str]) -> list[dict]:
    return [extract(t, d) for t, d in zip(texts, _nlp().pipe(texts, batch_size=64))]
