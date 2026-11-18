#!/usr/bin/env bash
# date-stamp-index-files.sh
#
# Finds chat-index CSVs and project-summary Markdown files under a root folder
# and appends each file's CREATION date (yyyy-mm-dd) to its name, before the
# extension:
#     foo-chat-index.csv      ->  foo-chat-index-2026-05-20.csv
#     foo-project-summary.md  ->  foo-project-summary-2026-06-25.md
#
# Dry run by default: nothing is renamed until you pass --apply.
# macOS: uses BSD `stat -f %SB` (file birth time). Falls back to GNU stat
# (`stat -c %W`) so the script can be tested on Linux.
#
# Usage:
#   date-stamp-index-files.sh [--apply] [--root DIR] [--exclude NAME]... [--sep STR]
#
# Options:
#   --apply         actually rename (default is a dry run)
#   --root DIR      folder to search (default: $DEV_ROOT, else ~/Development)
#   --exclude NAME  extra directory NAME to skip (repeatable). Always skipped:
#                   _development-notes, _meta, node_modules, .git, .venv, venv
#   --sep STR       text between name and date (default: "-")
#
# Environment overrides:
#   DEV_ROOT        default for --root
#   NAME_PATTERNS   space-separated find -name patterns
#                   (default: "*-summary.md *chat-index*.csv")
#
# Files already ending in a yyyy-mm-dd date, or whose target name already
# exists, are skipped and reported.

set -u

ROOT="${DEV_ROOT:-$HOME/Development}"
APPLY=0
SEP="-"
PATTERNS="${NAME_PATTERNS:-*-summary.md *chat-index*.csv}"
EXCLUDES="_development-notes _meta node_modules .git .venv venv"

while [ $# -gt 0 ]; do
  case "$1" in
    --apply)   APPLY=1 ;;
    --root)    shift; ROOT="${1:?--root needs a folder}" ;;
    --exclude) shift; EXCLUDES="$EXCLUDES ${1:?--exclude needs a name}" ;;
    --sep)     shift; SEP="${1-}" ;;
    -h|--help) sed -n '2,32p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

[ -d "$ROOT" ] || { echo "Root not found: $ROOT" >&2; exit 1; }

birth_date() {  # prints yyyy-mm-dd, or nothing if unavailable
  local f="$1" d
  if [ "$(uname)" = "Darwin" ]; then
    d=$(stat -f '%SB' -t '%Y-%m-%d' "$f" 2>/dev/null)
    [ -n "$d" ] && echo "$d"
    return
  fi
  d=$(stat -c '%W' "$f" 2>/dev/null)
  if [ -n "$d" ] && [ "$d" != "0" ] && [ "$d" != "-" ]; then
    date -d "@$d" '+%Y-%m-%d' 2>/dev/null || date -r "$d" '+%Y-%m-%d' 2>/dev/null
  fi
}

# Build the find expression: prune excluded directories, match name patterns.
prune=()
for e in $EXCLUDES; do prune+=( -name "$e" -o ); done
names=()
for p in $PATTERNS; do names+=( -name "$p" -o ); done
unset 'prune[${#prune[@]}-1]' 'names[${#names[@]}-1]'

count=0; skipped=0
while IFS= read -r f; do
  dir=$(dirname "$f"); file=$(basename "$f")
  ext="${file##*.}"; base="${file%.*}"

  if [[ "$base" =~ [0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    echo "skip (already dated)  $f"; skipped=$((skipped+1)); continue
  fi
  d=$(birth_date "$f")
  if [ -z "$d" ]; then
    echo "skip (no creation date available)  $f"; skipped=$((skipped+1)); continue
  fi
  new="$dir/${base}${SEP}${d}.${ext}"
  if [ -e "$new" ]; then
    echo "skip (target exists)  $new"; skipped=$((skipped+1)); continue
  fi
  if [ "$APPLY" -eq 1 ]; then
    mv -n -- "$f" "$new" && echo "renamed  $f"$'\n'"      ->  $new"
  else
    echo "would rename  $f"$'\n'"          ->  $new"
  fi
  count=$((count+1))
done < <(find "$ROOT" \( "${prune[@]}" \) -prune -o -type f \( "${names[@]}" \) -print | sort)

echo
if [ "$APPLY" -eq 1 ]; then echo "Done: $count renamed, $skipped skipped."
else echo "Dry run: $count would be renamed, $skipped skipped. Re-run with --apply to rename."; fi
