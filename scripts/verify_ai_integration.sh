#!/bin/bash
#!/bin/bash
# Quick verification that AI integration is repeatable

cd "$(dirname "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)")"

echo "✅ AI Integration Repeatability Verification"
echo "============================================"
echo ""

errors=0

# Check files exist
echo "📁 Files:"
for f in core/key_store.py core/api_key_cli.py core/ai_helper.py scripts/test_ai_terminal.py auraos_terminal.py auraos.sh AUDIT_AI_INTEGRATION.md QUICK_REFERENCE_AI.md; do
    if [ -f "$f" ]; then
        echo "  ✓ $f"
    else
        echo "  ✗ $f (MISSING)"
        ((errors++))
    fi
done
echo ""

# Check auraos.sh has new commands
echo "📋 auraos.sh commands:"
if grep -q "cmd_keys_onboard" auraos.sh; then
    echo "  ✓ cmd_keys_onboard() function"
else
    echo "  ✗ cmd_keys_onboard() function (MISSING)"
    ((errors++))
fi

if grep -q "^    onboard)" auraos.sh; then
    echo "  ✓ 'onboard' alias in dispatcher"
else
    echo "  ✗ 'onboard' alias in dispatcher (MISSING)"
    ((errors++))
fi

if grep -q "keys onboard" auraos.sh && grep -q "Interactive API key" auraos.sh; then
    echo "  ✓ Help text mentions 'keys onboard'"
else
    echo "  ✗ Help text (MISSING or outdated)"
    ((errors++))
fi
echo ""

# Quick Python checks
echo "🔗 Python modules:"
python3 -c "import sys; sys.path.insert(0, '.'); from core import key_store" 2>/dev/null && echo "  ✓ core.key_store" || { echo "  ✗ core.key_store"; ((errors++)); }
python3 -c "import sys; sys.path.insert(0, '.'); from core import api_key_cli" 2>/dev/null && echo "  ✓ core.api_key_cli" || { echo "  ✗ core.api_key_cli"; ((errors++)); }
python3 -c "import sys; sys.path.insert(0, '.'); from core import ai_helper" 2>/dev/null && echo "  ✓ core.ai_helper" || { echo "  ✗ core.ai_helper"; ((errors++)); }
echo ""

# Syntax checks
echo "✓ Syntax:"
bash -n auraos.sh 2>/dev/null && echo "  ✓ auraos.sh bash syntax" || { echo "  ✗ auraos.sh bash syntax"; ((errors++)); }
python3 -m py_compile core/ai_helper.py 2>/dev/null && echo "  ✓ core/ai_helper.py" || { echo "  ✗ core/ai_helper.py"; ((errors++)); }
python3 -m py_compile core/key_store.py 2>/dev/null && echo "  ✓ core/key_store.py" || { echo "  ✗ core/key_store.py"; ((errors++)); }
python3 -m py_compile auraos_terminal.py 2>/dev/null && echo "  ✓ auraos_terminal.py" || { echo "  ✗ auraos_terminal.py"; ((errors++)); }
echo ""

# Final result
echo "============================================"
if [ $errors -eq 0 ]; then
    echo "✅ All checks passed!"
    echo ""
    echo "To onboard an API key:"
    echo "  ./auraos.sh keys onboard"
    echo ""
    echo "To test AI functionality:"
    echo "  python3 scripts/test_ai_terminal.py"
    echo ""
    echo "For detailed docs:"
    echo "  cat AUDIT_AI_INTEGRATION.md"
    echo "  cat QUICK_REFERENCE_AI.md"
    exit 0
else
    echo "❌ $errors error(s) found. Please review above."
    exit 1
fi

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$REPO_ROOT"

echo "🔍 AI Integration Repeatability Audit"
echo "======================================"
echo "Repo root: $REPO_ROOT"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

passed=0
failed=0

check() {
    local desc=$1
    local cmd=$2
    
    echo -n "Checking: $desc ... "
    if eval "$cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        ((passed++))
    else
        echo -e "${RED}✗${NC}"
        ((failed++))
    fi
}

check_file_exists() {
    local file=$1
    local desc=$2
    echo -n "Checking: $desc ... "
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC}"
        ((passed++))
    else
        echo -e "${RED}✗ (missing: $file)${NC}"
        ((failed++))
    fi
}

check_syntax() {
    local file=$1
    local desc=$2
    echo -n "Checking: $desc ... "
    if bash -n "$SCRIPT_DIR/$file" 2>&1; then
        echo -e "${GREEN}✓${NC}"
        ((passed++))
    else
        echo -e "${RED}✗${NC}"
        ((failed++))
    fi
}

# File existence checks
echo "📁 Files Added/Modified:"
check_file_exists "core/key_store.py" "core/key_store.py exists"
check_file_exists "core/api_key_cli.py" "core/api_key_cli.py exists"
check_file_exists "scripts/test_ai_terminal.py" "scripts/test_ai_terminal.py exists"
check_file_exists "core/ai_helper.py" "core/ai_helper.py exists"
check_file_exists "auraos_terminal.py" "auraos_terminal.py exists"
check_file_exists "auraos_daemon/daemon.py" "auraos_daemon/daemon.py exists"
check_file_exists "auraos.sh" "auraos.sh exists"
echo ""

# Syntax checks
echo "✓ Syntax Checks:"
check_syntax "auraos.sh" "auraos.sh bash syntax"
python3 -m py_compile core/ai_helper.py 2>&1 || true
check "core/ai_helper.py Python syntax" "python3 -m py_compile core/ai_helper.py"
check "core/key_store.py Python syntax" "python3 -m py_compile core/key_store.py"
check "core/api_key_cli.py Python syntax" "python3 -m py_compile core/api_key_cli.py"
check "auraos_terminal.py Python syntax" "python3 -m py_compile auraos_terminal.py"
echo ""

# auraos.sh command checks
echo "📋 auraos.sh Commands:"
check "auraos.sh has 'keys onboard' command" "grep -q 'cmd_keys_onboard' 'auraos.sh'"
check "auraos.sh help mentions 'keys onboard'" "grep -q 'keys onboard' 'auraos.sh' && grep -q 'Interactive API key onboarding' 'auraos.sh'"
check "auraos.sh handles 'onboard' alias" "grep -q \"'onboard')\" 'auraos.sh'"
echo ""

# Module imports (with repo path)
echo "🔗 Module Imports:"
check "core.key_store imports cleanly" "python3 -c \"import sys; sys.path.insert(0, '.'); from core import key_store\""
check "core.api_key_cli imports cleanly" "python3 -c \"import sys; sys.path.insert(0, '.'); from core import api_key_cli\""
check "core.ai_helper imports cleanly" "python3 -c \"import sys; sys.path.insert(0, '.'); from core import ai_helper\""
echo ""

# Quick functional tests
echo "🧪 Functional Checks:"
check "key_store basic operations" "python3 scripts/test_ai_terminal.py 2>&1 | grep -q 'key_store tests'"
check "interpret_request_to_json fallbacks" "python3 scripts/test_ai_terminal.py 2>&1 | grep -q 'interpret_request_to_json fallbacks'"
echo ""

# Help text
echo "📖 Documentation:"
check_file_exists "AUDIT_AI_INTEGRATION.md" "AUDIT_AI_INTEGRATION.md exists"
check_file_exists "QUICK_REFERENCE_AI.md" "QUICK_REFERENCE_AI.md exists"
echo ""

# Summary
echo "======================================"
echo -e "Results: ${GREEN}$passed passed${NC}, ${RED}$failed failed${NC}"
echo ""

if [ $failed -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! AI integration is repeatable via auraos.sh.${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Some checks failed. Review the output above.${NC}"
    exit 1
fi
