#!/usr/bin/env bash
# Apply one of the patches to a scratch copy of the environment and print its path.
# Handy for poking at a fixed service by hand without touching the shipped tree.
#   scripts/apply_patch.sh patches/reference.patch
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "usage: $0 <patch file>" >&2
  exit 1
fi

root="$(cd "$(dirname "$0")/.." && pwd)"
patch="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
work="$(mktemp -d -t orderflow-XXXXXX)"

cp -R "$root/environment" "$work/environment"
rm -rf "$work/environment/order-service/target"

cd "$work/environment/order-service"
git init -q
git add -A
git -c user.email=scratch@local -c user.name=scratch commit -q -m base
git apply --whitespace=nowarn "$patch"

echo "$work/environment"
