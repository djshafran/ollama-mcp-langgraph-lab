#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts-dir", default="src/l0/artifacts/v0.1.0")
    args = parser.parse_args()

    art_dir = Path(args.artifacts_dir)
    freqs_path = art_dir / "freqs.json"
    freqs = json.loads(freqs_path.read_text(encoding="utf-8")) if freqs_path.exists() else {}

    priors = {
        "rare_token_penalty": 1.0,
        "common_token_bonus": 0.5,
        "unk_penalty": 2.0,
        "lemma_bonus": 0.2,
    }
    scoring_config = {
        "version": "v0.1.0",
        "freqs": freqs,
        "priors": priors,
    }

    (art_dir / "priors.json").write_text(json.dumps(priors, ensure_ascii=False, indent=2), encoding="utf-8")
    (art_dir / "scoring_config.json").write_text(
        json.dumps(scoring_config, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Wrote priors to {art_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
