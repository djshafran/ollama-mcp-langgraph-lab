from __future__ import annotations

import argparse
import json
from pathlib import Path
import os

from .analyze import analyze
from .validate import validate_spir


def _read_jsonl(path: Path) -> list[dict]:
    items = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def cmd_analyze(args: argparse.Namespace) -> int:
    src = Path(args.input)
    dst = Path(args.output)
    if args.syntax_backend:
        os.environ["SYNTAX_BACKEND"] = args.syntax_backend
    rows = _read_jsonl(src)
    out_rows = []
    for i, row in enumerate(rows):
        if args.limit and i >= args.limit:
            break
        text = (
            row.get("text_norm")
            or row.get("text_iast")
            or row.get("text_deva")
            or row.get("text")
            or ""
        )
        spir = analyze(
            text,
            input_format="auto",
            k_best=args.k_best,
            return_lattice=not args.no_lattice,
            artifacts_dir=args.artifacts_dir,
        )
        out_rows.append({"ref": row.get("ref"), "doc": row.get("doc"), "spir": spir})
    _write_jsonl(dst, out_rows)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    src = Path(args.input)
    rows = _read_jsonl(src)
    ok = 0
    for row in rows:
        spir = row.get("spir", row)
        result = validate_spir(spir)
        if result.get("ok"):
            ok += 1
    total = len(rows)
    print(json.dumps({"total": total, "ok": ok, "bad": total - ok}))
    return 0 if ok == total else 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sprs_l0")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_an = sub.add_parser("analyze", help="Analyze corpus.jsonl into SPIR jsonl")
    p_an.add_argument("--in", dest="input", required=True)
    p_an.add_argument("--out", dest="output", required=True)
    p_an.add_argument("--limit", type=int, default=0)
    p_an.add_argument("--k-best", type=int, default=5)
    p_an.add_argument("--no-lattice", action="store_true")
    p_an.add_argument("--artifacts-dir", default=None)
    p_an.add_argument(
        "--syntax-backend",
        choices=["rules", "hydra", "hyderabad", "none", "off"],
        help="Syntax parse backend",
    )
    p_an.set_defaults(func=cmd_analyze)

    p_val = sub.add_parser("validate", help="Validate SPIR jsonl")
    p_val.add_argument("--in", dest="input", required=True)
    p_val.set_defaults(func=cmd_validate)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
