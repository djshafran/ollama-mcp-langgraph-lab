#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

HYD_PARSER_ROOT="${HYD_PARSER_ROOT:-$ROOT_DIR/third_party/hyderabad_parser}"
SCL_DIR="${HYD_PARSER_SCL_DIR:-$HYD_PARSER_ROOT/scl}"
ZEN_DIR="${HYD_PARSER_ZEN_DIR:-$HYD_PARSER_ROOT/Zen}"
CONFIGURE_OPTS="${HYD_PARSER_CONFIGURE_OPTS:-}"
MAKE_OPTS="${HYD_PARSER_MAKE_OPTS:-}"
SKIP_ZEN="${HYD_PARSER_SKIP_ZEN:-}"

if [[ ! -d "$SCL_DIR" || ! -d "$ZEN_DIR" ]]; then
  echo "Missing Hyderabad parser sources at $HYD_PARSER_ROOT."
  echo "Run scripts/hyderabad/00_fetch.sh first or place sources there."
  exit 1
fi

if [[ -z "$SKIP_ZEN" ]]; then
  echo "Building Zen..."
  make -C "$ZEN_DIR/ML"
fi

SPEC_FILE="$SCL_DIR/spec.txt"
SPEC_TEMPLATE="${HYD_PARSER_SPEC_TEMPLATE:-$SCL_DIR/SPEC/spec_users.txt}"
if [[ ! -f "$SPEC_FILE" ]]; then
  if [[ -f "$SPEC_TEMPLATE" ]]; then
    echo "Creating spec.txt from template..."
    cp "$SPEC_TEMPLATE" "$SPEC_FILE"
    echo "spec.txt created at $SPEC_FILE. Review paths before install."
  else
    echo "spec.txt not found and template missing at $SPEC_TEMPLATE."
    exit 2
  fi
fi

echo "Configuring SCL..."
(cd "$SCL_DIR" && bash -lc "./configure $CONFIGURE_OPTS")
echo "Building SCL..."
(cd "$SCL_DIR" && make $MAKE_OPTS)
