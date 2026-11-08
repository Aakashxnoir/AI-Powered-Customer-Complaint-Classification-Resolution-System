"""Sentiment (4 levels) and emotion detection with pretrained transformers."""
import re
from functools import lru_cache

SENTIMENT_MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"
EMOTION_MODEL = "j-hartmann/emotion-english-distilroberta-base"

INTENSIFIERS = re.compile(
    r"\b(worst|unacceptable|disgust\w*|pathetic|horrible|terrible|lawyer|legal action|"
    r"consumer (court|complaint)|never (shop|buy)|scam|fraud|cheat\w*|furious|angry)\b", re.I)


@lru_cache
def _pipe(name):
    from transformers import pipeline
    return pipeline("text-classification", model=name, top_k=None, device=-1, truncation=True)


def _intensity(text: str) -> int:
    caps = sum(1 for w in text.split() if len(w) > 3 and w.isupper())
    return len(INTENSIFIERS.findall(text)) + (caps >= 2) + (text.count("!") >= 2)


def analyse(texts: list[str]) -> list[dict]:
    sent = _pipe(SENTIMENT_MODEL)(texts, batch_size=16)
    emo = _pipe(EMOTION_MODEL)(texts, batch_size=16)
    out = []
    for text, s, e in zip(texts, sent, emo):
        s = {d["label"].lower(): d["score"] for d in s}
        e = {d["label"].lower(): d["score"] for d in e}
        label = max(s, key=s.get)
        intensity = _intensity(text)
        if label == "negative" and (s["negative"] > 0.85 and intensity >= 1 or intensity >= 2):
            label = "highly_negative"
        emotion = max(e, key=e.get)
        frustration = round(e.get("anger", 0) + e.get("disgust", 0) + 0.5 * e.get("sadness", 0), 4)
        out.append({
            "sentiment": label,
            "sentiment_confidence": round(max(s.values()), 4),
            "sentiment_scores": {k: round(v, 4) for k, v in s.items()},
            "emotion": emotion,
            "emotion_scores": {k: round(v, 4) for k, v in e.items()},
            "frustration": min(frustration, 1.0),
            "intensity_markers": intensity,
        })
    return out
