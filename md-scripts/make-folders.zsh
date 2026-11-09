#!/bin/zsh
# ============================================================
# make-folders.zsh
# Creates a folder structure from a plain text definition file.
#
# Usage:
#   ./make-folders.zsh <definition-file> [root-directory]
#
# If root-directory is not given, folders are created in the
# current working directory.
#
# Definition file format:
#   - One folder path per line
#   - Use / to indicate nesting
#   - Blank lines and lines starting with # are ignored
#   - Leading/trailing whitespace is trimmed
#
# Example definition file (books.txt):
#
#   # My book library
#   art - practice/drawing
#   art - practice/painting
#   art - theory + history/art history
#   fiction + literature
#   fiction + literature/smut
#   _inbox
#
# Options:
#   --dry-run    Show what would be created without creating anything
#   --help       Show this help message
#
# Version: 1.0 — 2026-03-18
# ============================================================

set -uo pipefail

# --- colours (suppressed if not a terminal) ---
if [[ -t 1 ]]; then
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    RED='\033[0;31m'
    DIM='\033[0;90m'
    RESET='\033[0m'
else
    GREEN='' YELLOW='' RED='' DIM='' RESET=''
fi

# --- help ---
show_help() {
    sed -n '2,/^# ====/{ /^# ====/d; s/^# \{0,1\}//; p }' "$0"
    exit 0
}

# --- parse args ---
DRY_RUN=false
DEFINITION_FILE=""
ROOT_DIR=""

for arg in "$@"; do
    case "$arg" in
        --dry-run)  DRY_RUN=true ;;
        --help|-h)  show_help ;;
        *)
            if [[ -z "$DEFINITION_FILE" ]]; then
                DEFINITION_FILE="$arg"
            elif [[ -z "$ROOT_DIR" ]]; then
                ROOT_DIR="$arg"
            else
                echo "${RED}Error: too many arguments.${RESET}" >&2
                echo "Usage: $0 <definition-file> [root-directory]" >&2
                exit 1
            fi
            ;;
    esac
done

# --- validate ---
if [[ -z "$DEFINITION_FILE" ]]; then
    echo "${RED}Error: no definition file provided.${RESET}" >&2
    echo "Usage: $0 <definition-file> [root-directory]" >&2
    echo "Run $0 --help for details." >&2
    exit 1
fi

if [[ ! -f "$DEFINITION_FILE" ]]; then
    echo "${RED}Error: definition file not found: ${DEFINITION_FILE}${RESET}" >&2
    exit 1
fi

if [[ -z "$ROOT_DIR" ]]; then
    ROOT_DIR="."
fi

# --- process ---
created=0
skipped=0
errors=0

echo ""
if $DRY_RUN; then
    echo "${YELLOW}DRY RUN — nothing will be created${RESET}"
    echo ""
fi

while IFS= read -r line || [[ -n "$line" ]]; do
    # trim leading/trailing whitespace
    line="${line## }"
    line="${line%% }"

    # skip blank lines and comments
    [[ -z "$line" ]] && continue
    [[ "$line" == \#* ]] && continue

    target="${ROOT_DIR}/${line}"

    if [[ -d "$target" ]]; then
        echo "${DIM}  exists:  ${target}${RESET}"
        ((skipped++))
    elif $DRY_RUN; then
        echo "${GREEN}  create:  ${target}${RESET}"
        ((created++))
    else
        if mkdir -p "$target" 2>/dev/null; then
            echo "${GREEN}  create:  ${target}${RESET}"
            ((created++))
        else
            echo "${RED}  FAILED:  ${target}${RESET}" >&2
            ((errors++))
        fi
    fi
done < "$DEFINITION_FILE"

# --- summary ---
echo ""
echo "---"
if $DRY_RUN; then
    echo "Would create: ${created}  |  Already exist: ${skipped}  |  Errors: ${errors}"
else
    echo "Created: ${created}  |  Already existed: ${skipped}  |  Errors: ${errors}"
fi
echo ""
