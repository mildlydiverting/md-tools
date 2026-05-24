#!/usr/bin/env python3
"""
fix_obsidian_tags.py
Converts tags with spaces in Obsidian frontmatter to kebab-case.

Usage:
    python fix_obsidian_tags.py --vault "/path/to/vault" --dry-run
    python fix_obsidian_tags.py --vault "/path/to/vault"

Options:
    --vault     Path to your Obsidian vault
    --dry-run   Preview changes without writing anything
"""

# CHANGELOG
# v1.0.0 - Initial version
#   - Walks all .md files in vault
#   - Parses YAML frontmatter
#   - Converts spaced tags to kebab-case
#   - Handles both list-style and inline tag formats
#   - Dry-run mode with full report
#   - Summary stats on completion

import argparse
import re
import sys
from pathlib import Path


def to_kebab(tag: str) -> str:
    """Convert a tag with spaces to kebab-case. Leaves already-valid tags alone."""
    return tag.strip().lower().replace(" ", "-")


def needs_fixing(tag: str) -> bool:
    """Return True if tag contains spaces."""
    return " " in tag.strip()


def parse_frontmatter(content: str):
    """
    Extract frontmatter from note content.
    Returns (frontmatter_str, body_str) or (None, content) if no frontmatter.
    """
    if not content.startswith("---"):
        return None, content
    end = content.find("\n---", 3)
    if end == -1:
        return None, content
    frontmatter = content[3:end].strip()
    body = content[end + 4:]
    return frontmatter, body


def fix_tags_in_frontmatter(frontmatter: str):
    """
    Find and fix tags in frontmatter YAML.
    Handles:
      tags:
        - Some Tag With Spaces
        - already-fine
      and:
      tags: [Some Tag, another tag]
    Returns (fixed_frontmatter, list_of_changes)
    """
    changes = []
    lines = frontmatter.split("\n")
    new_lines = []
    in_tags_block = False

    # Match list-style tags block
    tag_list_item = re.compile(r'^(\s*-\s*)(.+)$')
    # Match inline tags: tags: [tag one, tag two]
    inline_tags = re.compile(r'^(tags:\s*\[)(.+)(\])$', re.IGNORECASE)
    # Match start of tags block: tags:
    tags_block_start = re.compile(r'^tags\s*:', re.IGNORECASE)

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check for inline tags: tags: [...]
        inline_match = inline_tags.match(line.strip())
        if inline_match:
            prefix = line[:len(line) - len(line.lstrip())]  # preserve indent
            raw_tags = inline_match.group(2).split(",")
            fixed_tags = []
            for t in raw_tags:
                t = t.strip()
                if needs_fixing(t):
                    fixed = to_kebab(t)
                    changes.append((t, fixed))
                    fixed_tags.append(fixed)
                else:
                    fixed_tags.append(t)
            new_line = f"{prefix}tags: [{', '.join(fixed_tags)}]"
            new_lines.append(new_line)
            in_tags_block = False
            i += 1
            continue

        # Check for start of tags block
        if tags_block_start.match(line.strip()) and "[" not in line:
            in_tags_block = True
            new_lines.append(line)
            i += 1
            continue

        # If we're in a tags block, look for list items
        if in_tags_block:
            list_match = tag_list_item.match(line)
            if list_match:
                indent_and_dash = list_match.group(1)
                tag = list_match.group(2).strip()
                # Strip surrounding quotes if present
                tag_clean = tag.strip('"').strip("'")
                if needs_fixing(tag_clean):
                    fixed = to_kebab(tag_clean)
                    changes.append((tag_clean, fixed))
                    new_lines.append(f"{indent_and_dash}{fixed}")
                else:
                    new_lines.append(line)
                i += 1
                continue
            else:
                # No longer in tags block if line doesn't start with -
                # (unless it's blank)
                if line.strip() != "":
                    in_tags_block = False

        new_lines.append(line)
        i += 1

    return "\n".join(new_lines), changes


def process_vault(vault_path: Path, dry_run: bool):
    md_files = list(vault_path.rglob("*.md"))
    total_files = len(md_files)
    files_with_changes = 0
    total_tag_changes = 0
    all_changes = []

    print(f"\n{'DRY RUN — no files will be modified' if dry_run else 'LIVE RUN — files will be modified'}")
    print(f"Vault: {vault_path}")
    print(f"Files found: {total_files}\n")
    print("-" * 60)

    for md_file in sorted(md_files):
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception as e:
            print(f"  SKIP (read error): {md_file.relative_to(vault_path)} — {e}")
            continue

        frontmatter, body = parse_frontmatter(content)
        if frontmatter is None:
            continue

        fixed_frontmatter, changes = fix_tags_in_frontmatter(frontmatter)

        if not changes:
            continue

        files_with_changes += 1
        total_tag_changes += len(changes)
        rel_path = md_file.relative_to(vault_path)

        print(f"  {rel_path}")
        for old, new in changes:
            print(f"    '{old}'  →  '{new}'")
            all_changes.append((str(rel_path), old, new))

        if not dry_run:
            new_content = f"---\n{fixed_frontmatter}\n---{body}"
            try:
                md_file.write_text(new_content, encoding="utf-8")
            except Exception as e:
                print(f"    ERROR writing file: {e}")

    print("-" * 60)
    print(f"\nSummary:")
    print(f"  Files scanned:       {total_files}")
    print(f"  Files with changes:  {files_with_changes}")
    print(f"  Tags fixed:          {total_tag_changes}")
    if dry_run:
        print(f"\n  Run without --dry-run to apply these changes.")
    else:
        print(f"\n  Done. All changes applied.")


def main():
    parser = argparse.ArgumentParser(description="Fix spaced tags in Obsidian vault frontmatter.")
    parser.add_argument("--vault", required=True, help="Path to your Obsidian vault")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    vault_path = Path(args.vault).expanduser().resolve()
    if not vault_path.exists():
        print(f"Error: vault path not found: {vault_path}")
        sys.exit(1)

    process_vault(vault_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
