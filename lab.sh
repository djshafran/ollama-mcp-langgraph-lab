#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

compose() {
  if [[ "${PROFILE:-gpu}" == "gpu" ]]; then
    docker compose -f docker-compose.yml -f docker-compose.gpu.yml "$@"
  else
    docker compose -f docker-compose.yml "$@"
  fi
}

cmd="${1:-help}"
shift || true

case "$cmd" in
  up)
    PROFILE="${1:-gpu}"
    export PROFILE
    echo "Starting stack (PROFILE=$PROFILE)..."
    compose up -d --build
    ;;
  down)
    PROFILE="${1:-gpu}"
    export PROFILE
    compose down
    ;;
  pull)
    PROFILE="${PROFILE:-gpu}"
    model="${1:-${MODEL:-qwen3:8b}}"
    echo "Pulling model: $model"
    compose exec -T ollama ollama pull "$model"
    ;;
  list)
    PROFILE="${PROFILE:-gpu}"
    compose exec -T ollama ollama list
    ;;
  ask)
    PROFILE="${PROFILE:-gpu}"
    if [[ $# -lt 1 ]]; then
      echo "Usage: ./lab.sh ask \"your prompt\""
      exit 1
    fi
    compose run --rm agent python /app/ask.py "$*"
    ;;
  logs)
    PROFILE="${PROFILE:-gpu}"
    compose logs -f
    ;;
  *)
    cat <<'USAGE'
Usage:
  ./lab.sh up [cpu|gpu]
  ./lab.sh down [cpu|gpu]
  ./lab.sh pull <model>
  ./lab.sh list
  ./lab.sh ask "your prompt"
  ./lab.sh logs
USAGE
    ;;
esac
