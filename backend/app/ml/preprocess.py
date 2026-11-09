import html
import re

MIN_LEN, MAX_LEN = 10, 5000


def normalize(text: str) -> str:
    """Clean raw complaint text: unescape HTML, drop tags/URLs/zero-width chars, collapse whitespace.
    Emails are kept: entity extraction reads them from the cleaned text."""
    text = html.unescape(str(text))
    text = re.sub(r"<[^<>]*>", " ", text)  # [^<>] keeps this linear on unclosed "<<<<"
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"[​-‍﻿]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def validate(text) -> str | None:
    """Return an error message, or None if the complaint text is acceptable."""
    if text is None or not str(text).strip():
        return "empty complaint text"
    if len(str(text)) > 4 * MAX_LEN:  # cheap gate before any regex work on huge input
        return f"text longer than {MAX_LEN} characters"
    clean = normalize(text)
    if len(clean) < MIN_LEN:
        return f"text shorter than {MIN_LEN} characters"
    if len(clean) > MAX_LEN:
        return f"text longer than {MAX_LEN} characters"
    if not re.search(r"[A-Za-z]", clean):
        return "text has no words"
    return None
