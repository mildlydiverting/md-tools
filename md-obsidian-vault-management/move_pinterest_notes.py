#!/usr/bin/env python3
"""
move_pinterest_notes.py — v1.0 (2026-09-22)

Moves markdown files whose frontmatter has a non-empty `pinterest-link`
and/or `pinterest-board` value into a destination folder.

Dry run by default. Add --apply to actually move files.

Usage:
    python move_pinterest_notes.py SOURCE DEST            # dry run
    python move_pinterest_notes.py SOURCE DEST --apply    # move
    python move_pinterest_notes.py SOURCE DEST -r --apply # include subfolders

Requires: pyyaml  (pip install pyyaml)

Changelog:
    v1.0 — initial version
"""

import argparse
import shutil
import sys
from pathlib import Path

import yaml

KEYS = ("pinterest-link", "pinterest-board")


def read_frontmatter(path: Path):
    """Return the frontmatter as a dict, {} if none, or None if unparseable."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() in ("---", "..."):
            block = "\n".join(lines[1:i])
            try:
                data = yaml.safe_load(block)
            except yaml.YAMLError:
                return None
            return data if isinstance(data, dict) else {}
    return {}  # opening --- but no closing one


def has_value(v) -> bool:
    """True if v is something other than null / empty / whitespace."""
    if v is None:
        return False
    if isinstance(v, str):
        return v.strip().lower() not in ("", "null", "none", "~")
    if isinstance(v, (list, dict)):
        return any(has_value(x) for x in (v.values() if isinstance(v, dict) else v))
    return True


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    p.add_argument("source", type=Path)
    p.add_argument("dest", type=Path)
    p.add_argument("-r", "--recursive", action="store_true", help="include subfolders")
    p.add_argument("--apply", action="store_true", help="actually move files")
    args = p.parse_args()

    src, dest = args.source.resolve(), args.dest.resolve()
    if not src.is_dir():
        sys.exit(f"Source folder not found: {src}")

    files = src.rglob("*.md") if args.recursive else src.glob("*.md")
    moved, skipped, errors = 0, 0, []

    for f in sorted(files):
        if dest in f.parents:  # don't re-process files already in dest
            continue
        fm = read_frontmatter(f)
        if fm is None:
            errors.append(f)
            continue
        if not any(has_value(fm.get(k)) for k in KEYS):
            continue

        target = dest / f.name
        if target.exists():
            print(f"SKIP (exists in dest): {f.relative_to(src)}")
            skipped += 1
            continue

        print(f"{'MOVE' if args.apply else 'WOULD MOVE'}: {f.relative_to(src)}")
        if args.apply:
            dest.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(target))
        moved += 1

    print(f"\n{moved} file(s) {'moved' if args.apply else 'to move'}, "
          f"{skipped} skipped (name clash), {len(errors)} with unreadable frontmatter.")
    for e in errors:
        print(f"  YAML error: {e.relative_to(src)}")
    if not args.apply and moved:
        print("Dry run only — re-run with --apply to move them.")


if __name__ == "__main__":
    main()
