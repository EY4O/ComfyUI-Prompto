#!/usr/bin/env bash
# Decides whether a push changed what ships to the Comfy Registry. Writes
# publish=true|false to $GITHUB_OUTPUT (or stdout when run by hand).
# Usage: needs-publish.sh EVENT BEFORE AFTER
set -euo pipefail
event=$1 before=$2 after=$3
out=${GITHUB_OUTPUT:-/dev/stdout}

if [ "$event" != "push" ] || ! git cat-file -e "${before}^{commit}" 2>/dev/null; then
  echo "publish=true" >> "$out"; exit 0
fi

# Anything outside the docs ships with the node.
code=$(git diff --name-only "$before" "$after" \
  | grep -vE '^(README\.md|LICENSE|docs/|\.github/|pyproject\.toml$)' || true)
# pyproject.toml counts too, unless only its version line changed.
meta=$(git diff -U0 "$before" "$after" -- pyproject.toml \
  | grep -E '^[+-][^+-]' | grep -vE '^[+-]version *=' || true)

if [ -n "$code$meta" ]; then
  echo "publish=true" >> "$out"
else
  echo "::notice::Docs-only change: not publishing to the Comfy Registry."
  echo "publish=false" >> "$out"
fi
