#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENDOR_DIR="$SCRIPT_DIR/src/batou_type/vendor"

sync_stubs() {
    local src="$1" dest="$2" name="$3"

    if [ -d "$src" ]; then
        rsync -av --delete --include='*.pyi' --exclude='*' "$src/" "$dest/"
        echo "Synced $name stubs ($src → $dest)"
    else
        echo "SKIP: $src not found ($name)"
    fi
}

sync_stubs "$SCRIPT_DIR/../batou/stubs" "$VENDOR_DIR/batou" "batou"
sync_stubs "$SCRIPT_DIR/../batou_ext/stubs" "$VENDOR_DIR/batou_ext" "batou_ext"
