# md-ember-to-eagle

Imports LittleSnapper / Ember `.embersnap` packages into [Eagle.app](https://eagle.cool), preserving title, source URL, tags, notes, and original capture date.

## What gets preserved

| Ember field | Eagle field |
|---|---|
| Title | Name |
| Source URL | Website |
| Tags | Tags |
| Comments | Annotation |
| Webarchive filename | Appended to annotation |
| Capture date (Info.plist `snapDate`) | `importedAt` (via plugin) |

**Not preserved:** Ember's annotation layers and crop data (no Eagle equivalent).

The webarchive file itself is not imported into Eagle (Eagle has no native format for it), but its filename is noted in the annotation so you can locate it alongside the original `.embersnap` package.

---

## Requirements

- Python 3.10+ (uses `plistlib`, `urllib` — no third-party packages needed)
- [Eagle.app](https://eagle.cool) 4.0 Build 21+ running during import

---

## Usage

### Step 1 — Import images

Eagle must be running.

```sh
python3 ember_to_eagle.py /path/to/embersnaps/
```

Options:

| Flag | Description |
|---|---|
| `--folder <id>` | Import into a specific Eagle folder (get the ID from Eagle's URL bar or API) |
| `--dry-run` | Parse packages and print what would be imported, without calling Eagle |
| `--log <path>` | Where to write the import log (default: `eagle_import_log.json`) |

The script writes `eagle_import_log.json` mapping each Eagle item ID to its original capture timestamp.

### Step 2 — Restore original dates

Eagle's REST API ignores date fields on import and update. Instead, `eagle_backdate.py` edits the `metadata.json` files directly inside the library.

**Close Eagle first** (or switch to a different library), then run:

```sh
python3 eagle_backdate.py eagle_import_log.json /path/to/your.library
```

Then reopen Eagle / switch back to the library. Items will show their original Ember capture dates.

The `eagle-backdate-plugin/` directory can be ignored — the script approach is simpler and more reliable.

---

## How it works

### Plist decoding

Ember stores metadata in binary NSKeyedArchiver plists (`Info.plist`, `Metadata2.plist`). These use an indirection table (`$objects`) rather than plain key-value pairs. The script includes a minimal NSKeyedArchiver decoder that handles `NSDate`, `NSURL`, `NSArray`, and generic objects without any third-party dependencies.

### Date conversion

Ember's `snapDate` is an `NSDate` (`NS.time`) — seconds since **2001-01-01** (the Mac/CoreData epoch). The script converts to Unix milliseconds by adding 978307200 seconds before multiplying by 1000.

### Batch size

The Eagle API accepts up to 1000 items per batch call. The script splits large directories automatically.

---

## File structure

```
.
├── ember_to_eagle.py     # Step 1: import .embersnap packages into Eagle
├── eagle_backdate.py     # Step 2: restore original capture dates in library
└── eagle_import_log.json # Written by step 1, read by step 2
```
