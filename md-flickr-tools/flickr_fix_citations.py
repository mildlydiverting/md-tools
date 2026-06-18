#!/usr/bin/env python3
"""
flickr_fix_citations.py — v1.0
Regenerate citation_markdown and tasl fields in existing Flickr JSON sidecars.

Existing sidecars may have broken citations if they were downloaded with an older
version of flickr_download.py (plain URL instead of [URL](URL), unlinked licence).
This script rebuilds both fields from the other sidecar fields, which are correct.

Usage:
    python flickr_fix_citations.py <folder_or_file> [--dry-run] [--recursive]

Examples:
    python flickr_fix_citations.py flickr_downloads/_test --dry-run
    python flickr_fix_citations.py flickr_downloads/
    python flickr_fix_citations.py flickr_downloads/ --recursive
"""

import json
import datetime
import argparse
from pathlib import Path


# ---------------------------------------------------------------------------
# Citation builders — kept in sync with flickr_download.py
# ---------------------------------------------------------------------------

def format_access_date(iso_string):
    """'2026-04-21T12:00:00Z' → '21 Apr 2026'"""
    dt = datetime.datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
    return dt.strftime("%-d %b %Y")


def extract_year(date_string):
    """
    Extract 4-digit year from various date formats:
      '1972-12-07', '2011-04-19 16:17:03', '1826-01-01 00:00:00'
    Returns string year, or 'n.d.' if unparseable.
    """
    if not date_string:
        return 'n.d.'
    s = str(date_string).strip()
    if len(s) >= 4 and s[:4].isdigit():
        return s[:4]
    return 'n.d.'


def build_citation(creator, year, title, medium, institution, institution_location,
                   accessed_url, access_date_str, license_name, license_url):
    """
    Harvard-adjacent citation in Markdown.
    Author (yyyy). _Title_. [Medium]. Institution, Location.
    Available at [URL](URL) (Accessed dd mmm yyyy). Licensed under [Licence](url).
    """
    parts = [f"{creator} ({year}). _{title}_. [{medium}]."]
    if institution:
        loc = f"{institution}, {institution_location}" if institution_location else institution
        parts.append(f" {loc}.")
    parts.append(f" Available at [{accessed_url}]({accessed_url}) (Accessed {access_date_str}).")
    if license_url:
        parts.append(f" Licensed under [{license_name}]({license_url}).")
    else:
        parts.append(f" {license_name}.")
    return "".join(parts)


def build_tasl(title, accessed_url, creator, creator_url, license_name, license_url):
    """
    TASL attribution line in Markdown.
    [Title](page url) — [Author](profile url) — [Licence](url)
    """
    title_part   = f"[{title}]({accessed_url})"
    creator_part = f"[{creator}]({creator_url})" if creator_url else creator
    license_part = f"[{license_name}]({license_url})" if license_url else license_name
    return f"{title_part} — {creator_part} — {license_part}"


# ---------------------------------------------------------------------------
# Sidecar processing
# ---------------------------------------------------------------------------

def fix_sidecar(path, dry_run=False):
    """
    Regenerate citation_markdown and tasl for one sidecar file.
    Returns (changed: bool, error: str|None).
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return False, str(e)

    # Extract fields needed for rebuilding
    creator          = meta.get('creator', '')
    creator_url      = meta.get('creator_profile_url', '')
    title            = meta.get('title', '')
    medium           = meta.get('medium') or 'Photograph'
    institution      = meta.get('institution')
    institution_loc  = meta.get('institution_location')
    accessed_url     = meta.get('accessed_url', '')
    date_accessed    = meta.get('date_accessed', '')
    license_name     = meta.get('license_name', '')
    license_url      = meta.get('license_url')
    date_created     = meta.get('date_created')

    if not accessed_url or not creator:
        return False, "missing accessed_url or creator — skipping"

    year             = extract_year(date_created)
    access_date_str  = format_access_date(date_accessed) if date_accessed else 'unknown'

    new_citation = build_citation(
        creator=creator,
        year=year,
        title=title,
        medium=medium,
        institution=institution,
        institution_location=institution_loc,
        accessed_url=accessed_url,
        access_date_str=access_date_str,
        license_name=license_name,
        license_url=license_url,
    )

    new_tasl = build_tasl(
        title=title,
        accessed_url=accessed_url,
        creator=creator,
        creator_url=creator_url,
        license_name=license_name,
        license_url=license_url,
    )

    old_citation = meta.get('citation_markdown')
    old_tasl     = meta.get('tasl')

    citation_changed = old_citation != new_citation
    tasl_changed     = old_tasl != new_tasl

    if not citation_changed and not tasl_changed:
        return False, None  # already correct

    if dry_run:
        if citation_changed:
            print(f"    citation_markdown:")
            print(f"      OLD: {old_citation}")
            print(f"      NEW: {new_citation}")
        if tasl_changed:
            print(f"    tasl:")
            print(f"      OLD: {old_tasl}")
            print(f"      NEW: {new_tasl}")
        return True, None

    meta['citation_markdown'] = new_citation
    meta['tasl']              = new_tasl

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    return True, None


def find_sidecars(root, recursive=False):
    """Yield all .json sidecar paths (excludes _gallery_manifest.json)."""
    root = Path(root)
    if root.is_file() and root.suffix == '.json':
        yield root
        return
    pattern = '**/*.json' if recursive else '*.json'
    for p in sorted(root.glob(pattern)):
        if not p.name.startswith('_'):
            yield p


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Regenerate citation_markdown and tasl in Flickr JSON sidecars."
    )
    parser.add_argument('target', help="Folder of sidecars, or a single .json file")
    parser.add_argument('--dry-run', action='store_true',
                        help="Show what would change without writing anything")
    parser.add_argument('--recursive', action='store_true',
                        help="Recurse into subfolders")
    args = parser.parse_args()

    sidecars = list(find_sidecars(args.target, recursive=args.recursive))
    if not sidecars:
        print("No JSON sidecars found.")
        return

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Processing {len(sidecars)} sidecar(s) in {args.target}\n")

    updated = 0
    unchanged = 0
    errors = 0

    for path in sidecars:
        print(f"  {path.name}")
        changed, err = fix_sidecar(path, dry_run=args.dry_run)
        if err:
            print(f"    SKIP: {err}")
            errors += 1
        elif changed:
            if not args.dry_run:
                print(f"    Updated.")
            updated += 1
        else:
            print(f"    OK (no changes needed)")
            unchanged += 1

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Done.")
    print(f"  Updated:   {updated}")
    print(f"  Unchanged: {unchanged}")
    print(f"  Skipped:   {errors}")


if __name__ == '__main__':
    main()
