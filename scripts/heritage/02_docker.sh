#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d "Heritage_Platform/ML" ]]; then
  echo "Warning: Heritage_Platform/ML not found. Local shell mode may not work."
fi

# Build and start L0 service

docker compose build l0

docker compose up -d l0

echo "L0 service started."
