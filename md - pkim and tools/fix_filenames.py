#!/usr/bin/env python3
"""
fix_filenames.py
----------------
Fixes filenames for Dropbox compatibility. Handles two structures:

  1. Eagle .info folders  (mode: eagle)
     Each item lives in  <id>.info/  containing the image and metadata.json.
     The image is named  <metadata.name>.<metadata.ext>.
     We sanitise the name to ASCII-safe, rename the image, update metadata.json.

  2. Flickr download folders  (mode: flickr)
     Old style:  <photo_id>_<title>.jpg  +  <photo_id>_<title>.json
     New style:  <photo_id>.jpg          +  <photo_id>.json
     Renames pairs to bare photo_id (read from the sidecar JSON).
     Also updates _manifest.json if present.

Usage:
    # Fix an Eagle library images folder:
    python fix_filenames.py eagle  /path/to/Eagle.library/images

    # Rename Flickr downloads to photo_id-only filenames:
    python fix_filenames.py flickr /path/to/flickr_downloads

    # Dry run (no changes made):
    python fix_filenames.py eagle  /path/... --dry-run
    python fix_filenames.py flickr /path/... --dry-run

Requirements: Python 3.9+, no third-party packages needed.
"""

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path


# ─── SANITISER ───────────────────────────────────────────────────────────────

# Characters that are illegal in Dropbox / Windows filenames
_ILLEGAL = re.compile(r'[\\/:*?"<>|]')
# Collapse runs of whitespace / underscores
_MULTI_SPACE = re.compile(r'[ \t]+')
_MULTI_UNDER = re.compile(r'_+')


def safe_filename(s: str, max_len: int = 80) -> str:
    """
    Return a filename stem that is safe for Dropbox, Windows, and macOS.

    Strategy:
      1. NFKD-normalise then drop combining diacritical marks (converts é→e, etc.)
      2. Encode to ASCII, replacing any non-ASCII char with '_'
      3. Strip Windows/Dropbox-illegal characters: \\ / : * ? " < > |
      4. Collapse whitespace to single spaces, collapse runs of underscores
      5. Strip leading/trailing spaces, dots, underscores
      6. Truncate to max_len characters
    """
    # Step 1: NFKD normalise, drop combining diacritical marks (category Mn)
    normalised = unicodedata.normalize('NFKD', s)
    ascii_only = ''.join(c for c in normalised if unicodedata.category(c) != 'Mn')

    # Step 2: encode to ASCII; unknown chars become '?' then '_'
    s2 = ascii_only.encode('ascii', errors='replace').decode('ascii').replace('?', '_')

    # Step 3: strip illegal chars
    s2 = _ILLEGAL.sub('_', s2)

    # Keep only printable, non-control chars
    s2 = ''.join(c if c.isprintable() and ord(c) >= 32 else '_' for c in s2)

    # Step 4: normalise whitespace and underscores
    s2 = _MULTI_SPACE.sub(' ', s2)
    s2 = _MULTI_UNDER.sub('_', s2)

    # Step 5: strip leading/trailing junk
    s2 = s2.strip(' ._')

    # Step 6: truncate
    s2 = s2[:max_len].rstrip(' ._')

    # Fallback if we ended up with nothing
    return s2 or '_unnamed'


def needs_fixing(name: str) -> bool:
    """True if the name differs from its sanitised form."""
    return safe_filename(name) != name


# ─── EAGLE MODE ───────────────────────────────────────────────────────────────

def fix_eagle_folder(root: Path, dry_run: bool) -> None:
    """
    Walk <root> looking for *.info subdirectories.
    Inside each, fix the image filename and update metadata.json.
    """
    info_dirs = sorted(root.rglob('*.info'))
    if not info_dirs:
        print(f"No .info folders found under {root}")
        return

    changed = 0
    skipped = 0

    for info_dir in info_dirs:
        if not info_dir.is_dir():
            continue

        metadata_path = info_dir / 'metadata.json'
        if not metadata_path.exists():
            print(f"  [warn] No metadata.json in {info_dir.name}")
            continue

        with open(metadata_path, encoding='utf-8') as f:
            try:
                meta = json.load(f)
            except json.JSONDecodeError as e:
                print(f"  [error] Bad JSON in {metadata_path}: {e}")
                continue

        name = meta.get('name', '')
        ext  = meta.get('ext', '')

        if not name:
            skipped += 1
            continue

        new_name = safe_filename(name)

        if new_name == name:
            skipped += 1
            continue

        # Find the image file (name.ext or just any non-metadata file)
        old_img = info_dir / f"{name}.{ext}" if ext else None
        new_img = info_dir / f"{new_name}.{ext}" if ext else None

        print(f"\n  [{info_dir.name}]")
        print(f"    name:  {name!r}")
        print(f"    →      {new_name!r}")

        if dry_run:
            print("    [DRY RUN] no changes made")
            changed += 1
            continue

        # Rename image file if it exists
        if old_img and old_img.exists():
            if new_img and not new_img.exists():
                old_img.rename(new_img)
                print(f"    renamed: {old_img.name} → {new_img.name}")
            elif new_img and new_img.exists():
                print(f"    [warn] target already exists: {new_img.name} — skipping rename")
        else:
            # Try to find the file by extension
            candidates = [f for f in info_dir.iterdir() if f.suffix.lstrip('.').lower() == ext.lower()
                          and f.name != 'metadata.json']
            if len(candidates) == 1:
                old_img = candidates[0]
                new_img = info_dir / f"{new_name}.{ext}"
                if not new_img.exists():
                    old_img.rename(new_img)
                    print(f"    renamed: {old_img.name} → {new_img.name}")
            else:
                print(f"    [warn] Could not find image file for {name}.{ext}")

        # Update metadata.json
        meta['name'] = new_name
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        print(f"    updated metadata.json")

        changed += 1

    print(f"\nDone. {changed} item(s) {'would be ' if dry_run else ''}fixed, {skipped} skipped.")


# ─── FLICKR MODE ─────────────────────────────────────────────────────────────

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.tif', '.tiff', '.bmp'}


def fix_flickr_folder(root: Path, dry_run: bool) -> None:
    """
    Rename Flickr sidecar pairs from  <photo_id>_<title>.{jpg,json}
    to bare  <photo_id>.{jpg,json}.

    The photo_id is read from inside the sidecar JSON ("photo_id" field),
    so it works even if the stem is mangled.  Also updates _manifest.json.
    """
    manifest_path = root / '_manifest.json'
    manifest = {}
    if manifest_path.exists():
        with open(manifest_path, encoding='utf-8') as f:
            try:
                manifest = json.load(f)
            except json.JSONDecodeError as e:
                print(f"[warn] Could not parse _manifest.json: {e}")

    # Find all JSON sidecars (not the manifest itself)
    json_files = sorted(p for p in root.rglob('*.json')
                        if p.name != '_manifest.json' and p.is_file())

    changed = 0
    skipped = 0

    for json_path in json_files:
        # Load sidecar to get the authoritative photo_id
        try:
            with open(json_path, encoding='utf-8') as f:
                meta = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  [error] Could not read {json_path.name}: {e}")
            continue

        photo_id = meta.get('photo_id')
        if not photo_id:
            print(f"  [warn] No photo_id in {json_path.name} — skipping")
            skipped += 1
            continue

        # Already correctly named?
        if json_path.stem == photo_id:
            skipped += 1
            continue

        # Find matching image file
        img_path = None
        for ext in IMAGE_EXTENSIONS:
            candidate = json_path.with_suffix(ext)
            if candidate.exists():
                img_path = candidate
                break

        new_json = json_path.with_name(f"{photo_id}.json")
        new_img  = img_path.with_name(f"{photo_id}{img_path.suffix}") if img_path else None

        print(f"\n  {json_path.stem!r}")
        print(f"  → {photo_id!r}")

        if dry_run:
            print("  [DRY RUN] no changes made")
            changed += 1
            continue

        # Rename image
        if img_path and new_img:
            if not new_img.exists():
                img_path.rename(new_img)
                print(f"  renamed image: {img_path.name} → {new_img.name}")
            else:
                print(f"  [warn] image target exists: {new_img.name}")

        # Rename JSON sidecar
        if not new_json.exists():
            json_path.rename(new_json)
            print(f"  renamed json:  {json_path.name} → {new_json.name}")
        else:
            print(f"  [warn] json target exists: {new_json.name}")

        # Patch manifest entry
        old_img_name = img_path.name if img_path else f"{json_path.stem}.jpg"
        new_img_name = new_img.name if new_img else f"{photo_id}.jpg"
        if photo_id in manifest:
            manifest[photo_id]['filename'] = new_img_name
            print(f"  patched manifest entry for {photo_id}")

        changed += 1

    # Save updated manifest
    if manifest and changed > 0 and not dry_run:
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        print(f"\nSaved updated _manifest.json")

    print(f"\nDone. {changed} file pair(s) {'would be ' if dry_run else ''}renamed, {skipped} skipped.")


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Fix special-character filenames for Dropbox compatibility.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('mode', choices=['eagle', 'flickr'],
                        help='"eagle" for Eagle .info folders, "flickr" for Flickr download folders')
    parser.add_argument('folder', type=Path,
                        help='Root folder to process')
    parser.add_argument('--dry-run', action='store_true',
                        help='Report what would change without making any changes')

    args = parser.parse_args()

    if not args.folder.exists():
        print(f"Error: folder does not exist: {args.folder}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print("[DRY RUN MODE — no files will be changed]\n")

    if args.mode == 'eagle':
        fix_eagle_folder(args.folder, dry_run=args.dry_run)
    else:
        fix_flickr_folder(args.folder, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
