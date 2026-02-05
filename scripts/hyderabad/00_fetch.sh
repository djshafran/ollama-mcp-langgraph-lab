#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

HYD_PARSER_ROOT="${HYD_PARSER_ROOT:-$ROOT_DIR/third_party/hyderabad_parser}"
mkdir -p "$HYD_PARSER_ROOT"

SCL_URL="${HYD_PARSER_SCL_URL:-https://github.com/samsaadhanii/scl.git}"
SCL_BRANCH="${HYD_PARSER_SCL_BRANCH:-}"
ZEN_URL="${HYD_PARSER_ZEN_URL:-https://gitlab.inria.fr/huet/Zen.git}"
ZEN_BRANCH="${HYD_PARSER_ZEN_BRANCH:-}"

clone_or_update() {
  local url="$1"
  local dir="$2"
  local branch="$3"

  if [[ -d "$dir/.git" ]]; then
    echo "Updating $dir..."
    local current_branch
    current_branch="$(git -C "$dir" rev-parse --abbrev-ref HEAD || echo "")"
    if [[ -z "$branch" ]]; then
      if [[ "$current_branch" == "HEAD" || -z "$current_branch" ]]; then
        branch="master"
      else
        branch="$current_branch"
      fi
    fi
    git -C "$dir" pull --ff-only origin "$branch" || true
    if ! git -C "$dir" rev-parse --verify HEAD >/dev/null 2>&1; then
      git -C "$dir" fetch origin "$branch"
      git -C "$dir" checkout -B "$branch" "origin/$branch"
    fi
    return 0
  fi

  if [[ -n "$(ls -A "$dir" 2>/dev/null)" ]]; then
    echo "Directory $dir exists and is not a git repo."
    echo "Remove it or set HYD_PARSER_ROOT to an empty folder."
    exit 1
  fi

  echo "Cloning $url into $dir..."
  git clone "$url" "$dir"
  if [[ -n "$branch" ]]; then
    git -C "$dir" checkout -B "$branch" "origin/$branch"
  elif ! git -C "$dir" rev-parse --verify HEAD >/dev/null 2>&1; then
    git -C "$dir" fetch origin master
    git -C "$dir" checkout -B master origin/master
  fi
}

clone_or_update "$ZEN_URL" "$HYD_PARSER_ROOT/Zen" "$ZEN_BRANCH"
clone_or_update "$SCL_URL" "$HYD_PARSER_ROOT/scl" "$SCL_BRANCH"

echo "Done."
