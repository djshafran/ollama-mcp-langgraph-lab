#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from collections import Counter
import unicodedata
from pathlib import Path


def _has_letter(text: str) -> bool:
    for ch in text:
        if unicodedata.category(ch).startswith("L"):
            return True
    return False


def _clean_token(text: str) -> str:
    return text.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="input", default="l0_data/prepared/corpus.jsonl")
    parser.add_argument("--out-dir", default="l0_artifacts/v0.1.0")
    parser.add_argument("--use-analyze", action="store_true", help="Use sprs_l0.analyze() tokens instead of whitespace split")
    parser.add_argument("--exclude-nonletters", action="store_true", help="Drop tokens with no letters (punct/digits)")
    args = parser.parse_args()

    inp = Path(args.input)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    surface = Counter()
    lemma = Counter()

    if args.use_analyze:
        from sprs_l0.analyze import analyze

    with inp.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if args.use_analyze:
                text = row.get("text_deva") or row.get("text_norm") or ""
                spir = analyze(text)
                for tok in spir.get("tokens", []):
                    s = _clean_token(tok.get("surface") or "")
                    l = _clean_token(tok.get("lemma") or "")
                    if args.exclude_nonletters and (not _has_letter(s) and not _has_letter(l)):
                        continue
                    if s:
                        surface[s] += 1
                    if l:
                        lemma[l] += 1
            else:
                text = row.get("text_norm") or row.get("text_deva") or ""
                for tok in text.split():
                    tok = _clean_token(tok)
                    if args.exclude_nonletters and not _has_letter(tok):
                        continue
                    surface[tok] += 1
                    lemma[tok.lower()] += 1

    lexicon = {
        "surface": surface.most_common(),
        "lemma": lemma.most_common(),
    }
    freqs = {
        "surface_total": sum(surface.values()),
        "lemma_total": sum(lemma.values()),
    }

    (out_dir / "lexicon.json").write_text(json.dumps(lexicon, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "freqs.json").write_text(json.dumps(freqs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote lexicon to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
