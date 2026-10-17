#!/usr/bin/env python3
"""
Recursively add a frontmatter property to markdown files that lack it.

Works on the text directly (no YAML parser), so existing formatting,
comments and key order are left exactly as they were.

Examples:
    python add_frontmatter_property.py ~/notes --key status --value draft --dry-run
    python add_frontmatter_property.py ~/notes --key status --value draft
    python add_frontmatter_property.py ~/notes --key tags --value "[]" --create-frontmatter
"""

import argparse
import re
import sys
from pathlib import Path


def find_frontmatter(lines):
    """Return the index of the closing delimiter, or None if there's no frontmatter."""
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            return i
    return None


def has_key(lines, end, key):
    """Check for a top-level key inside the frontmatter block."""
    pattern = re.compile(rf"^{re.escape(key)}\s*:")
    return any(pattern.match(line) for line in lines[1:end])


def process_file(path, key, value, create_frontmatter, dry_run):
    """Return 'added', 'exists', 'no-frontmatter' or 'created'."""
    # newline="" keeps the file's existing line endings intact
    with open(path, "r", encoding="utf-8", newline="") as f:
        text = f.read()

    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines(keepends=True)
    stripped = [line.rstrip("\r\n") for line in lines]
    new_line = f"{key}: {value}{newline}"

    end = find_frontmatter(stripped)

    if end is None:
        if not create_frontmatter:
            return "no-frontmatter"
        new_text = f"---{newline}{new_line}---{newline}{text}"
        status = "created"
    elif has_key(stripped, end, key):
        return "exists"
    else:
        # Make sure the line before the closing delimiter ends in a newline
        if not lines[end - 1].endswith(("\n", "\r")):
            lines[end - 1] += newline
        lines.insert(end, new_line)
        new_text = "".join(lines)
        status = "added"

    if not dry_run:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(new_text)
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", type=Path, help="Folder to search recursively")
    parser.add_argument("--key", required=True, help="Frontmatter property name")
    parser.add_argument("--value", required=True, help="Value to write, as YAML (e.g. draft, 2026-09-30, \"[]\")")
    parser.add_argument("--create-frontmatter", action="store_true",
                        help="Add a frontmatter block to files that don't have one")
    parser.add_argument("--include-hidden", action="store_true",
                        help="Also search hidden folders (.obsidian, .git, .trash etc.)")
    parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing")
    args = parser.parse_args()

    if not args.folder.is_dir():
        sys.exit(f"Not a folder: {args.folder}")

    counts = {"added": 0, "created": 0, "exists": 0, "no-frontmatter": 0, "error": 0}

    for path in sorted(args.folder.rglob("*.md")):
        relative = path.relative_to(args.folder)
        if not args.include_hidden and any(part.startswith(".") for part in relative.parts):
            continue
        try:
            result = process_file(path, args.key, args.value, args.create_frontmatter, args.dry_run)
        except (OSError, UnicodeDecodeError) as e:
            print(f"error           {relative}: {e}")
            counts["error"] += 1
            continue
        counts[result] += 1
        if result in ("added", "created", "no-frontmatter"):
            print(f"{result:<15} {relative}")

    prefix = "Would have changed" if args.dry_run else "Changed"
    print(
        f"\n{prefix} {counts['added'] + counts['created']} file(s). "
        f"Already had '{args.key}': {counts['exists']}. "
        f"Skipped (no frontmatter): {counts['no-frontmatter']}. "
        f"Errors: {counts['error']}."
    )


if __name__ == "__main__":
    main()
