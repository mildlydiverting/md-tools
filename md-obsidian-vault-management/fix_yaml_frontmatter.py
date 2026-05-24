#!/usr/bin/env python3
"""
fix_yaml_frontmatter.py — v1.1
Fixes YAML frontmatter in obsidian-art-inbox .md files.

What it fixes:
  1. Renames creation_date / modification_date -> created / modified
  2. Converts human-readable dates ("June 26, 2022") to ISO 8601 ("2022-06-26")
  3. Strips trailing colons from title values  (title: My Title: -> title: My Title)
  4. Strips invalid timezone suffixes from created/modified values
     ("2025-08-07T11:46:13 (UTC +01:00)" -> "2025-08-07T11:46:13+01:00")
  5. Fixes unclosed opening quotes in title values
  6. Quotes title values containing a mid-value colon
     (title: EXERCISE: FIVE-STAR -> title: "EXERCISE: FIVE-STAR")

DRY RUN by default — prints proposed changes, writes nothing.
Pass --write to apply changes.
Pass --verbose to see unchanged files too.

Usage:
    python3 fix_yaml_frontmatter.py [--write] [--verbose]
"""

import re
import sys
import os
from pathlib import Path
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────

VAULT_ROOT = Path(
    "/Users/kimplowright/Library/Mobile Documents/"
    "iCloud~md~obsidian/Documents/art-reference"
)
INBOX = VAULT_ROOT / "obsidian-art-inbox"

WRITE = "--write" in sys.argv
VERBOSE = "--verbose" in sys.argv

# ── Helpers ───────────────────────────────────────────────────────────────────

HUMAN_DATE_RE = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{1,2},\s+\d{4}$"
)

# "(UTC +01:00)" or "(UTC +00:00)" or "(UTC -05:00)"
TZ_SUFFIX_RE = re.compile(r"\s+\(UTC\s+([+-]\d{2}:\d{2})\)$")

# Trailing colon at end of unquoted YAML scalar value
TRAILING_COLON_RE = re.compile(r"^(title:\s+)(.+):(\s*)$")

# Unclosed opening quote: title: "Some text  (no closing quote)
UNCLOSED_QUOTE_RE = re.compile(r'^(title:\s+)"([^"]+)(\s*)$')

# Unquoted title value containing a mid-value colon (not already quoted)
# Matches: title: EXERCISE: FIVE-STAR  but not  title: "already quoted"
MID_COLON_RE = re.compile(r'^(title:\s+)([^"\'][^:]*:[^:].*)$')


def parse_human_date(value: str) -> str | None:
    """'June 26, 2022' -> '2022-06-26'. Returns None if not parseable."""
    try:
        return datetime.strptime(value.strip(), "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def fix_tz_suffix(value: str) -> str:
    """'2025-08-07T11:46:13 (UTC +01:00)' -> '2025-08-07T11:46:13+01:00'"""
    m = TZ_SUFFIX_RE.search(value)
    if m:
        base = value[: m.start()]
        offset = m.group(1)
        return base + offset
    return value


def fix_frontmatter(text: str) -> tuple[str, list[str]]:
    """
    Parse and fix frontmatter in a markdown file.
    Returns (new_text, list_of_change_descriptions).
    If no changes, new_text == text.
    """
    # Must start with ---
    if not text.startswith("---"):
        return text, []

    end = text.find("\n---", 3)
    if end == -1:
        return text, []

    fm_raw = text[3:end]          # everything between the --- markers
    body = text[end:]              # from closing --- onwards

    lines = fm_raw.split("\n")
    new_lines = []
    changes = []

    for line in lines:
        original = line

        # 1. Rename creation_date -> created
        if line.startswith("creation_date:"):
            line = "created:" + line[len("creation_date:"):]
            changes.append(f"  creation_date → created")

        # 2. Rename modification_date -> modified
        if line.startswith("modification_date:"):
            line = "modified:" + line[len("modification_date:"):]
            changes.append(f"  modification_date → modified")

        # 3. Convert human-readable dates on created/modified lines
        for key in ("created:", "modified:"):
            if line.startswith(key):
                value = line[len(key):].strip()
                iso = parse_human_date(value)
                if iso:
                    line = f"{key} {iso}"
                    changes.append(f"  date '{value}' → '{iso}'")
                else:
                    # Try timezone suffix fix
                    fixed = fix_tz_suffix(value)
                    if fixed != value:
                        line = f"{key} {fixed}"
                        changes.append(f"  tz suffix '{value}' → '{fixed}'")

        # 4. Strip trailing colon from title value
        m = TRAILING_COLON_RE.match(line)
        if m:
            line = m.group(1) + m.group(2) + m.group(3)
            changes.append(f"  trailing colon removed from title")

        # 5. Fix unclosed opening quote on title
        m = UNCLOSED_QUOTE_RE.match(line)
        if m:
            # Close the quote properly
            line = f'{m.group(1)}"{m.group(2)}"{m.group(3)}'
            changes.append(f"  unclosed quote fixed in title")

        # 6. Quote unquoted title values containing a mid-value colon
        m = MID_COLON_RE.match(line)
        if m:
            value = m.group(2).strip()
            line = f'{m.group(1)}"{value}"'
            changes.append(f"  mid-colon title quoted: '{value}'")

        new_lines.append(line)

    new_fm = "\n".join(new_lines)
    new_text = "---" + new_fm + body

    # Deduplicate change messages while preserving order
    seen = set()
    deduped = []
    for c in changes:
        if c not in seen:
            seen.add(c)
            deduped.append(c)

    return new_text, deduped


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    md_files = sorted(INBOX.rglob("*.md"))

    changed = 0
    unchanged = 0
    errors = 0

    print(f"{'DRY RUN' if not WRITE else 'WRITING'} — scanning {len(md_files)} files in:")
    print(f"  {INBOX}\n")

    for path in md_files:
        try:
            original = path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"ERROR reading {path.name}: {e}")
            errors += 1
            continue

        fixed, changes = fix_frontmatter(original)

        if changes:
            changed += 1
            rel = path.relative_to(VAULT_ROOT)
            print(f"{'WOULD FIX' if not WRITE else 'FIXED'}: {rel}")
            for c in changes:
                print(c)
            if WRITE:
                try:
                    path.write_text(fixed, encoding="utf-8")
                except Exception as e:
                    print(f"  ERROR writing: {e}")
                    errors += 1
            print()
        else:
            unchanged += 1
            if VERBOSE:
                print(f"  ok: {path.name}")

    print(f"── Summary ──────────────────────────")
    print(f"  Files scanned : {len(md_files)}")
    print(f"  Need fixing   : {changed}")
    print(f"  Already clean : {unchanged}")
    print(f"  Errors        : {errors}")
    if not WRITE and changed > 0:
        print(f"\n  Run with --write to apply changes.")


if __name__ == "__main__":
    main()
