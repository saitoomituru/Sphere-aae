#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

mkdir -p docs/api/_generated

python3 -m sphinx.ext.apidoc \
  --separate \
  --force \
  --module-first \
  -o docs/api/_generated \
  python/sphere_aae \
  python/sphere_aae/model \
  python/sphere_aae/testing \
  python/sphere_aae/bench

make -C docs html
