#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

printf '\n==> Run implementation-detail advisory tests\n'
python -m unittest tests.test_player_placeholder_advisory

printf '\n==> Advisory validation passed\n'
