#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sprs_l0.normalize import normalize_text


def iter_lines(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            yield idx, line


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", default="src/l0/data/raw")
    parser.add_argument("--out", default="src/l0/data/prepared/corpus.jsonl")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for fp in sorted(raw_dir.glob("*.txt")):
        name = fp.stem.lower()
        doc = "bg" if "gita" in name else "sb" if "bhagavatam" in name else name
        for idx, line in iter_lines(fp):
            rows.append(
                {
                    "doc": doc,
                    "ref": str(idx),
                    "text_deva": line,
                    "text_iast": None,
                    "text_norm": normalize_text(line),
                }
            )

    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Wrote {len(rows)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
