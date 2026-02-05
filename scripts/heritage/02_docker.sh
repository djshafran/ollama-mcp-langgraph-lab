#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"
HERITAGE_ROOT="${HERITAGE_ROOT:-$ROOT_DIR/third_party/heritage}"

if [[ ! -d "$HERITAGE_ROOT/Heritage_Platform/ML" ]]; then
  echo "Warning: $HERITAGE_ROOT/Heritage_Platform/ML not found. Local shell mode may not work."
fi

# Build and start L0 service

docker compose build l0

docker compose up -d l0

echo "L0 service started."
