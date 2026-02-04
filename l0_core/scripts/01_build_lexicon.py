#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="input", default="l0_data/prepared/corpus.jsonl")
    parser.add_argument("--out-dir", default="l0_artifacts/v0.1.0")
    args = parser.parse_args()

    inp = Path(args.input)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    surface = Counter()
    lemma = Counter()

    with inp.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            text = row.get("text_norm") or row.get("text_deva") or ""
            for tok in text.split():
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
