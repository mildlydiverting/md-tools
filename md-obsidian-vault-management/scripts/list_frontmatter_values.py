#!/usr/bin/env python3
"""
List all the distinct values of a frontmatter property across markdown files.

Requires PyYAML:  pip install pyyaml

Examples:
    python list_frontmatter_values.py ~/notes --key type
    python list_frontmatter_values.py ~/notes --key type --recursive --counts
    python list_frontmatter_values.py ~/notes --key tags -r > tags.txt
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("This script needs PyYAML. Install it with: pip install pyyaml")


def read_frontmatter(path):
    """Return the parsed frontmatter as a dict, or None if there isn't any."""
    with open(path, "r", encoding="utf-8-sig") as f:
        lines = f.read().splitlines()

    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            data = yaml.safe_load("\n".join(lines[1:i]))
            return data if isinstance(data, dict) else None
    return None


def flatten(value):
    """Turn a property value into a flat list of strings.

    Handles scalars, lists (including nested ones, e.g. an unquoted
    [[wikilink]] which YAML reads as a list within a list), dates and empties.
    """
    if value is None:
        return ["(empty)"]
    if isinstance(value, (list, tuple)):
        if not value:
            return ["(empty list)"]
        items = []
        for v in value:
            items.extend(flatten(v))
        return items
    if hasattr(value, "isoformat"):  # dates and datetimes
        return [value.isoformat()]
    return [str(value).strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", type=Path, help="Folder containing markdown files")
    parser.add_argument("--key", required=True, help="Frontmatter property to look for")
    parser.add_argument("-r", "--recursive", action="store_true", help="Search subfolders too")
    parser.add_argument("--counts", action="store_true", help="Show how many files use each value")
    parser.add_argument("--files", action="store_true", help="Show which files use each value")
    parser.add_argument("--include-hidden", action="store_true",
                        help="Also search hidden folders (.obsidian, .git, .trash etc.)")
    args = parser.parse_args()

    if not args.folder.is_dir():
        sys.exit(f"Not a folder: {args.folder}")

    pattern = "**/*.md" if args.recursive else "*.md"
    values = defaultdict(set)  # value -> set of relative file paths
    scanned = with_key = errors = 0

    for path in sorted(args.folder.glob(pattern)):
        relative = path.relative_to(args.folder)
        if not args.include_hidden and any(part.startswith(".") for part in relative.parts):
            continue
        scanned += 1
        try:
            data = read_frontmatter(path)
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as e:
            print(f"error: {relative}: {e}", file=sys.stderr)
            errors += 1
            continue
        if not data or args.key not in data:
            continue
        with_key += 1
        for v in flatten(data[args.key]):
            values[v].add(str(relative))

    # Values go to stdout (easy to pipe); the summary goes to stderr
    for v in sorted(values, key=str.lower):
        if args.counts:
            print(f"{v}\t{len(values[v])}")
        else:
            print(v)
        if args.files:
            for f in sorted(values[v]):
                print(f"    {f}")

    print(
        f"\n{len(values)} distinct value(s) for '{args.key}'. "
        f"Files scanned: {scanned}. With property: {with_key}. Errors: {errors}.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
