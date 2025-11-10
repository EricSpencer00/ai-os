#!/bin/bash
# AuraOS Terminal v3.0 - Quick Verification Script
# Run this to verify all components are ready

echo "╔════════════════════════════════════════════════════════╗"
echo "║  AuraOS Terminal v3.0 - Verification Script          ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

ERRORS=0
WARNINGS=0
PASSES=0

check_pass() {
    echo "✓ $1"
    ((PASSES++))
}

check_fail() {
    echo "❌ $1"
    ((ERRORS++))
}

check_warn() {
    echo "⚠️  $1"
    ((WARNINGS++))
}

# Phase 1: Environment
echo "═══════════════════════════════════════════════════════"
echo "PHASE 1: Environment"
echo "═══════════════════════════════════════════════════════"

if python3 --version >/dev/null 2>&1; then
    check_pass "Python3 installed"
else
    check_fail "Python3 not found"
fi

if python3 -m pip --version >/dev/null 2>&1; then
    check_pass "pip available"
else
    check_fail "pip not found"
fi

if python3 -c "import flask" 2>/dev/null; then
    check_pass "Flask library available"
else
    check_warn "Flask not installed (pip install flask)"
fi

if python3 -c "import requests" 2>/dev/null; then
    check_pass "Requests library available"
else
    check_warn "Requests not installed (pip install requests)"
fi

if python3 -c "import PIL" 2>/dev/null; then
    check_pass "Pillow library available"
else
    check_warn "Pillow not installed (pip install Pillow)"
fi

echo ""

# Phase 2: File Structure
echo "═══════════════════════════════════════════════════════"
echo "PHASE 2: File Structure"
echo "═══════════════════════════════════════════════════════"

files=(
    "auraos_terminal_v3.py"
    "auraos_daemon/core/ai_handler.py"
    "auraos_daemon/core/screen_context.py"
    "auraos_daemon/core/daemon.py"
    "auraos_daemon/main.py"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        check_pass "Found: $file"
    else
        check_fail "Missing: $file"
    fi
done

echo ""

# Phase 3: Syntax
echo "═══════════════════════════════════════════════════════"
echo "PHASE 3: Python Syntax"
echo "═══════════════════════════════════════════════════════"

if python3 -m py_compile auraos_terminal_v3.py 2>/dev/null; then
    check_pass "Terminal syntax valid"
else
    check_fail "Terminal syntax error"
fi

if python3 -m py_compile auraos_daemon/core/ai_handler.py 2>/dev/null; then
    check_pass "AI Handler syntax valid"
else
    check_fail "AI Handler syntax error"
fi

if python3 -m py_compile auraos_daemon/core/screen_context.py 2>/dev/null; then
    check_pass "Screen Context syntax valid"
else
    check_fail "Screen Context syntax error"
fi

echo ""

# Phase 4: Imports
echo "═══════════════════════════════════════════════════════"
echo "PHASE 4: Import Tests"
echo "═══════════════════════════════════════════════════════"

if python3 -c "import sys; sys.path.insert(0, 'auraos_daemon'); from core.ai_handler import EnhancedAIHandler" 2>/dev/null; then
    check_pass "AI Handler import successful"
else
    check_fail "AI Handler import failed"
fi

if python3 -c "import sys; sys.path.insert(0, 'auraos_daemon'); from core.screen_context import ScreenContextDB, ScreenCaptureManager" 2>/dev/null; then
    check_pass "Screen Context import successful"
else
    check_fail "Screen Context import failed"
fi

echo ""

# Phase 5: Documentation
echo "═══════════════════════════════════════════════════════"
echo "PHASE 5: Documentation"
echo "═══════════════════════════════════════════════════════"

docs=(
    "TERMINAL_V3_QUICKREF.md"
    "TERMINAL_V3_SETUP.md"
    "TERMINAL_V3_ARCHITECTURE.md"
    "TERMINAL_V3_DIAGRAMS.md"
    "IMPLEMENTATION_SUMMARY.md"
    "DOCUMENTATION_INDEX.md"
    "TEST_PLAN.md"
)

for doc in "${docs[@]}"; do
    if [ -f "$doc" ]; then
        lines=$(wc -l < "$doc")
        check_pass "Found: $doc ($lines lines)"
    else
        check_fail "Missing: $doc"
    fi
done

echo ""

# Phase 6: Optional components
echo "═══════════════════════════════════════════════════════"
echo "PHASE 6: Optional Components"
echo "═══════════════════════════════════════════════════════"

if command -v git >/dev/null 2>&1; then
    check_pass "Git available (for version control)"
else
    check_warn "Git not available"
fi

if [ -f "auraos.sh" ]; then
    if bash -n auraos.sh 2>/dev/null; then
        check_pass "auraos.sh syntax valid"
    else
        check_warn "auraos.sh has syntax warnings"
    fi
else
    check_warn "auraos.sh not found"
fi

echo ""

# Summary
echo "═══════════════════════════════════════════════════════"
echo "VERIFICATION SUMMARY"
echo "═══════════════════════════════════════════════════════"
echo "✓ Passed:  $PASSES"
echo "⚠️  Warnings: $WARNINGS"
echo "❌ Failed:  $ERRORS"

if [ $ERRORS -eq 0 ]; then
    echo ""
    echo "🎉 All critical checks passed!"
    echo ""
    echo "Next steps:"
    echo "1. Review documentation: TERMINAL_V3_QUICKREF.md"
    echo "2. Start daemon: cd auraos_daemon && python main.py"
    echo "3. Launch terminal: python auraos_terminal_v3.py"
    echo "4. Follow TEST_PLAN.md for comprehensive testing"
    echo ""
    exit 0
else
    echo ""
    echo "⚠️  Please fix critical issues before proceeding"
    echo ""
    exit 1
fi
