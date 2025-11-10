#!/bin/bash
# AuraOS Quick Start Helper
# Convenient wrapper for common AuraOS operations

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/auraos_daemon/venv"

# Configurable VM username (default matches Multipass cloud images)
AURAOS_USER="${AURAOS_USER:-ubuntu}"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_header()
{
    echo -e "${BLUE}==============================${NC}"
    echo -e "${BLUE}      AuraOS Quick Start      ${NC}"
    echo -e "${BLUE}==============================${NC}"
}