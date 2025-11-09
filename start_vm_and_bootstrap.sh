#!/usr/bin/env bash
# Convenience top-level launcher
# Prefer Multipass (when installed on macOS) for a reliable VM path,
# otherwise fall back to the existing QEMU helper in vm_resources.
# Usage: ./start_vm_and_bootstrap.sh [--debug]

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT_DIR="$SCRIPT_DIR"
QEMU_HELPER="$ROOT_DIR/vm_resources/run_and_bootstrap_vm.sh"
MP_HELPER="$ROOT_DIR/start_vm_with_multipass.sh"

function die(){ echo "$*" >&2; exit 2; }

if command -v multipass >/dev/null 2>&1 && [ -x "$MP_HELPER" ]; then
  echo "Multipass detected — launching via $MP_HELPER"
  if [ "$#" -gt 0 ]; then
    exec "$MP_HELPER" "$@"
  else
    exec "$MP_HELPER"
  fi
else
  if [ ! -x "$QEMU_HELPER" ]; then
    die "QEMU helper not found or not executable: $QEMU_HELPER"
  fi
  echo "Multipass not detected — falling back to QEMU helper: $QEMU_HELPER"
  if [ "$#" -gt 0 ]; then
    exec "$QEMU_HELPER" "$@"
  else
    exec "$QEMU_HELPER"
  fi
fi
