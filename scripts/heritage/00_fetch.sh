#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"
HERITAGE_ROOT="${HERITAGE_ROOT:-$ROOT_DIR/third_party/heritage}"
mkdir -p "$HERITAGE_ROOT"

clone_or_update() {
  local url="$1"
  local dir="$2"
  if [[ -d "$dir/.git" ]]; then
    echo "Updating $dir..."
    branch="$(git -C "$dir" rev-parse --abbrev-ref HEAD || echo "")"
    if [[ "$branch" == "HEAD" || -z "$branch" ]]; then
      branch="master"
    fi
    git -C "$dir" pull --ff-only origin "$branch" || true
    # If repo has no commits checked out, try to set master
    if ! git -C "$dir" rev-parse --verify HEAD >/dev/null 2>&1; then
      git -C "$dir" fetch origin master
      git -C "$dir" checkout -B master origin/master
    fi
  else
    echo "Cloning $url into $dir..."
    git clone "$url" "$dir"
    # Ensure a branch is checked out (some repos default to no HEAD)
    if ! git -C "$dir" rev-parse --verify HEAD >/dev/null 2>&1; then
      git -C "$dir" fetch origin master
      git -C "$dir" checkout -B master origin/master
    fi
  fi
}

clone_or_update "https://gitlab.inria.fr/huet/Zen.git" "$HERITAGE_ROOT/Zen"
clone_or_update "https://gitlab.inria.fr/huet/Heritage_Resources.git" "$HERITAGE_ROOT/Heritage_Resources"
clone_or_update "https://gitlab.inria.fr/huet/Heritage_Platform.git" "$HERITAGE_ROOT/Heritage_Platform"

echo "Done."
