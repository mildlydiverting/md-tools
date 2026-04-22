#!/usr/bin/env python3
"""
inbox.py — insert one or more entries into _INBOX: in a TaskPaper file.

Reads from stdin (preferred) or first argument.

Input handling:
  - Lines already formatted (start with tab + dash): inserted as-is
  - Raw text lines: wrapped as a bare task with @date
  - Blank lines: skipped

Usage (Alfred — pipe via stdin):
    echo "$1" | python3 /path/to/inbox.py

Usage (direct):
    python3 inbox.py "Buy more charcoal"
    echo "	- Pre-formatted line @date(2026-04-22)" | python3 inbox.py
"""

import sys
from datetime import date
from pathlib import Path

FILE = Path.home() / "Library/Mobile Documents/com~hogbaysoftware~TaskPaper/Documents/todo.taskpaper"
INBOX_HEADING = "_INBOX:"


def format_raw(text: str) -> str:
    today = date.today().isoformat()
    return f"\t- {text.strip()} @date({today})"


def prepare_lines(raw_input: str) -> list[str]:
    lines = []
    for line in raw_input.splitlines():
        if not line.strip():
            continue
        if line.startswith("\t-") or line.startswith("\t\t"):
            lines.append(line)
        else:
            lines.append(format_raw(line))
    return lines


def insert_into_inbox(filepath: Path, entries: list[str]) -> None:
    if not filepath.exists():
        sys.exit(f"File not found: {filepath}")

    lines = filepath.read_text(encoding="utf-8").splitlines(keepends=True)

    for i, line in enumerate(lines):
        if line.strip() == INBOX_HEADING:
            for j, entry in enumerate(entries):
                lines.insert(i + 1 + j, entry.rstrip("\n") + "\n")
            filepath.write_text("".join(lines), encoding="utf-8")
            for entry in entries:
                print(f"Added: {entry.strip()}")
            return

    sys.exit(f"Could not find '{INBOX_HEADING}' in file.")


def main():
    if len(sys.argv) > 1:
        raw = sys.argv[1]
    else:
        raw = sys.stdin.read()

    if not raw.strip():
        sys.exit("No input provided.")

    entries = prepare_lines(raw)
    if not entries:
        sys.exit("No valid entries found.")

    insert_into_inbox(FILE, entries)


if __name__ == "__main__":
    main()
