#!/usr/bin/env bash
# Start a write-up for an agent attempt from the template.
#   scripts/new_attempt.sh sonnet-4.5 3
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "usage: $0 <model-slug> <attempt-number>" >&2
  exit 1
fi

root="$(cd "$(dirname "$0")/.." && pwd)"
stamp="$(date +%Y-%m-%d)"
target="$root/results/attempts/${stamp}-$1-$2.md"

if [ -e "$target" ]; then
  echo "already exists: $target" >&2
  exit 1
fi

sed "s/<date>-<model>-<n>/${stamp}-$1-$2/" "$root/results/attempts/TEMPLATE.md" > "$target"
echo "$target"
