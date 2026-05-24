#!/usr/bin/env python3
"""
extract_vault_tags.py
Extracts all unique tags from Obsidian vault frontmatter and outputs them
sorted alphabetically, with a count of how many files each tag appears in.

Usage:
    python extract_vault_tags.py --vault "/path/to/vault"
    python extract_vault_tags.py --vault "/path/to/vault" --output tags.csv
"""

# CHANGELOG
# v1.0.0 - Initial version

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path


def parse_frontmatter(content: str):
    if not content.startswith("---"):
        return None
    end = content.find("\n---", 3)
    if end == -1:
        return None
    return content[3:end].strip()


def extract_tags(frontmatter: str):
    tags = []
    lines = frontmatter.split("\n")
    in_tags_block = False
    inline_tags = re.compile(r'^tags\s*:\s*\[(.+)\]', re.IGNORECASE)
    tags_block_start = re.compile(r'^tags\s*:', re.IGNORECASE)
    list_item = re.compile(r'^\s*-\s*(.+)$')

    for line in lines:
        inline_match = inline_tags.match(line.strip())
        if inline_match:
            for t in inline_match.group(1).split(","):
                t = t.strip().strip('"').strip("'")
                if t:
                    tags.append(t)
            in_tags_block = False
            continue

        if tags_block_start.match(line.strip()) and "[" not in line:
            in_tags_block = True
            continue

        if in_tags_block:
            list_match = list_item.match(line)
            if list_match:
                t = list_match.group(1).strip().strip('"').strip("'")
                if t:
                    tags.append(t)
            elif line.strip():
                in_tags_block = False

    return tags


def main():
    parser = argparse.ArgumentParser(description="Extract all tags from Obsidian vault.")
    parser.add_argument("--vault", required=True, help="Path to your Obsidian vault")
    parser.add_argument("--output", help="Optional CSV output file path")
    args = parser.parse_args()

    vault_path = Path(args.vault).expanduser().resolve()
    if not vault_path.exists():
        print(f"Error: vault path not found: {vault_path}")
        sys.exit(1)

    tag_counter = Counter()
    files_checked = 0
    files_with_tags = 0

    for md_file in vault_path.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue

        files_checked += 1
        frontmatter = parse_frontmatter(content)
        if not frontmatter:
            continue

        tags = extract_tags(frontmatter)
        if tags:
            files_with_tags += 1
            for tag in tags:
                tag_counter[tag] += 1

    sorted_tags = sorted(tag_counter.items(), key=lambda x: x[0].lower())

    print(f"\nVault: {vault_path}")
    print(f"Files scanned:      {files_checked}")
    print(f"Files with tags:    {files_with_tags}")
    print(f"Unique tags found:  {len(sorted_tags)}\n")
    print(f"{'Tag':<60} {'Count':>5}")
    print("-" * 67)
    for tag, count in sorted_tags:
        print(f"{tag:<60} {count:>5}")

    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["tag", "count"])
            writer.writerows(sorted_tags)
        print(f"\nCSV saved to: {output_path}")


if __name__ == "__main__":
    main()
