#!/usr/bin/env python3
"""
inbox.py — insert one or more entries into _INBOX: in a TaskPaper file.

Accepts text as a positional argument or via stdin.

Input handling:
  - Lines already formatted (start with tab + dash): inserted as-is
  - Raw text lines: wrapped as a bare task with @date
  - Blank lines: skipped
  - If heading not found: prepended to top of file

Usage (terminal):
    python3 inbox.py "Buy more charcoal"
    echo "some text" | python3 inbox.py

Usage (Alfred — zsh, pipe via stdin):
    query=$1
    echo "$1" | python3 /path/to/inbox.py

File path: hardcoded default is ~/Library/Mobile Documents/com~hogbaysoftware~TaskPaper/Documents/todo.taskpaper or pass --file to override. (also passed from Alfred var:targetfile)

Inbox heading: defaults to _INBOX:, or set via environment variable 'inbox'.

Alfred Variables are
{var:targetfile}
{var:inbox}

"""

import argparse
import os
import sys
from datetime import date
from pathlib import Path

DEFAULT_FILE = Path(os.environ.get("targetfile", str(Path.home() / "Library/Mobile Documents/com~hogbaysoftware~TaskPaper/Documents/todo.taskpaper")))
INBOX_HEADING = os.environ.get("inbox", "_INBOX:")


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

    # Heading not found — prepend it with entries beneath it
    new_lines = [INBOX_HEADING + "\n"] + [e.rstrip("\n") + "\n" for e in entries]
    filepath.write_text("".join(new_lines + lines), encoding="utf-8")
    for entry in entries:
        print(f"Added (new inbox created): {entry.strip()}")


def main():
    parser = argparse.ArgumentParser(description="Append a task to a TaskPaper inbox.")
    parser.add_argument("text", nargs="?", help="Task text (or pipe via stdin)")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE, help="Path to TaskPaper file")
    args = parser.parse_args()

    if args.text:
        raw = args.text
    else:
        raw = sys.stdin.read()

    if not raw.strip():
        sys.exit("No input provided.")

    entries = prepare_lines(raw)
    if not entries:
        sys.exit("No valid entries found.")

    insert_into_inbox(args.file, entries)


if __name__ == "__main__":
    main()
