#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

HYD_PARSER_ROOT="${HYD_PARSER_ROOT:-$ROOT_DIR/third_party/hyderabad_parser}"
SCL_DIR="${HYD_PARSER_SCL_DIR:-$HYD_PARSER_ROOT/scl}"
INSTALL_CMD="${HYD_PARSER_INSTALL_CMD:-sudo make install}"
ENABLE_APACHE="${HYD_PARSER_ENABLE_APACHE:-}"

if [[ ! -d "$SCL_DIR" ]]; then
  echo "Missing SCL sources at $SCL_DIR."
  echo "Run scripts/hyderabad/00_fetch.sh and 01_build.sh first."
  exit 1
fi

echo "Installing SCL..."
(cd "$SCL_DIR" && bash -lc "$INSTALL_CMD")

if [[ -n "$ENABLE_APACHE" ]]; then
  echo "Enabling Apache CGI (requires sudo)..."
  sudo a2enmod cgid
  sudo systemctl restart apache2
fi

echo "Install complete."
