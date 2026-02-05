#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

HYD_PARSER_ROOT="${HYD_PARSER_ROOT:-$ROOT_DIR/third_party/hyderabad_parser}"
SCL_DIR="${HYD_PARSER_SCL_DIR:-$HYD_PARSER_ROOT/scl}"
DOCKERFILE="${HYD_PARSER_DOCKERFILE:-$SCL_DIR/Dockerfile}"
IMAGE="${HYD_PARSER_IMAGE:-hyderabad-parser:local}"

if [[ -f "$DOCKERFILE" ]]; then
  echo "Building Hyderabad parser image: $IMAGE"
  docker build -t "$IMAGE" -f "$DOCKERFILE" "$SCL_DIR"
else
  echo "Warning: Dockerfile not found at $DOCKERFILE. Skipping parser image build."
fi
