#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from sprs_l0.analyze import analyze
from sprs_l0.validate import validate_spir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="input", default="src/l0/data/prepared/corpus.jsonl")
    parser.add_argument("--artifacts-dir", default="src/l0/artifacts/v0.1.0")
    parser.add_argument("--out", default="src/l0/artifacts/v0.1.0/eval_smoke.json")
    parser.add_argument("--sample", type=int, default=50)
    args = parser.parse_args()

    inp = Path(args.input)
    rows = []
    with inp.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

    if not rows:
        print("No rows found")
        return 1

    sample = random.sample(rows, k=min(args.sample, len(rows)))
    ok = 0
    total = 0
    for row in sample:
        text = row.get("text_norm") or row.get("text_deva") or ""
        spir = analyze(text, artifacts_dir=args.artifacts_dir)
        result = validate_spir(spir)
        total += 1
        if result.get("ok"):
            ok += 1

    out = {
        "total": total,
        "ok": ok,
        "bad": total - ok,
        "ok_ratio": (ok / total) if total else 0.0,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
