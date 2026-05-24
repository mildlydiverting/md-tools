#!/usr/bin/env python3
"""
fix_yarle_frontmatter.py — v1.0
Fixes YAML frontmatter in Yarle-exported .md files.

Covers:
  /yarle 2/
  /yarle-test-1/

What it fixes:
  1. Renames created-at  -> created
  2. Renames last-updated-at -> modified
     (dates are already ISO 8601, no conversion needed)
  3. Converts broken tags block to valid YAML list, stripping # prefixes
     FROM:
       tags: 
       ["#zapier"]
     TO:
       tags:
         - zapier
  4. Handles both split-line and inline JSON array forms:
       tags: ["#zapier", "#ifttt"]  ->  tags:\n  - zapier\n  - ifttt

DRY RUN by default — prints proposed changes, writes nothing.
Pass --write to apply changes.
Pass --verbose to see unchanged files too.

Usage:
    python3 fix_yarle_frontmatter.py [--write] [--verbose]
"""

import re
import sys
import json
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

VAULT_ROOT = Path(
    "/Users/kimplowright/Library/Mobile Documents/"
    "iCloud~md~obsidian/Documents/art-reference"
)

FOLDERS = [
    VAULT_ROOT / "yarle 2",
    VAULT_ROOT / "yarle-test-1",
]

WRITE   = "--write" in sys.argv
VERBOSE = "--verbose" in sys.argv

# ── Helpers ───────────────────────────────────────────────────────────────────

# Matches JSON array of tag strings, with or without # prefixes
# e.g. ["#zapier"]  or  ["#zapier", "#ifttt"]  or  ["zapier"]
JSON_TAGS_RE = re.compile(r'^\s*\[([^\]]*)\]\s*$')


def parse_json_tags(array_str: str) -> list[str]:
    """
    Parse a JSON-ish tag array string into clean tag names.
    Strips # prefixes. Returns [] if unparseable.
    e.g. '["#zapier", "#ifttt"]' -> ['zapier', 'ifttt']
    """
    try:
        tags = json.loads(array_str.strip())
        if isinstance(tags, list):
            return [str(t).lstrip('#').strip() for t in tags if str(t).strip()]
    except (json.JSONDecodeError, ValueError):
        # Try stripping outer brackets and splitting manually
        inner = array_str.strip().lstrip('[').rstrip(']')
        parts = [p.strip().strip('"').strip("'").lstrip('#').strip()
                 for p in inner.split(',')]
        return [p for p in parts if p]
    return []


def tags_to_yaml(tags: list[str]) -> str:
    """Convert list of tag strings to YAML list block."""
    return "tags:\n" + "".join(f"  - {t}\n" for t in tags)


def fix_frontmatter(text: str) -> tuple[str, list[str]]:
    """
    Parse and fix frontmatter. Returns (new_text, changes).
    If no changes needed, new_text == text.
    """
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

        # 1. Rename created-at -> created
        if line.startswith("created-at:"):
            line = "created:" + line[len("created-at:"):]
            changes.append("  created-at → created")

        # 2. Rename last-updated-at -> modified
        elif line.startswith("last-updated-at:"):
            line = "modified:" + line[len("last-updated-at:"):]
            changes.append("  last-updated-at → modified")

        # 3. Fix tags block
        # Case A: tags on its own line, JSON array on next line
        elif re.match(r'^tags:\s*$', line):
            # Look ahead for the JSON array line
            j = i + 1
            # Skip blank lines between tags: and the array
            while j < len(lines) and lines[j].strip() == "":
                j += 1

            if j < len(lines) and JSON_TAGS_RE.match(lines[j]):
                tags = parse_json_tags(lines[j])
                if tags:
                    yaml_tags = tags_to_yaml(tags)
                    # yaml_tags ends with \n; split back to lines for new_lines
                    new_lines.extend(yaml_tags.rstrip("\n").split("\n"))
                    changes.append(f"  tags JSON array → YAML list: {tags}")
                    i = j + 1  # skip the array line
                    continue
                else:
                    # Unparseable — leave as empty list
                    new_lines.append("tags: []")
                    changes.append("  tags: unparseable array → tags: []")
                    i = j + 1
                    continue
            else:
                # No array follows — just pass through
                new_lines.append(line)
                i += 1
                continue

        # Case B: inline JSON array — tags: ["#zapier"]
        elif re.match(r'^tags:\s*\[', line):
            m = re.match(r'^tags:\s*(\[.*\])\s*$', line)
            if m:
                tags = parse_json_tags(m.group(1))
                if tags:
                    yaml_tags = tags_to_yaml(tags)
                    new_lines.extend(yaml_tags.rstrip("\n").split("\n"))
                    changes.append(f"  tags inline JSON → YAML list: {tags}")
                    i += 1
                    continue

        new_lines.append(line)
        i += 1

    new_fm   = "\n".join(new_lines)
    new_text = "---" + new_fm + body

    # Deduplicate change messages
    seen, deduped = set(), []
    for c in changes:
        if c not in seen:
            seen.add(c)
            deduped.append(c)

    return new_text, deduped


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    md_files = []
    for folder in FOLDERS:
        if folder.exists():
            md_files.extend(sorted(folder.rglob("*.md")))
        else:
            print(f"WARNING: folder not found: {folder}")

    changed = unchanged = errors = 0

    print(f"{'DRY RUN' if not WRITE else 'WRITING'} — scanning {len(md_files)} files\n")

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
