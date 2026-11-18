# extract_book_metadata

Scans a folder of PDF and EPUB files, extracts metadata, flags duplicates,
and writes everything to an Excel spreadsheet. Makes no changes to source files.

## Setup

```zsh
# Create and activate a virtualenv
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install pymupdf ebooklib openpyxl rapidfuzz
```

## Usage

```zsh
# Basic — scan everything under /Volumes/MyServer/Books
python extract_book_metadata.py /Volumes/MyServer/Books output.xlsx

# Test run on first 200 files before committing to the full collection
python extract_book_metadata.py /Volumes/MyServer/Books output.xlsx --limit 200
```

## Output

The Excel file has two sheets:

**Book Metadata** — one row per file, columns:
| Column | Notes |
|---|---|
| File path | Full path including subdirectories |
| Filename | Filename only |
| Type | .pdf or .epub |
| Title | From embedded metadata, or guessed from first page |
| Title source | `metadata`, `first-page (guessed)`, or blank |
| Author(s) | Semicolon-separated if multiple |
| Editor(s) | Separate from authors where EPUB marks role |
| Year | Publication year where available |
| Edition | Populated if in metadata (rare) |
| Publisher | From metadata |
| ISBN | Extracted from identifier fields or text |
| Possible duplicate of | Filename(s) of likely duplicates |
| Error | Any extraction errors |

Row colours:
- **Yellow** — possible duplicate flagged
- **Salmon** — file could not be read (corrupt, DRM-protected, etc.)
- Alternating white/light blue — normal rows

**Summary** — counts of titles found, duplicates, errors, etc.

## Duplicate detection

Three checks are run:
1. **Same ISBN** — exact match
2. **Same filename in different folders** — exact match
3. **Same title + author** — fuzzy match at 92/100 strictness

Fuzzy matching only runs on files where a title was found. Hash filenames
and DOI filenames with no recoverable title will not be fuzzy-matched.

## Known limitations

- **DRM-protected EPUBs** will error — this is expected. The filename will
  still appear in the output, just with no metadata and an error note.
- **Scanned PDFs** (image-only, no text layer) will have no first-page text
  to guess from. ExifTool metadata may still be present.
- **Edition** is rarely embedded in PDF/EPUB metadata — expect this column
  to be mostly empty. You can fill it in manually in the spreadsheet.
- The first-page title guess works well for academic papers (title at top)
  and poorly for books that start with copyright pages or tables of contents.
- Fuzzy matching is O(n²) — on a 9,500-file collection it may take a few
  minutes. The `--limit` flag is useful for testing.

## Dependencies

| Library | Purpose |
|---|---|
| `pymupdf` | PDF reading and text extraction |
| `ebooklib` | EPUB parsing |
| `openpyxl` | Excel output |
| `rapidfuzz` | Fast fuzzy string matching |
