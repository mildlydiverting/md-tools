# Handoff: md-ember-to-eagle — Import LittleSnapper/Ember .embersnap packages into Eagle.app

## Context
- **Repo**: /Users/kimplowright/Development/md-tools/md-ember-to-eagle/
- **File(s) being worked on**: `ember_to_eagle.py`, `eagle_backdate.py`
- **Current version**: working, tested on 28 sample snaps

## What we built last session
A two-script Python pipeline that reads a directory of `.embersnap` packages, decodes their binary NSKeyedArchiver plists without any third-party dependencies, and imports them into Eagle via its REST API (`localhost:41595`). A second script (`eagle_backdate.py`) directly edits the `metadata.json` files inside the Eagle library to restore original Ember capture dates (the REST API silently ignores date fields). Both scripts are tested and working against `_assets/test-embersnaps/` and `_assets/test-library.library/`.

## Known issues / deferred things
- **Classification data unverified on real library**: the 28 test snaps all had empty `tags` and `collections` arrays. We don't yet know if the main Ember library (Google Drive) has snaps with tags or folder/collection assignments. This needs checking before a full run — if collections are populated, we'd want to map them to Eagle folders.
- **Google Drive access**: the MCP can't see the shared folder at `https://drive.google.com/drive/folders/1OSh2cWllcn5c2qgGvBIYQHyA955VaFm3`. Either add it as a shortcut to My Drive, or download a small local sample for inspection.
- **Eagle plugin (eagle-backdate-plugin/)**: built but abandoned — showed a blank window on load. Superseded by `eagle_backdate.py`. Can be deleted.
- **Webarchives not imported**: `.webarchive` files are noted in Eagle annotations but not imported (Eagle has no native format for them). Decision pending on whether to do anything more with them.
- **`eagle_check()` uses `library/info` endpoint**: confirmed working on Eagle 4.0 Build 21. If Eagle version changes this may need updating.

## What I want to do next session
1. **Verify classification data** in the real Ember library — check a sample of snaps for non-empty `tags` and `collections` before running the full import. Either add the Drive folder shortcut to My Drive, or drop a local sample in `_assets/`.
2. **If collections are present**: map Ember collections → Eagle folders (create folders by collection name, then assign items).
3. **Full run** against the real library once the above is confirmed.

## Relevant technical constraints or decisions already made
- Pure Python 3.10+, no third-party packages — uses only `plistlib`, `urllib`, `json`, `pathlib`
- NSKeyedArchiver decoder is hand-rolled in `ember_to_eagle.py` — handles `NSDate`, `NSURL`, `NSArray`; `plistlib.UID.data` (not `.integer`) is the correct attribute
- Mac/CoreData epoch offset: `NS.time + 978307200` → Unix seconds
- Eagle REST API endpoint for batch import: `POST /api/v2/item/add` with `items` array (not `addFromPaths`)
- Eagle `btime` field in `metadata.json` is what Eagle displays as the item date — editing this directly works; Eagle must be closed first and the library reopened after
- Do NOT search outside the working directory without explicit user approval

## Files to attach
- [ ] `ember_to_eagle.py`
- [ ] `eagle_backdate.py`
- [ ] `_assets/eagle_import_log.json` (from the test run)

---
*Template: ~/Development/md-tools/handoff-template.md*
