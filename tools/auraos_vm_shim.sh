#!/usr/bin/env bash
# Simple VM-side automation shim for AuraOS GUI apps
# Usage: auraos_vm_shim.sh automate "<request>"

set -e

cmd="$1"
shift || true

case "$cmd" in
  automate)
    request="$*"
    # Basic handlers
    if echo "$request" | grep -iq "open firefox"; then
      nohup env DISPLAY=:99 firefox >/dev/null 2>&1 &
      echo "Launched Firefox"
      exit 0
    fi

    if echo "$request" | grep -iq "^find files:"; then
      query=$(echo "$request" | sed -E 's/^find files:\s*//I')
      # sanitize single quotes
      q=$(printf "%s" "$query" | sed "s/'/'\\''/g")
      bash -lc "find ~ -type f -iname '*$q*' 2>/dev/null | head -n 200"
      exit 0
    fi

    if echo "$request" | grep -iq "^open url:"; then
      url=$(echo "$request" | sed -E 's/^open url:\s*//I')
      nohup env DISPLAY=:99 firefox "$url" >/dev/null 2>&1 &
      echo "Opened $url"
      exit 0
    fi

    echo "Unsupported request: $request" >&2
    exit 2
    ;;
  *)
    echo "Usage: $0 automate \"<request>\"" >&2
    exit 1
    ;;
esac
