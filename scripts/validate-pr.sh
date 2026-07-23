#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

log() {
  printf '\n==> %s\n' "$1"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'Required command is unavailable: %s\n' "$1" >&2
    exit 127
  fi
}

require_command godot
require_command git

log "Verify Godot version"
godot --version

log "Load project and default scene"
godot --headless --path . --quit-after 2

log "Run player controller test"
godot --headless --path . --script tests/godot/player_controller_2d_test.gd

log "Run follow camera test"
godot --headless --path . --script tests/godot/follow_camera_2d_test.gd

log "Load player movement validation scene"
godot --headless --path . scenes/validation/player_movement_validation.tscn --quit-after 2

log "Export Godot Web build"
bash scripts/export-web.sh --no-install

log "Validate Web export artifacts"
test -s build/web/index.html
test -s build/web/index.js
test -s build/web/index.wasm
test -s build/web/index.pck

log "Check patch formatting"
git diff --check

log "Migrated runtime validation passed"
