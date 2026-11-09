#!/bin/zsh
# open-urls.sh — open a list of URLs in the default browser, gently
#
# Usage:
#   open-urls.sh "text containing URLs"      # from an argument (e.g. Alfred {query})
#   pbpaste | open-urls.sh                   # from stdin
#   open-urls.sh                             # no input: falls back to the clipboard
#   open-urls.sh --dry-run "..."             # list what would open, open nothing
#
# Behaviour:
#   - Pulls out anything starting http:// or https:// (one per line or mixed in text)
#   - Lines starting www. get https:// added
#   - Cleans copy-paste damage: en/em dashes back to "--", non-breaking and
#     zero-width spaces removed, trailing punctuation from prose stripped
#   - Removes duplicates, keeps original order
#   - Opens in batches with pauses, so browsers and sites don't get swamped
#   - Asks before starting if there are more than MAX_WITHOUT_ASKING
#   - Reports any URL that macOS refused to open
#
# Changelog
#   v1.1  2026-11-07  Gentle rate limit (batches + pauses); fix smart-dash and
#                     invisible-whitespace damage; report failed opens
#   v1.0  2026-11-07  First version: arg/stdin/clipboard input, dedupe, dry run, confirm over limit

set -euo pipefail

# --- Settings ---------------------------------------------------------------
MAX_WITHOUT_ASKING=10
DELAY=1.5          # seconds between each URL
BATCH_SIZE=8       # URLs per batch
BATCH_PAUSE=20     # seconds between batches
# ---------------------------------------------------------------------------

dry_run=false
if [[ "${1:-}" == "--dry-run" || "${1:-}" == "-n" ]]; then
  dry_run=true
  shift
fi

# 1. Get the input: argument, then stdin, then clipboard
if [[ -n "${1:-}" ]]; then
  input="$*"
elif [[ ! -t 0 ]]; then
  input="$(cat)"
else
  input="$(pbpaste)"
fi

# 2. Repair copy-paste damage
#    en dash / em dash -> "--" (smart punctuation turns "--" into a dash)
#    non-breaking space, zero-width space/joiners, byte-order mark -> removed
input="${input//$'–'/--}"
input="${input//$'—'/--}"
for ch in $' ' $'​' $'‌' $'‍' $'﻿'; do
  input="${input//$ch/ }"
done

# 3. Extract, tidy and dedupe the URLs
urls=("${(@f)$(
  print -r -- "$input" \
    | sed -E 's/^[[:space:]]*(www\.)/https:\/\/\1/' \
    | grep -Eo 'https?://[^[:space:]<>"]+' \
    | sed -E 's/[]).,;:'"'"'">]+$//' \
    | awk '!seen[$0]++'
)}")

# Empty result gives one empty element; clear it
[[ "${urls[1]:-}" == "" ]] && urls=()

count=${#urls}

if (( count == 0 )); then
  echo "No URLs found."
  exit 0
fi

if $dry_run; then
  echo "Would open $count URL(s):"
  printf '  %s\n' "${urls[@]}"
  exit 0
fi

# 4. Check before starting a big run (dialog works from Alfred, which has no terminal)
if (( count > MAX_WITHOUT_ASKING )); then
  batches=$(( (count + BATCH_SIZE - 1) / BATCH_SIZE ))
  minutes=$(( (count * DELAY + (batches - 1) * BATCH_PAUSE) / 60 + 1 ))
  msg="Open $count URLs?\n\n$batches batches of $BATCH_SIZE, about $minutes min."
  answer=$(osascript -e "button returned of (display dialog \"$msg\" buttons {\"Cancel\", \"Open\"} default button \"Open\" with title \"Open URLs\")" 2>/dev/null || echo "Cancel")
  if [[ "$answer" != "Open" ]]; then
    echo "Cancelled."
    exit 0
  fi
fi

# 5. Open them, gently
failed=()
i=0
for url in "${urls[@]}"; do
  (( i += 1 ))
  open "$url" 2>/dev/null || failed+=("$url")
  if (( i < count )); then
    if (( i % BATCH_SIZE == 0 )); then
      sleep $BATCH_PAUSE
    else
      sleep $DELAY
    fi
  fi
done

echo "Opened $(( count - ${#failed} )) of $count URL(s)."
if (( ${#failed} > 0 )); then
  echo "Couldn't open:"
  printf '  %s\n' "${failed[@]}"
fi
