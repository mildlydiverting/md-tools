#!/usr/bin/env python3
"""
eagle_import.py — v1.0
Import Flickr image+JSON sidecar pairs into Eagle via Web API v2.

Usage:
    python eagle_import.py <folder_path> [--dry-run]

- Scans folder for image files with matching .json sidecars
- Creates/finds Eagle folder by gallery title (from sidecar)
- Imports image with name, url, tags, and YAML annotation block
- Writes Eagle item ID back into the JSON sidecar (eagle_id field)
- Skips items already imported (eagle_id present in sidecar)
- Falls back gracefully if Eagle is not running

Requires:
    pip install requests --break-system-packages

Eagle must be running with the MCP plugin enabled (port 41595).
"""

import json
import os
import sys
import argparse
import requests
import yaml
from pathlib import Path

EAGLE_API = "http://localhost:41595/api"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".tif", ".tiff", ".bmp", ".svg"}


# ---------------------------------------------------------------------------
# Eagle API helpers
# ---------------------------------------------------------------------------

def eagle_ping():
    """Return True if Eagle is reachable."""
    try:
        r = requests.get(f"{EAGLE_API}/application/info", timeout=3)
        return r.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


def eagle_get_folders():
    """Return list of all Eagle folders."""
    r = requests.get(f"{EAGLE_API}/folder/list", timeout=10)
    r.raise_for_status()
    return r.json().get("data", [])


def _find_folder_by_name(folders, name):
    """Recursively search folder tree for a folder by name. Returns folder dict or None."""
    for folder in folders:
        if folder.get("name") == name:
            return folder
        children = folder.get("children", [])
        if children:
            found = _find_folder_by_name(children, name)
            if found:
                return found
    return None


def eagle_get_or_create_folder(name, dry_run=False):
    """
    Return Eagle folder ID for the given name, creating it if necessary.
    Returns None on dry_run or if name is falsy.
    """
    if not name:
        return None

    folders = eagle_get_folders()
    existing = _find_folder_by_name(folders, name)
    if existing:
        print(f"  Folder found: '{name}' (id: {existing['id']})")
        return existing["id"]

    if dry_run:
        print(f"  [DRY RUN] Would create folder: '{name}'")
        return None

    payload = {"folderName": name}
    r = requests.post(f"{EAGLE_API}/folder/create", json=payload, timeout=10)
    r.raise_for_status()
    data = r.json().get("data", {})
    new_id = data.get("id") if isinstance(data, dict) else (data[0]["id"] if data else None)
    if new_id:
        print(f"  Folder created: '{name}' (id: {new_id})")
        return new_id

    print(f"  WARNING: Folder creation for '{name}' returned unexpected response.")
    return None


def eagle_add_item(image_path, name, website, tags, annotation, folder_id, dry_run=False):
    """
    Add a single item to Eagle. Returns Eagle item ID string, or None on dry_run.
    Uses filePath (local file) rather than URL import.
    """
    if dry_run:
        print(f"  [DRY RUN] Would import: {image_path.name}")
        print(f"    name: {name}")
        print(f"    website: {website}")
        print(f"    tags: {tags}")
        print(f"    folder_id: {folder_id}")
        print(f"    annotation snippet: {(annotation or '')[:80]}...")
        return None

    item = {
        "path": str(image_path),
        "name": name,
        "website": website or "",
        "tags": tags or [],
        "annotation": annotation or "",
    }
    # folderId is a top-level param on addFromPaths, not per-item
    payload = {"items": [item]}
    if folder_id:
        payload["folderId"] = folder_id

    r = requests.post(f"{EAGLE_API}/item/addFromPaths", json=payload, timeout=30)
    r.raise_for_status()
    data = r.json().get("data", [])
    if data:
        return data[0].get("id")
    return None


# ---------------------------------------------------------------------------
# Sidecar helpers
# ---------------------------------------------------------------------------

def build_annotation(meta):
    """
    Build the YAML annotation block from the canonical Flickr sidecar fields.
    Field names match the output of flickr_download.py / flickr_gallery_download.py.
    """
    lines = {}

    creator = meta.get("creator")
    if creator:
        lines["creator"] = creator

    creator_url = meta.get("creator_profile_url")
    if creator_url:
        lines["creator_url"] = creator_url

    date = meta.get("date_created")
    if date:
        lines["date_created"] = str(date)

    medium = meta.get("medium")
    if medium:
        lines["medium"] = medium

    license_name = meta.get("license_name")
    if license_name:
        lines["license"] = license_name

    license_url = meta.get("license_url")
    if license_url:
        lines["license_url"] = license_url

    source_url = meta.get("accessed_url")
    if source_url:
        lines["source_url"] = source_url

    copyright_line = meta.get("copyright_line")
    if copyright_line:
        lines["copyright_line"] = copyright_line

    tasl = meta.get("tasl")
    if tasl:
        lines["tasl"] = tasl

    citation = meta.get("citation_markdown")
    if citation:
        lines["citation"] = citation

    if not lines:
        return ""

    return yaml.dump(lines, allow_unicode=True, default_flow_style=False, sort_keys=False).strip()


def load_sidecar(json_path):
    """Load and return sidecar JSON. Returns None on failure."""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  WARNING: Could not read sidecar {json_path.name}: {e}")
        return None


def save_sidecar(json_path, meta):
    """Write updated sidecar back to disk."""
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Core import logic
# ---------------------------------------------------------------------------

def find_pairs(folder):
    """
    Yield (image_path, json_path) tuples for all image+sidecar pairs in folder.
    Matches by stem: photo.jpg + photo.jpg.json (or photo.json).
    """
    folder = Path(folder)
    for image_path in sorted(folder.iterdir()):
        if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        # Try both naming conventions: photo.jpg.json and photo.json
        sidecar_full = image_path.parent / (image_path.name + ".json")
        sidecar_stem = image_path.parent / (image_path.stem + ".json")
        sidecar = sidecar_full if sidecar_full.exists() else sidecar_stem if sidecar_stem.exists() else None
        if sidecar:
            yield image_path, sidecar
        else:
            print(f"  SKIP (no sidecar): {image_path.name}")


def import_folder(folder_path, dry_run=False):
    folder = Path(folder_path)
    if not folder.is_dir():
        print(f"ERROR: Not a directory: {folder_path}")
        sys.exit(1)

    if not eagle_ping():
        print("ERROR: Eagle is not running or MCP plugin is not enabled (port 41595).")
        print("Please open Eagle and ensure the MCP plugin is active, then retry.")
        sys.exit(1)

    print(f"\nScanning: {folder}\n")

    pairs = list(find_pairs(folder))
    if not pairs:
        print("No image+sidecar pairs found.")
        return

    print(f"Found {len(pairs)} image+sidecar pair(s).\n")

    # Cache folder IDs so we only create each folder once per run
    folder_id_cache = {}
    imported = 0
    skipped = 0
    failed = 0

    for image_path, sidecar_path in pairs:
        print(f"Processing: {image_path.name}")
        meta = load_sidecar(sidecar_path)
        if meta is None:
            failed += 1
            continue

        # Skip if already imported
        if meta.get("eagle_id"):
            print(f"  SKIP: already imported (eagle_id: {meta['eagle_id']})")
            skipped += 1
            continue

        # Resolve folder — gallery_title present in gallery downloads, absent for favourites
        gallery_title = meta.get("gallery_title") or (meta.get("gallery") or {}).get("title")
        folder_id = None
        if gallery_title:
            if gallery_title not in folder_id_cache:
                folder_id_cache[gallery_title] = eagle_get_or_create_folder(gallery_title, dry_run=dry_run)
            folder_id = folder_id_cache[gallery_title]

        # Build fields
        name = meta.get("title") or image_path.stem
        website = meta.get("accessed_url") or ""
        tags = meta.get("tags") or []
        annotation = build_annotation(meta)

        # Import
        eagle_id = eagle_add_item(
            image_path=image_path,
            name=name,
            website=website,
            tags=tags,
            annotation=annotation,
            folder_id=folder_id,
            dry_run=dry_run,
        )

        if not dry_run:
            if eagle_id:
                meta["eagle_id"] = eagle_id
                save_sidecar(sidecar_path, meta)
                print(f"  Imported. eagle_id: {eagle_id}")
                imported += 1
            else:
                print(f"  WARNING: Import call succeeded but no ID returned.")
                failed += 1
        else:
            imported += 1  # count dry-run "would import" as success for summary

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Done.")
    print(f"  Imported: {imported}")
    print(f"  Skipped (already imported): {skipped}")
    print(f"  Failed: {failed}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import Flickr image+JSON sidecar pairs into Eagle."
    )
    parser.add_argument("folder", help="Path to folder containing images and JSON sidecars")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be imported without making any changes",
    )
    args = parser.parse_args()

    import_folder(args.folder, dry_run=args.dry_run)
