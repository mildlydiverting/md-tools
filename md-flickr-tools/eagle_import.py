#!/usr/bin/env python3
"""
eagle_import.py — v1.0
Import Flickr image+JSON sidecar pairs into Eagle via Web API v2.

Usage:
    python eagle_import.py <folder_path> [--dry-run]

- Scans folder for image files with matching .json sidecars
- Creates/finds Eagle folder by gallery title (from sidecar)
- Imports image with name, url, tags, and YAML annotation block
- Writes eagle_imported: true back into the JSON sidecar after import
- Skips items already imported (eagle_imported present in sidecar)
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
        "path": str(image_path.resolve()),
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
    if not r.ok:
        print(f"  ERROR {r.status_code}: {r.text[:300]}")
        r.raise_for_status()
    # addFromPaths returns {status: success} only — no item IDs
    return "imported"


# ---------------------------------------------------------------------------
import re as _re

MACHINE_TAG_RE = _re.compile(r'^[A-Za-z][A-Za-z0-9_]*:.+')

def split_tags(tags):
    """
    Split a flat tag list into (human_tags, machine_tags).
    Machine tags match namespace:value pattern (e.g. taxonomy:binomial=..., dc:identifier=...).
    """
    human, machine = [], []
    for tag in (tags or []):
        if MACHINE_TAG_RE.match(tag):
            machine.append(tag)
        else:
            human.append(tag)
    return human, machine


# Sidecar helpers
# ---------------------------------------------------------------------------

def build_annotation(meta):
    """
    Build the annotation block for Eagle.
    Format: YAML front matter wrapped in --- dividers, followed by the plain-text citation.
    Field names match the output of flickr_download.py / flickr_gallery_download.py.
    """
    fields = {}

    for dest, src in [
        ("creator",       "creator"),
        ("creator_url",   "creator_profile_url"),
        ("date_created",  "date_created"),
        ("medium",        "medium"),
        ("license",       "license_name"),
        ("license_url",   "license_url"),
        ("source_url",    "accessed_url"),
        ("copyright_line","copyright_line"),
        ("tasl",          "tasl"),
        ("citation",      "citation_markdown"),
    ]:
        val = meta.get(src)
        if val:
            fields[dest] = str(val)

    if not fields:
        return ""

    yaml_block = yaml.dump(fields, allow_unicode=True, default_flow_style=False, sort_keys=False).strip()
    front_matter = f"---\n{yaml_block}\n---"

    citation = fields.get("citation", "")
    machine_tags = meta.get("_machine_tags", [])

    parts = [front_matter]
    if citation:
        parts.append(citation)
    if machine_tags:
        parts.append("tags:\n" + "\n".join(f"  {t}" for t in machine_tags))

    return "\n\n".join(parts)


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

def find_pairs(folder, recursive=False):
    """
    Yield (image_path, json_path) tuples for all image+sidecar pairs in folder.
    Matches by stem: photo.jpg + photo.jpg.json (or photo.json).
    """
    folder = Path(folder)
    pattern = "**/*" if recursive else "*"
    for image_path in sorted(folder.glob(pattern)):
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


def import_folder(folder_path, dry_run=False, recursive=False):
    folder = Path(folder_path)
    if not folder.is_dir():
        print(f"ERROR: Not a directory: {folder_path}")
        sys.exit(1)

    if not eagle_ping():
        print("ERROR: Eagle is not running or MCP plugin is not enabled (port 41595).")
        print("Please open Eagle and ensure the MCP plugin is active, then retry.")
        sys.exit(1)

    suffix = " (recursive)" if recursive else ""
    print(f"\nScanning: {folder}{suffix}\n")

    pairs = list(find_pairs(folder, recursive=recursive))
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
        if meta.get("eagle_imported") or meta.get("eagle_id"):
            print(f"  SKIP: already imported")
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
        name = meta.get("photo_id") or image_path.stem
        website = meta.get("accessed_url") or ""
        all_tags = meta.get("tags") or []
        tags, machine_tags = split_tags(all_tags)
        meta["_machine_tags"] = machine_tags  # temp field for build_annotation
        annotation = build_annotation(meta)
        meta.pop("_machine_tags", None)  # remove temp field

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
                meta["eagle_imported"] = True
                save_sidecar(sidecar_path, meta)
                print(f"  Imported.")
                imported += 1
            else:
                print(f"  WARNING: Import call succeeded but no confirmation returned.")
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
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recurse into subfolders",
    )
    args = parser.parse_args()

    import_folder(args.folder, dry_run=args.dry_run, recursive=args.recursive)
