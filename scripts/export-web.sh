#!/usr/bin/env bash
set -Eeuo pipefail

PRESET_NAME="Web"
EXPORT_PATH="build/web/index.html"
LOG_LINES="${GODOT_EXPORT_LOG_LINES:-200}"
INSTALL_GODOT=1
GODOT_BIN="${GODOT_BIN:-godot}"

usage() {
  cat <<'USAGE'
Usage: bash scripts/export-web.sh [--no-install] [--godot-bin PATH]

Exports the Godot Web preset to build/web/index.html.

Options:
  --no-install       Use an already installed Godot binary and export templates.
  --godot-bin PATH   Godot executable to use instead of GODOT_BIN or godot.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --no-install)
      INSTALL_GODOT=0
      shift
      ;;
    --godot-bin)
      if [ "$#" -lt 2 ]; then
        echo "Missing value for --godot-bin." >&2
        usage >&2
        exit 2
      fi
      GODOT_BIN="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

require_tool() {
  command -v "$1" >/dev/null 2>&1 || fail "Required tool '$1' is not available on PATH."
}

if [ ! -f ".godot-version" ]; then
  fail "Missing .godot-version; run this script from the repository root."
fi

GODOT_VERSION="$(tr -d '\r\n' < .godot-version)"
if [ -z "$GODOT_VERSION" ]; then
  fail ".godot-version is empty."
fi

TEMPLATE_VERSION="${GODOT_VERSION/-/.}"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
TEMPLATE_DIR="$DATA_HOME/godot/export_templates/$TEMPLATE_VERSION"
WEB_RELEASE_TEMPLATE="$TEMPLATE_DIR/web_release.zip"
WEB_DEBUG_TEMPLATE="$TEMPLATE_DIR/web_debug.zip"

install_godot_and_templates() {
  require_tool curl
  require_tool unzip

  local cache_dir="${GODOT_BOOTSTRAP_DIR:-.godot-bootstrap/$GODOT_VERSION}"
  local godot_zip="$cache_dir/godot-linux.zip"
  local templates_zip="$cache_dir/export-templates.tpz"
  local godot_url="https://github.com/godotengine/godot/releases/download/$GODOT_VERSION/Godot_v${GODOT_VERSION}_linux.x86_64.zip"
  local templates_url="https://github.com/godotengine/godot/releases/download/$GODOT_VERSION/Godot_v${GODOT_VERSION}_export_templates.tpz"

  mkdir -p "$cache_dir" "$TEMPLATE_DIR"

  if [ ! -x "$cache_dir/Godot_v${GODOT_VERSION}_linux.x86_64" ]; then
    echo "Downloading Godot $GODOT_VERSION from $godot_url"
    curl --fail --location --retry 3 --connect-timeout 20 --output "$godot_zip" "$godot_url"
    unzip -q -o "$godot_zip" -d "$cache_dir"
    chmod +x "$cache_dir/Godot_v${GODOT_VERSION}_linux.x86_64"
  fi

  GODOT_BIN="$cache_dir/Godot_v${GODOT_VERSION}_linux.x86_64"

  if [ ! -f "$WEB_RELEASE_TEMPLATE" ] || [ ! -f "$WEB_DEBUG_TEMPLATE" ]; then
    echo "Installing Godot export templates into $TEMPLATE_DIR"
    curl --fail --location --retry 3 --connect-timeout 20 --output "$templates_zip" "$templates_url"
    unzip -q -o "$templates_zip" -d "$cache_dir/templates-unpacked"
    cp "$cache_dir"/templates-unpacked/templates/* "$TEMPLATE_DIR"/
  fi
}

print_context() {
  echo "Godot Web export"
  echo "  repository: $(pwd)"
  echo "  requested version: $GODOT_VERSION"
  echo "  command: $GODOT_BIN"
  echo "  preset: $PRESET_NAME"
  echo "  export path: $EXPORT_PATH"
  echo "  template version: $TEMPLATE_VERSION"
  echo "  template directory: $TEMPLATE_DIR"
  echo "  no-install: $([ "$INSTALL_GODOT" -eq 0 ] && echo true || echo false)"
}

run_with_log() {
  local log_file="$1"
  shift
  echo "+ $*"
  if "$@" >"$log_file" 2>&1; then
    return 0
  fi

  local status=$?
  echo "Command failed with exit code $status: $*" >&2
  echo "---- Godot output tail (last $LOG_LINES lines) ----" >&2
  tail -n "$LOG_LINES" "$log_file" >&2 || true
  echo "---- end Godot output tail ----" >&2
  return "$status"
}

if [ "$INSTALL_GODOT" -eq 1 ]; then
  install_godot_and_templates
fi

command -v "$GODOT_BIN" >/dev/null 2>&1 || [ -x "$GODOT_BIN" ] || fail "Godot binary '$GODOT_BIN' is not available. Install Godot $GODOT_VERSION or omit --no-install on Linux."

print_context

if [ ! -f "$WEB_RELEASE_TEMPLATE" ] || [ ! -f "$WEB_DEBUG_TEMPLATE" ]; then
  echo "WARNING: Expected Web templates were not found:" >&2
  echo "  $WEB_RELEASE_TEMPLATE" >&2
  echo "  $WEB_DEBUG_TEMPLATE" >&2
  echo "Godot may fail export validation until matching templates are installed." >&2
fi

mkdir -p "$(dirname "$EXPORT_PATH")"
rm -f build/web/index.html build/web/index.js build/web/index.wasm build/web/index.pck

VERSION_LOG="$(mktemp)"
EXPORT_LOG="$(mktemp)"
trap 'rm -f "$VERSION_LOG" "$EXPORT_LOG"' EXIT

run_with_log "$VERSION_LOG" "$GODOT_BIN" --version
run_with_log "$EXPORT_LOG" "$GODOT_BIN" --headless --verbose --path . --export-release "$PRESET_NAME" "$EXPORT_PATH"

for asset in build/web/index.html build/web/index.js build/web/index.wasm build/web/index.pck; do
  if [ ! -s "$asset" ]; then
    fail "Expected export asset missing or empty: $asset"
  fi
done

echo "Godot Web export completed successfully."
ls -lh build/web/index.html build/web/index.js build/web/index.wasm build/web/index.pck
