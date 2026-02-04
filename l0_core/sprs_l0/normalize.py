import re


def normalize_text(text: str) -> str:
    # Minimal, language-agnostic normalization: trim and collapse whitespace.
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text
