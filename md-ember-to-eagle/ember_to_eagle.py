#!/usr/bin/env python3
"""
ember_to_eagle.py — Import LittleSnapper/Ember .embersnap packages into Eagle.app

Usage:
    python3 ember_to_eagle.py <input_dir> [--folder <eagle_folder_id>] [--dry-run]

Requires Eagle.app to be running. After import, run the companion Eagle plugin
(eagle-backdate-plugin/) to restore original capture dates.

Outputs a JSON sidecar file (eagle_import_log.json) mapping Eagle item IDs to
original timestamps, for use by the backdating plugin.
"""

import argparse
import json
import os
import plistlib
import struct
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import urllib.request
import urllib.error

EAGLE_API = "http://localhost:41595/api/v2"
# Mac/CoreData epoch is 2001-01-01; Unix epoch is 1970-01-01
MAC_EPOCH_OFFSET = 978307200  # seconds


# ---------------------------------------------------------------------------
# NSKeyedArchiver decoder
# ---------------------------------------------------------------------------

def _resolve(objects, uid_or_val):
    """Follow a CF$UID reference into the $objects array, returning the value."""
    if isinstance(uid_or_val, plistlib.UID):
        idx = uid_or_val.data
        if idx == 0:
            return None  # $null sentinel
        return objects[idx]
    return uid_or_val


def _decode_nska(objects, ref):
    """Recursively decode an NSKeyedArchiver object graph node."""
    val = _resolve(objects, ref)
    if val is None:
        return None
    if not isinstance(val, dict):
        return val

    classname = None
    cls_ref = val.get("$class")
    if cls_ref is not None:
        cls_obj = _resolve(objects, cls_ref)
        if isinstance(cls_obj, dict):
            classname = cls_obj.get("$classname")

    if classname == "NSDate":
        ns_time = val.get("NS.time", 0.0)
        return ns_time  # seconds since 2001-01-01

    if classname == "NSURL":
        relative = _decode_nska(objects, val.get("NS.relative"))
        base = _decode_nska(objects, val.get("NS.base"))
        if base:
            return base + relative
        return relative

    if classname in ("NSArray", "NSMutableArray"):
        items = val.get("NS.objects", [])
        return [_decode_nska(objects, item) for item in items]

    if classname in ("NSString", "NSMutableString"):
        return _decode_nska(objects, val.get("NS.string"))

    # Generic dict-like object — decode all keys that aren't $class
    result = {}
    for k, v in val.items():
        if k == "$class":
            continue
        result[k] = _decode_nska(objects, v)
    return result


def decode_nska_plist(path: Path) -> dict:
    """Read a binary NSKeyedArchiver plist and return the decoded root object."""
    with open(path, "rb") as f:
        raw = plistlib.load(f)

    objects = raw["$objects"]
    top_uid = raw["$top"]["root"]
    root = _decode_nska(objects, top_uid)
    return root


# ---------------------------------------------------------------------------
# embersnap reading
# ---------------------------------------------------------------------------

def read_embersnap(snap_path: Path) -> dict | None:
    """
    Parse an .embersnap package and return a dict with all usable fields.
    Returns None and prints a warning if the package can't be read.
    """
    if not snap_path.is_dir():
        print(f"  [skip] {snap_path.name}: not a directory")
        return None

    info_path = snap_path / "Info.plist"
    meta_path = snap_path / "Metadata2.plist"

    if not meta_path.exists():
        print(f"  [skip] {snap_path.name}: no Metadata2.plist")
        return None

    try:
        meta = decode_nska_plist(meta_path)
    except Exception as e:
        print(f"  [skip] {snap_path.name}: Metadata2.plist unreadable: {e}")
        return None

    # Capture date — prefer Info.plist snapDate, fall back to file mtime
    snap_date_unix = None
    if info_path.exists():
        try:
            info = decode_nska_plist(info_path)
            ns_time = info.get("snapDate")
            if isinstance(ns_time, (int, float)) and ns_time:
                snap_date_unix = ns_time + MAC_EPOCH_OFFSET
        except Exception:
            pass

    if snap_date_unix is None:
        snap_date_unix = info_path.stat().st_mtime if info_path.exists() else snap_path.stat().st_mtime

    # Image file
    image_filename = meta.get("imageFileName")
    image_path = None
    if image_filename:
        candidate = snap_path / image_filename
        if candidate.exists():
            image_path = candidate
    if image_path is None:
        # Fall back: first PNG in the package
        pngs = list(snap_path.glob("*.png"))
        if pngs:
            image_path = pngs[0]

    # Webarchive
    webarchive_filename = meta.get("webArchiveFileName")
    webarchive_path = None
    if webarchive_filename:
        candidate = snap_path / webarchive_filename
        if candidate.exists():
            webarchive_path = candidate

    # Tags: NSArray of strings (may be empty)
    raw_tags = meta.get("tags") or []
    tags = [t for t in raw_tags if isinstance(t, str)]

    # Comments: may be None, a string, or an NSArray of strings
    raw_comments = meta.get("comments")
    if isinstance(raw_comments, list):
        annotation = "\n".join(c for c in raw_comments if isinstance(c, str))
    elif isinstance(raw_comments, str):
        annotation = raw_comments
    else:
        annotation = ""

    # Append webarchive note to annotation
    if webarchive_path:
        wa_note = f"[webarchive: {webarchive_path.name}]"
        annotation = (annotation + "\n" + wa_note).strip()

    return {
        "snap_path": snap_path,
        "name": meta.get("title") or snap_path.stem,
        "url": meta.get("url"),
        "tags": tags,
        "annotation": annotation,
        "image_path": image_path,
        "webarchive_path": webarchive_path,
        "snap_date_unix": snap_date_unix,
        "snap_date_ms": int(snap_date_unix * 1000),
        "snap_date_iso": datetime.fromtimestamp(snap_date_unix, tz=timezone.utc).isoformat(),
        "rating": meta.get("rating") or 0,
    }


# ---------------------------------------------------------------------------
# Eagle Web API
# ---------------------------------------------------------------------------

def eagle_post(endpoint: str, payload: dict) -> dict:
    url = f"{EAGLE_API}/{endpoint}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.URLError as e:
        raise RuntimeError(f"Eagle API unreachable at {EAGLE_API}: {e}") from e


def eagle_check():
    """Raise if Eagle is not running or the API is unavailable."""
    try:
        req = urllib.request.Request(f"{EAGLE_API}/library/info")
        with urllib.request.urlopen(req, timeout=5):
            pass
    except Exception as e:
        raise RuntimeError(
            f"Eagle API not responding at {EAGLE_API}.\n"
            "Make sure Eagle.app is running before importing."
        ) from e


def import_batch(items: list[dict], folder_id: str | None, dry_run: bool) -> list[dict]:
    """
    Send up to 1000 items to Eagle's batch import endpoint.
    Returns a list of {eagle_id, snap_date_ms, name} dicts for the log.
    """
    payload_items = []
    for item in items:
        if item["image_path"] is None:
            print(f"  [skip] {item['name']}: no image found")
            continue

        entry = {
            "path": str(item["image_path"].resolve()),
            "name": item["name"],
        }
        if item["url"]:
            entry["website"] = item["url"]
        if item["tags"]:
            entry["tags"] = item["tags"]
        if item["annotation"]:
            entry["annotation"] = item["annotation"]
        if folder_id:
            entry["folders"] = [folder_id]

        payload_items.append((item, entry))

    if not payload_items:
        return []

    if dry_run:
        print(f"  [dry-run] would import {len(payload_items)} items")
        for item, _ in payload_items:
            print(f"    · {item['name']} ({item['snap_date_iso']})")
        return []

    print(f"  Importing {len(payload_items)} items…")
    response = eagle_post("item/add", {"items": [e for _, e in payload_items]})

    if response.get("status") != "success":
        raise RuntimeError(f"Eagle API error: {response}")

    ids = response.get("data", {}).get("ids", [])
    log = []
    for i, (item, _) in enumerate(payload_items):
        eagle_id = ids[i] if i < len(ids) else None
        log.append({
            "eagle_id": eagle_id,
            "name": item["name"],
            "snap_date_ms": item["snap_date_ms"],
            "snap_date_iso": item["snap_date_iso"],
            "source_url": item["url"],
            "snap_path": str(item["snap_path"]),
        })
        status = f"id={eagle_id}" if eagle_id else "no id returned"
        print(f"    ✓ {item['name']} ({status})")

    return log


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Import .embersnap packages into Eagle.app")
    parser.add_argument("input_dir", help="Directory containing .embersnap packages")
    parser.add_argument("--folder", default=None, help="Eagle folder ID to import into")
    parser.add_argument("--dry-run", action="store_true", help="Parse snaps but don't call Eagle API")
    parser.add_argument("--log", default="eagle_import_log.json", help="Path for the import log (default: eagle_import_log.json)")
    args = parser.parse_args()

    input_dir = Path(args.input_dir).expanduser().resolve()
    if not input_dir.is_dir():
        print(f"Error: {input_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    if not args.dry_run:
        eagle_check()

    snaps = sorted(input_dir.glob("*.embersnap"))
    if not snaps:
        print(f"No .embersnap files found in {input_dir}")
        sys.exit(0)

    print(f"Found {len(snaps)} .embersnap packages in {input_dir}")

    parsed = []
    for snap_path in snaps:
        print(f"  Reading {snap_path.name}…")
        result = read_embersnap(snap_path)
        if result:
            parsed.append(result)

    print(f"\n{len(parsed)} packages parsed successfully.")

    if not parsed:
        sys.exit(0)

    # Import in batches of 1000 (Eagle API limit)
    all_log = []
    batch_size = 1000
    for i in range(0, len(parsed), batch_size):
        batch = parsed[i : i + batch_size]
        print(f"\nBatch {i // batch_size + 1} ({len(batch)} items):")
        log_entries = import_batch(batch, args.folder, args.dry_run)
        all_log.extend(log_entries)

    if not args.dry_run and all_log:
        log_path = Path(args.log).expanduser().resolve()
        with open(log_path, "w") as f:
            json.dump(all_log, f, indent=2)
        print(f"\nImport log written to {log_path}")
        print(f"Run the Eagle plugin in eagle-backdate-plugin/ to restore original capture dates.")

    success = sum(1 for e in all_log if e.get("eagle_id"))
    print(f"\nDone. {success}/{len(all_log)} items imported successfully.")


if __name__ == "__main__":
    main()
