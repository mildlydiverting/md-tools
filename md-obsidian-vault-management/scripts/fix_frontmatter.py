#!/usr/bin/env python3
"""
fix_frontmatter.py — v1.0
General-purpose YAML frontmatter fixer for Obsidian vaults.
Combines all fixes from fix_yaml_frontmatter.py and fix_yarle_frontmatter.py.

What it fixes:
  1. Renames creation_date / created-at  -> created
  2. Renames modification_date / last-updated-at / modified_date -> modified
  3. Converts human-readable dates ("June 26, 2022") to ISO 8601 ("2022-06-26")
  4. Strips invalid timezone suffixes ("2025-08-07T11:46:13 (UTC +01:00)" -> "2025-08-07T11:46:13+01:00")
  5. Strips trailing colons from title values
  6. Quotes title values containing a mid-value colon
  7. Fixes unclosed opening quotes in title values
  8. Converts broken Yarle-style tags block to valid YAML list, stripping # prefixes
     FROM:  tags: \n["#zapier"]
     TO:    tags:\n  - zapier
  9. Converts inline JSON tag arrays: tags: ["#foo"] -> tags:\n  - foo

Deliberately leaves alone:
  - source-url, pinterest-link, pinterest-board, evernote-notebook
  - Any key not listed above

DRY RUN by default — prints proposed changes, writes nothing.
Pass --write to apply changes.
Pass --verbose to see unchanged files too.
Pass --folder <path> to override the target folder (default: see FOLDER below).

Usage:
    python3 fix_frontmatter.py [--write] [--verbose] [--folder /path/to/folder]
"""

import re
import sys
import json
from pathlib import Path
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────

# Default target — override with --folder
DEFAULT_FOLDER = Path(
    "/Users/kimplowright/Library/CloudStorage/Dropbox/obsidian/obsidian vault/obsidian-general-to-import"
)

WRITE   = "--write" in sys.argv
VERBOSE = "--verbose" in sys.argv

# Parse optional --folder argument
FOLDER = DEFAULT_FOLDER
if "--folder" in sys.argv:
    idx = sys.argv.index("--folder")
    if idx + 1 < len(sys.argv):
        FOLDER = Path(sys.argv[idx + 1])

# ── Regexes ───────────────────────────────────────────────────────────────────

HUMAN_DATE_RE   = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{1,2},\s+\d{4}$"
)
TZ_SUFFIX_RE    = re.compile(r"\s+\(UTC\s+([+-]\d{2}:\d{2})\)$")
TRAILING_COLON_RE = re.compile(r"^(title:\s+)(.+):(\s*)$")
UNCLOSED_QUOTE_RE = re.compile(r'^(title:\s+)"([^"]+)(\s*)$')
MID_COLON_RE    = re.compile(r'^(title:\s+)([^"\'"][^:]*:[^:].*)$')
JSON_TAGS_RE    = re.compile(r'^\s*\[([^\]]*)\]\s*$')

# Keys to rename -> canonical form
KEY_RENAMES = {
    "creation_date":    "created",
    "created-at":       "created",
    "modification_date": "modified",
    "modified_date":    "modified",
    "last-updated-at":  "modified",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_human_date(value: str) -> str | None:
    try:
        return datetime.strptime(value.strip(), "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def fix_tz_suffix(value: str) -> str:
    m = TZ_SUFFIX_RE.search(value)
    if m:
        return value[:m.start()] + m.group(1)
    return value


def parse_json_tags(array_str: str) -> list[str]:
    try:
        tags = json.loads(array_str.strip())
        if isinstance(tags, list):
            return [str(t).lstrip('#').strip() for t in tags if str(t).strip()]
    except (json.JSONDecodeError, ValueError):
        inner = array_str.strip().lstrip('[').rstrip(']')
        parts = [p.strip().strip('"').strip("'").lstrip('#').strip()
                 for p in inner.split(',')]
        return [p for p in parts if p]
    return []


def tags_to_yaml(tags: list[str]) -> str:
    return "tags:\n" + "".join(f"  - {t}\n" for t in tags)


# ── Core fixer ────────────────────────────────────────────────────────────────

def fix_frontmatter(text: str) -> tuple[str, list[str]]:
    if not text.startswith("---"):
        return text, []
    end = text.find("\n---", 3)
    if end == -1:
        return text, []

    fm_raw = text[3:end]
    body   = text[end:]
    lines  = fm_raw.split("\n")
    changes = []
    new_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # 1+2. Rename date keys
        for old_key, new_key in KEY_RENAMES.items():
            if line.startswith(f"{old_key}:"):
                line = f"{new_key}:" + line[len(old_key) + 1:]
                changes.append(f"  {old_key} → {new_key}")
                break

        # 3+4. Fix date values on created/modified lines
        for key in ("created:", "modified:"):
            if line.startswith(key):
                value = line[len(key):].strip()
                iso = parse_human_date(value)
                if iso:
                    line = f"{key} {iso}"
                    changes.append(f"  date '{value}' → '{iso}'")
                else:
                    fixed = fix_tz_suffix(value)
                    if fixed != value:
                        line = f"{key} {fixed}"
                        changes.append(f"  tz suffix stripped")

        # 5. Strip trailing colon from title value
        m = TRAILING_COLON_RE.match(line)
        if m:
            line = m.group(1) + m.group(2) + m.group(3)
            changes.append("  trailing colon removed from title")

        # 6. Quote title with mid-value colon
        m = MID_COLON_RE.match(line)
        if m:
            value = m.group(2).strip()
            line = f'{m.group(1)}"{value}"'
            changes.append(f"  mid-colon title quoted")

        # 7. Fix unclosed opening quote in title
        m = UNCLOSED_QUOTE_RE.match(line)
        if m:
            line = f'{m.group(1)}"{m.group(2)}"{m.group(3)}'
            changes.append("  unclosed quote fixed in title")

        # 8. Yarle-style tags: blank line, then JSON array on next line
        if re.match(r'^tags:\s*$', line):
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j < len(lines) and JSON_TAGS_RE.match(lines[j]):
                tags = parse_json_tags(lines[j])
                if tags:
                    new_lines.extend(tags_to_yaml(tags).rstrip("\n").split("\n"))
                    changes.append(f"  tags JSON array → YAML list: {tags}")
                    i = j + 1
                    continue
                else:
                    new_lines.append("tags: []")
                    changes.append("  tags: unparseable → tags: []")
                    i = j + 1
                    continue

        # 9. Inline JSON tag array: tags: ["#zapier"]
        elif re.match(r'^tags:\s*\[', line):
            m = re.match(r'^tags:\s*(\[.*\])\s*$', line)
            if m:
                tags = parse_json_tags(m.group(1))
                if tags:
                    new_lines.extend(tags_to_yaml(tags).rstrip("\n").split("\n"))
                    changes.append(f"  tags inline JSON → YAML list: {tags}")
                    i += 1
                    continue

        new_lines.append(line)
        i += 1

    new_text = "---" + "\n".join(new_lines) + body

    # Deduplicate change messages
    seen, deduped = set(), []
    for c in changes:
        if c not in seen:
            seen.add(c)
            deduped.append(c)

    return new_text, deduped


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not FOLDER.exists():
        print(f"ERROR: folder not found: {FOLDER}")
        sys.exit(1)

    md_files = sorted(FOLDER.rglob("*.md"))
    changed = unchanged = errors = 0

    print(f"{'DRY RUN' if not WRITE else 'WRITING'} — scanning {len(md_files)} files in:")
    print(f"  {FOLDER}\n")

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
            print(f"{'WOULD FIX' if not WRITE else 'FIXED'}: {path.relative_to(FOLDER.parent)}")
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
