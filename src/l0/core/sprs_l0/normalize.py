import re


def normalize_text(text: str) -> str:
    # Normalize escaped whitespace sequences that often appear in CLI/BDD payloads.
    text = text.replace("\\n", " ").replace("\\t", " ").replace("\\r", " ")
    # Minimal, language-agnostic normalization: trim and collapse whitespace.
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text
