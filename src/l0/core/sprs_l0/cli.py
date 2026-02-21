from __future__ import annotations

import argparse
import json
from pathlib import Path
import os

from .analyze import analyze
from .exporter import export_artifacts
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
            syntax_backend=args.syntax_backend,
            return_ud=args.ud,
            return_syntax=True,
            ud_mode=args.ud_mode,
            include_enhanced=args.include_enhanced,
            kag_mode=args.kag_mode,
            include_provenance=args.include_provenance,
            doc=row.get("doc"),
            ref=row.get("ref"),
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


def cmd_export(args: argparse.Namespace) -> int:
    src = Path(args.input)
    rows = _read_jsonl(src)
    out_dir = Path(args.output_dir)
    formats = [fmt.strip() for fmt in (args.formats or "").split(",") if fmt.strip()]
    for idx, row in enumerate(rows, start=1):
        spir = row.get("spir", row)
        ref = row.get("ref") or f"row_{idx}"
        row_dir = out_dir / str(ref).replace("/", "_")
        export_artifacts(
            spir,
            formats=formats or None,
            output_dir=row_dir,
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sprs-l0")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_an = sub.add_parser("analyze", help="Analyze corpus.jsonl into SPIR v0.5 jsonl")
    p_an.add_argument("--in", dest="input", required=True)
    p_an.add_argument("--out", dest="output", required=True)
    p_an.add_argument("--limit", type=int, default=0)
    p_an.add_argument("--k-best", type=int, default=5)
    p_an.add_argument("--no-lattice", action="store_true")
    p_an.add_argument("--artifacts-dir", default=None)
    p_an.add_argument(
        "--syntax-backend",
        choices=["rules", "hydra", "hyderabad", "none", "off"],
        default=os.getenv("SYNTAX_BACKEND", "rules"),
        help="Syntax parse backend",
    )
    p_an.add_argument(
        "--ud-mode",
        choices=["head_rules", "projected", "none"],
        default="head_rules",
    )
    p_an.add_argument("--ud", dest="ud", action="store_true", default=True)
    p_an.add_argument("--no-ud", dest="ud", action="store_false")
    p_an.add_argument("--include-enhanced", dest="include_enhanced", action="store_true", default=True)
    p_an.add_argument("--no-enhanced", dest="include_enhanced", action="store_false")
    p_an.add_argument("--kag-mode", choices=["full", "none"], default="full")
    p_an.add_argument("--include-provenance", dest="include_provenance", action="store_true", default=True)
    p_an.add_argument("--no-provenance", dest="include_provenance", action="store_false")
    p_an.set_defaults(func=cmd_analyze)

    p_val = sub.add_parser("validate", help="Validate SPIR v0.5 jsonl")
    p_val.add_argument("--in", dest="input", required=True)
    p_val.set_defaults(func=cmd_validate)

    p_exp = sub.add_parser("export", help="Export sidecar artifacts from SPIR jsonl")
    p_exp.add_argument("--in", dest="input", required=True)
    p_exp.add_argument("--out-dir", dest="output_dir", required=True)
    p_exp.add_argument(
        "--formats",
        default="conllu_basic,conllu_enhanced,kag_jsonl,align_json",
        help="Comma separated list of formats",
    )
    p_exp.set_defaults(func=cmd_export)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
