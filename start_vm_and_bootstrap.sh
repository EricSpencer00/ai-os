#!/usr/bin/env bash
# Convenience top-level launcher
# Run the VM + cloud-init bootstrap using the existing helper in vm_resources.
# Usage: ./start_vm_and_bootstrap.sh [--debug]

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT_DIR="$SCRIPT_DIR"
TARGET="$ROOT_DIR/vm_resources/run_and_bootstrap_vm.sh"

if [ ! -f "$TARGET" ]; then
  echo "Error: expected helper script at $TARGET" >&2
  exit 2
fi

if [ "$#" -gt 0 ]; then
  # forward args (e.g. --debug) to underlying script
  exec "$TARGET" "$@"
else
  exec "$TARGET"
fi
