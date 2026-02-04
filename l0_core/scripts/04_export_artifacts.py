#!/usr/bin/env python
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="src", default="l0_artifacts/v0.1.0")
    parser.add_argument("--to", dest="dst", default="l0_artifacts/current")
    args = parser.parse_args()

    src = Path(args.src)
    dst = Path(args.dst)
    if not src.exists():
        print(f"Source artifacts not found: {src}")
        return 1

    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    print(f"Exported artifacts {src} -> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
