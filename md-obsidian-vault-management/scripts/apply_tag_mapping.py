#!/usr/bin/env python3
"""
apply_tag_mapping.py
Applies a tag mapping CSV to all Obsidian vault notes.

Each old tag is replaced by one or more new tags (pipe-separated in the CSV).
Tags not in the mapping are left untouched.
Duplicate tags in the resulting set are removed.

Usage:
    python apply_tag_mapping.py --vault "/path/to/vault" --mapping tag_mapping.csv --dry-run
    python apply_tag_mapping.py --vault "/path/to/vault" --mapping tag_mapping.csv

Options:
    --vault     Path to your Obsidian vault
    --mapping   Path to the tag_mapping.csv file
    --dry-run   Preview changes without writing anything
    --report    Path to write a CSV report of all changes (optional)
"""

# CHANGELOG
# v1.0.0 - Initial version
#   - Reads tag_mapping.csv (old_tag, new_tags pipe-separated)
#   - Walks all .md files in vault
#   - Replaces tags in both list-style and inline frontmatter formats
#   - Deduplicates resulting tag set
#   - Tags not in mapping are preserved unchanged
#   - Dry-run mode
#   - Optional CSV change report

import argparse
import csv
import re
import sys
from pathlib import Path


def load_mapping(mapping_path: Path) -> dict:
    """
    Load tag_mapping.csv.
    Returns dict: {old_tag: [new_tag, ...]}
    """
    mapping = {}
    with open(mapping_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            old = row["old_tag"].strip()
            new_tags = [t.strip() for t in row["new_tags"].split("|") if t.strip()]
            mapping[old] = new_tags
    return mapping


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


def clean_tag(tag: str) -> str:
    """Strip quotes and whitespace from a tag."""
    return tag.strip().strip('"').strip("'").strip()


def apply_mapping_to_tags(tags: list, mapping: dict) -> tuple:
    """
    Given a list of existing tags, apply the mapping.
    Returns (new_tag_list, changes_list)
    changes_list entries: (old_tag, new_tags_list)
    """
    result = []
    changes = []
    seen = set()

    for tag in tags:
        tag_clean = clean_tag(tag)
        if not tag_clean:
            continue

        if tag_clean in mapping:
            new_tags = mapping[tag_clean]
            if new_tags != [tag_clean]:
                changes.append((tag_clean, new_tags))
            for t in new_tags:
                if t not in seen:
                    result.append(t)
                    seen.add(t)
        else:
            # Not in mapping — keep as-is
            if tag_clean not in seen:
                result.append(tag_clean)
                seen.add(tag_clean)

    return result, changes


def process_frontmatter(frontmatter: str, mapping: dict):
    """
    Find and remap tags in frontmatter YAML.
    Handles list-style and inline tag formats.
    Returns (new_frontmatter, changes_list)
    """
    lines = frontmatter.split("\n")
    new_lines = []
    in_tags_block = False
    all_changes = []

    tag_list_item = re.compile(r'^(\s*-\s*)(.+)$')
    inline_tags = re.compile(r'^(tags:\s*\[)(.+)(\]\s*)$', re.IGNORECASE)
    tags_block_start = re.compile(r'^tags\s*:', re.IGNORECASE)

    # Collect list-style tags together so we can deduplicate across the whole block
    # We do a two-pass approach: first collect all list tags, then rebuild

    # Find if tags are list-style or inline
    tags_style = None  # 'list' or 'inline'
    tags_start_idx = None
    tags_end_idx = None
    inline_line_idx = None

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if inline_tags.match(stripped):
            tags_style = 'inline'
            inline_line_idx = idx
            break
        if tags_block_start.match(stripped) and "[" not in line:
            tags_style = 'list'
            tags_start_idx = idx
            # Find where list ends
            for end_idx in range(idx + 1, len(lines)):
                if lines[end_idx].strip() and not lines[end_idx].strip().startswith("-"):
                    tags_end_idx = end_idx
                    break
            else:
                tags_end_idx = len(lines)
            break

    if tags_style == 'inline':
        # Process inline tags: tags: [tag1, tag2]
        for idx, line in enumerate(lines):
            if idx == inline_line_idx:
                stripped = line.strip()
                m = inline_tags.match(stripped)
                if m:
                    raw_tags = [t.strip() for t in m.group(2).split(",")]
                    new_tags, changes = apply_mapping_to_tags(raw_tags, mapping)
                    all_changes.extend(changes)
                    indent = line[:len(line) - len(line.lstrip())]
                    new_lines.append(f"{indent}tags: [{', '.join(new_tags)}]")
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

    elif tags_style == 'list':
        for idx, line in enumerate(lines):
            if idx == tags_start_idx:
                # Collect all list items
                raw_tags = []
                for list_idx in range(tags_start_idx + 1, tags_end_idx):
                    m = tag_list_item.match(lines[list_idx])
                    if m:
                        raw_tags.append(clean_tag(m.group(2)))

                new_tags, changes = apply_mapping_to_tags(raw_tags, mapping)
                all_changes.extend(changes)

                # Rebuild: keep the "tags:" line, then write new list items
                new_lines.append(line)  # the "tags:" line itself
                for t in new_tags:
                    new_lines.append(f"  - {t}")

            elif tags_start_idx < idx < tags_end_idx:
                # Skip original list items — already handled above
                continue
            else:
                new_lines.append(line)
    else:
        # No tags found
        new_lines = lines

    return "\n".join(new_lines), all_changes


def process_vault(vault_path: Path, mapping: dict, dry_run: bool, report_path=None):
    md_files = list(vault_path.rglob("*.md"))
    total_files = len(md_files)
    files_with_changes = 0
    total_tag_changes = 0
    all_report_rows = []

    print(f"\n{'DRY RUN — no files will be modified' if dry_run else 'LIVE RUN — files will be modified'}")
    print(f"Vault:   {vault_path}")
    print(f"Mapping: {len(mapping)} rules loaded")
    print(f"Files:   {total_files}\n")
    print("-" * 70)

    for md_file in sorted(md_files):
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception as e:
            print(f"  SKIP (read error): {md_file.relative_to(vault_path)} — {e}")
            continue

        frontmatter, body = parse_frontmatter(content)
        if frontmatter is None:
            continue

        new_frontmatter, changes = process_frontmatter(frontmatter, mapping)

        if not changes:
            continue

        files_with_changes += 1
        total_tag_changes += len(changes)
        rel_path = str(md_file.relative_to(vault_path))

        print(f"  {rel_path}")
        for old_tag, new_tags in changes:
            new_tags_str = ", ".join(new_tags)
            print(f"    {old_tag!r:40s} → [{new_tags_str}]")
            all_report_rows.append({
                "file": rel_path,
                "old_tag": old_tag,
                "new_tags": "|".join(new_tags),
            })

        if not dry_run:
            new_content = f"---\n{new_frontmatter}\n---{body}"
            try:
                md_file.write_text(new_content, encoding="utf-8")
            except Exception as e:
                print(f"    ERROR writing: {e}")

    print("-" * 70)
    print(f"\nSummary:")
    print(f"  Files scanned:        {total_files}")
    print(f"  Files with changes:   {files_with_changes}")
    print(f"  Tag remappings:       {total_tag_changes}")

    if dry_run:
        print(f"\n  Run without --dry-run to apply these changes.")
    else:
        print(f"\n  Done. All changes applied.")

    if report_path and all_report_rows:
        rp = Path(report_path)
        with open(rp, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["file", "old_tag", "new_tags"])
            writer.writeheader()
            writer.writerows(all_report_rows)
        print(f"\n  Report saved to: {rp}")


def main():
    parser = argparse.ArgumentParser(
        description="Apply tag mapping CSV to Obsidian vault frontmatter."
    )
    parser.add_argument("--vault", required=True, help="Path to your Obsidian vault")
    parser.add_argument("--mapping", required=True, help="Path to tag_mapping.csv")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--report", help="Optional path to write a CSV change report")
    args = parser.parse_args()

    vault_path = Path(args.vault).expanduser().resolve()
    mapping_path = Path(args.mapping).expanduser().resolve()

    if not vault_path.exists():
        print(f"Error: vault path not found: {vault_path}")
        sys.exit(1)
    if not mapping_path.exists():
        print(f"Error: mapping file not found: {mapping_path}")
        sys.exit(1)

    mapping = load_mapping(mapping_path)
    process_vault(vault_path, mapping, dry_run=args.dry_run, report_path=args.report)


if __name__ == "__main__":
    main()
