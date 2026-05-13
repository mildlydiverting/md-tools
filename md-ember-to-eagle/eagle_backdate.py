#!/usr/bin/env python3
"""
eagle_backdate.py — Restore original capture dates on Eagle items imported
from Ember .embersnap packages.

Reads the eagle_import_log.json produced by ember_to_eagle.py and directly
edits each item's metadata.json inside the Eagle library, setting btime to
the original Ember capture timestamp.

Eagle must be CLOSED (or the library switched away from) before running this,
then reopened afterwards so it picks up the changes.

Usage:
    python3 eagle_backdate.py <log_file> <library_path>

Example:
    python3 eagle_backdate.py _assets/eagle_import_log.json \
        _assets/test-library.library
"""

import json
import sys
from pathlib import Path


def backdate(log_path: Path, library_path: Path):
    with open(log_path) as f:
        entries = json.load(f)

    images_dir = library_path / "images"
    if not images_dir.is_dir():
        print(f"Error: {images_dir} not found — is this an Eagle library?", file=sys.stderr)
        sys.exit(1)

    ok = fail = skip = 0

    for entry in entries:
        eagle_id = entry.get("eagle_id")
        snap_date_ms = entry.get("snap_date_ms")
        name = entry.get("name", "?")

        if not eagle_id:
            print(f"  skip  {name} — no Eagle ID")
            skip += 1
            continue

        if not snap_date_ms:
            print(f"  skip  {name} — no timestamp")
            skip += 1
            continue

        meta_path = images_dir / f"{eagle_id}.info" / "metadata.json"
        if not meta_path.exists():
            print(f"  miss  {name} ({eagle_id}) — metadata.json not found")
            fail += 1
            continue

        with open(meta_path) as f:
            meta = json.load(f)

        old_btime = meta.get("btime", "—")
        meta["btime"] = snap_date_ms
        # modificationTime is Eagle's "last edited in Eagle" timestamp;
        # leave it as-is so Eagle doesn't think we've modified the item.

        with open(meta_path, "w") as f:
            json.dump(meta, f, separators=(",", ":"))

        print(f"  ok    {name}  {old_btime} → {snap_date_ms}")
        ok += 1

    print(f"\nDone. {ok} backdated, {fail} not found, {skip} skipped.")
    if ok:
        print("Reopen the Eagle library (or restart Eagle) to see updated dates.")


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    log_path = Path(sys.argv[1]).expanduser().resolve()
    library_path = Path(sys.argv[2]).expanduser().resolve()

    if not log_path.exists():
        print(f"Error: log file not found: {log_path}", file=sys.stderr)
        sys.exit(1)
    if not library_path.exists():
        print(f"Error: library not found: {library_path}", file=sys.stderr)
        sys.exit(1)

    backdate(log_path, library_path)


if __name__ == "__main__":
    main()
