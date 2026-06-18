# Handoff: md-flickr-tools — Eagle import + citation fixes

## Context
- **Repo**: https://github.com/mildlydiverting/md-tools (subfolder: `md-flickr-tools/`)
- **Files worked on this session**: `eagle_import.py` (new), `flickr_fix_citations.py` (new)
- **Current versions**: `eagle_import.py` v1.0, `flickr_fix_citations.py` v1.0

## What we built this session

### `eagle_import.py`
Imports Flickr image+JSON sidecar pairs into Eagle via the Web API v1 (`localhost:41595`). Features:

- Scans a folder (optionally recursive) for image+sidecar pairs, matched by filename stem
- Checks Eagle is running before doing anything
- Gets or creates an Eagle folder from `gallery_title` in the sidecar; favourites land unfoldered
- Splits Flickr tags into human tags (sent to Eagle) and machine tags (appended to annotation)
- Builds a YAML front matter annotation block + plain-text citation + machine tags section
- Writes `eagle_imported: true` back to the sidecar after import (used to skip on rerun)
- Supports `--dry-run` and `--recursive`

### `flickr_fix_citations.py`
Backfills broken `citation_markdown` and `tasl` fields in existing sidecars. Sidecars downloaded before the citation bug was fixed had plain URLs (not hyperlinked) and unlinked licence names. This script rebuilds both fields from the other sidecar fields, which are correct. Supports `--dry-run` and `--recursive`. Skips files with no changes needed.

## Known issues / deferred things

- **Eagle `addFromPaths` returns no item IDs** — the v1 API only returns `{"status": "success"}`. We write `eagle_imported: true` as a boolean flag instead of storing an Eagle item ID. If Eagle ever exposes item IDs on import we can upgrade this.
- **Eagle inspector plugin** — started in an earlier session (`md-ember-to-eagle`), showed blank window likely due to manifest config issue. Still outstanding. Plugin API confirmed: `eagle.item.getSelected()` + `item.save()` supports reading/writing `annotation` and `tags`.
- **TASL citation format** — the four-part TASL (Title/Author/Source/Licence) is now correct in new downloads. Existing sidecars pre-June 2026 may still need `flickr_fix_citations.py` run against them.
- **`tags_normalised` deliberately omitted** — will be handled by a separate standalone tag normalisation tool
- **`medium` and `dimensions` not available from Flickr API** — consider a manual enrichment pass

## Reset the eagle_imported flag

To reimport everything (e.g. after changing annotation format):

```bash
cd ~/Development/md-tools/md-flickr-tools
python3 -c "
import json, pathlib
for p in pathlib.Path('flickr_downloads').rglob('*.json'):
    if p.name.startswith('_'):
        continue
    m = json.load(open(p))
    if m.pop('eagle_imported', None) or m.pop('eagle_id', None):
        json.dump(m, open(p, 'w'), indent=2, ensure_ascii=False)
        print(f'Reset: {p}')
"
```

## Relevant technical constraints and decisions already made

- **Eagle API v1** (`localhost:41595/api/`) — no auth needed for localhost. Use `addFromPaths` (plural) not `addFromPath` (singular). `folderId` is a top-level payload parameter, not per-item. Folder create uses `{"folderName": "..."}`.
- **Image path must be absolute** — pass `image_path.resolve()` not a relative path or Eagle returns ENOENT.
- **Machine tag filter** — regex `\w+:.+` catches all `namespace:value` tags (bookid, taxonomy, dc, bhl, geo, sherlocknet, artist, etc.)
- **Annotation format** — YAML front matter (`---` delimiters) + blank line + plain-text citation + blank line + machine tags block
- **Separate scripts, loosely joined** — each script does one thing; canonical JSON sidecar is the interchange format
- **venv**: `/Users/kimplowright/Development/bins/bin/activate`; requires `requests`, `pyyaml`, `python-dotenv`

## Files to attach next session
- [ ] `eagle_import.py` (current working version)
- [ ] `flickr_fix_citations.py` (current working version)
- [ ] A sample sidecar from `flickr_downloads/` to test against

---
*Template: ~/Development/are.na-toolkit/handoff-template.md*
