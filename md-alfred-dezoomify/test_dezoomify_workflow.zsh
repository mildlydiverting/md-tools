#!/usr/bin/env zsh
# test_dezoomify_workflow.zsh — v1.0
#
# Runs each component of the dezoomify Alfred workflow from the Terminal
# so you can verify everything works before wiring it up in Alfred.
#
# Usage:
#   chmod +x test_dezoomify_workflow.zsh
#   ./test_dezoomify_workflow.zsh
#
# Run from the workflow folder (where get_browser_info.js lives).

set -e  # exit on first error

SCRIPT_DIR="${0:A:h}"  # absolute path to this script's directory
PASS="✅"
FAIL="❌"
WARN="⚠️ "
SEP="─────────────────────────────────────────────"

# ── Helpers ────────────────────────────────────────────────────────────────────

check() { echo "${PASS} $1" }
warn()  { echo "${WARN} $1" }
fail()  { echo "${FAIL} $1" }

section() {
    echo ""
    echo "$SEP"
    echo "  $1"
    echo "$SEP"
}

# ── 1. Preflight checks ────────────────────────────────────────────────────────

section "1 / Preflight"

# Check osascript
if command -v osascript &>/dev/null; then
    check "osascript found: $(which osascript)"
else
    fail "osascript not found — this should never happen on macOS"
    exit 1
fi

# Check Python 3
if command -v python3 &>/dev/null; then
    check "python3 found: $(python3 --version)"
else
    fail "python3 not found"
    exit 1
fi

# Check dezoomify-rs
DEZOOMIFY_BIN=""
for candidate in \
    "$SCRIPT_DIR/bin/dezoomify-rs" \
    "/opt/homebrew/bin/dezoomify-rs" \
    "/usr/local/bin/dezoomify-rs"
do
    if [[ -x "$candidate" ]]; then
        DEZOOMIFY_BIN="$candidate"
        break
    fi
done

if [[ -z "$DEZOOMIFY_BIN" ]]; then
    DEZOOMIFY_BIN=$(command -v dezoomify-rs 2>/dev/null || true)
fi

if [[ -n "$DEZOOMIFY_BIN" ]]; then
    check "dezoomify-rs found: $DEZOOMIFY_BIN"
    check "dezoomify-rs version: $($DEZOOMIFY_BIN --version 2>&1 | head -1)"
else
    fail "dezoomify-rs not found. Install with: brew install dezoomify-rs"
    exit 1
fi

# Check get_browser_info.js
if [[ -f "$SCRIPT_DIR/get_browser_info.js" ]]; then
    check "get_browser_info.js found"
else
    fail "get_browser_info.js not found in $SCRIPT_DIR"
    exit 1
fi

# Check dezoomify_save.py
if [[ -f "$SCRIPT_DIR/dezoomify_save.py" ]]; then
    check "dezoomify_save.py found"
else
    fail "dezoomify_save.py not found in $SCRIPT_DIR"
    exit 1
fi

# ── 2. JXA script test ─────────────────────────────────────────────────────────

section "2 / JXA browser info script"

echo "   Running get_browser_info.js via osascript..."
echo "   (Make sure Safari or Chrome has a tab open before continuing)"
echo ""
read -q "?   Press [y] to run, any other key to skip: "
echo ""

if [[ $REPLY == "y" ]]; then
    JXA_OUTPUT=$(osascript -l JavaScript "$SCRIPT_DIR/get_browser_info.js" 2>&1)
    JXA_EXIT=$?

    if [[ $JXA_EXIT -eq 0 ]]; then
        check "JXA script exited cleanly"
        echo "   Raw output:"
        echo "   $JXA_OUTPUT"
        echo ""

        # Try to parse as JSON using Python
        PARSED=$(python3 -c "
import json, sys
try:
    data = json.loads('''$JXA_OUTPUT''')
    v = data.get('alfredworkflow', {}).get('variables', {})
    print('URL:          ', v.get('url', '(empty)'))
    print('Title:        ', v.get('title', '(empty)'))
    st = v.get('selected_text', '')
    print('Selected text:', st[:60] + ('…' if len(st) > 60 else '') if st else '(none)')
except Exception as e:
    print('JSON parse error:', e)
    sys.exit(1)
" 2>&1)
        PARSE_EXIT=$?

        if [[ $PARSE_EXIT -eq 0 ]]; then
            check "JSON parsed successfully:"
            echo "$PARSED" | while IFS= read -r line; do echo "   $line"; done
        else
            fail "Could not parse output as JSON:"
            echo "   $PARSED"
        fi
    else
        fail "JXA script failed (exit $JXA_EXIT):"
        echo "   $JXA_OUTPUT"
        echo ""
        echo "   Common causes:"
        echo "   - No browser window open"
        echo "   - macOS Automation permission not granted for Terminal"
        echo "     → System Settings → Privacy & Security → Automation"
    fi
else
    warn "JXA test skipped"
fi

# ── 3. Automation permissions check ───────────────────────────────────────────

section "3 / macOS Automation permissions"

echo "   Checking whether Terminal can talk to Safari..."
SAFARI_CHECK=$(osascript -e 'tell application "Safari" to return name of window 1' 2>&1)
SAFARI_EXIT=$?
if [[ $SAFARI_EXIT -eq 0 ]]; then
    check "Terminal → Safari automation: OK"
else
    if echo "$SAFARI_CHECK" | grep -qi "not allowed"; then
        fail "Terminal → Safari automation: DENIED"
        echo "   Fix: System Settings → Privacy & Security → Automation → Terminal → Safari ✓"
    else
        warn "Safari check returned: $SAFARI_CHECK"
    fi
fi

echo ""
echo "   Checking whether Terminal can talk to Google Chrome..."
CHROME_CHECK=$(osascript -e 'tell application "Google Chrome" to return URL of active tab of window 1' 2>&1)
CHROME_EXIT=$?
if [[ $CHROME_EXIT -eq 0 ]]; then
    check "Terminal → Chrome automation: OK"
else
    if echo "$CHROME_CHECK" | grep -qi "not allowed"; then
        fail "Terminal → Chrome automation: DENIED"
        echo "   Fix: System Settings → Privacy & Security → Automation → Terminal → Google Chrome ✓"
    elif echo "$CHROME_CHECK" | grep -qi "no windows"; then
        warn "Chrome is running but has no windows open"
    else
        warn "Chrome not running or check inconclusive: $CHROME_CHECK"
    fi
fi

# ── 4. dezoomify-rs smoke test ─────────────────────────────────────────────────

section "4 / dezoomify-rs smoke test (IIIF sample image)"

echo "   This will attempt to download a small public IIIF test image."
echo "   Source: Yale Center for British Art (public IIIF endpoint)"
echo ""
read -q "?   Press [y] to run, any other key to skip: "
echo ""

if [[ $REPLY == "y" ]]; then
    TEST_URL="https://manifests.collections.yale.edu/ycba/obj/5005"
    TMPDIR=$(mktemp -d)
    OUTFILE="$TMPDIR/test_image.jpg"

    echo "   Running: dezoomify-rs $TEST_URL $OUTFILE"
    echo "   (This may take 10–30 seconds...)"
    echo ""

    "$DEZOOMIFY_BIN" "$TEST_URL" "$OUTFILE" 2>&1 | while IFS= read -r line; do
        echo "   $line"
    done
    DEZOOM_EXIT=${pipestatus[1]}

    if [[ $DEZOOM_EXIT -eq 0 ]] && [[ -f "$OUTFILE" ]]; then
        SIZE=$(du -sh "$OUTFILE" | cut -f1)
        check "dezoomify-rs downloaded image successfully ($SIZE)"
        echo "   Saved to: $OUTFILE"
        echo "   Opening in Preview..."
        open "$OUTFILE"
    else
        fail "dezoomify-rs failed or produced no output file"
        echo ""
        echo "   Note: IIIF endpoints sometimes change. If this URL fails,"
        echo "   try running dezoomify-rs manually against a known-good IIIF page."
    fi

    # Cleanup
    read -q "?   Delete the test download? [y/n]: "
    echo ""
    if [[ $REPLY == "y" ]]; then
        rm -rf "$TMPDIR"
        check "Test files cleaned up"
    else
        echo "   Test file kept at: $OUTFILE"
    fi
else
    warn "dezoomify-rs test skipped"
fi

# ── 5. Python script dry run ───────────────────────────────────────────────────

section "5 / Python script dry run"

echo "   Simulating the Alfred environment by setting env vars manually"
echo "   and running dezoomify_save.py with a fake URL (dezoomify-rs will"
echo "   fail, but we can verify the script loads and dialogs work)."
echo ""
read -q "?   Press [y] to run, any other key to skip: "
echo ""

if [[ $REPLY == "y" ]]; then
    export url="https://example.com/test"
    export page_title="Test Page — Dry Run"
    export selected_text="A test description"
    export save_folder="/tmp/dezoomify_test"
    export dezoomify_bin="$DEZOOMIFY_BIN"
    export image_format="jpg"

    echo ""
    echo "   Env vars set:"
    echo "   url=$url"
    echo "   page_title=$page_title"
    echo "   selected_text=$selected_text"
    echo "   save_folder=$save_folder"
    echo "   dezoomify_bin=$dezoomify_bin"
    echo ""
    echo "   A filename dialog should appear. Enter anything and click Save"
    echo "   (dezoomify-rs will then fail on the fake URL — that's expected)."
    echo ""

    python3 "$SCRIPT_DIR/dezoomify_save.py" 2>&1 || true

    warn "Expected failure on fake URL — if the filename dialog appeared, Python integration is working"
else
    warn "Python dry run skipped"
fi

# ── Summary ────────────────────────────────────────────────────────────────────

section "Done"
echo ""
echo "   If all checks passed, you're ready to wire this into Alfred."
echo "   See README.md for the step-by-step workflow setup."
echo ""
