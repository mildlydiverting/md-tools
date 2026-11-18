#!/usr/bin/env python3
"""
extract_book_metadata.py
------------------------
Scans a directory (including mounted file servers) for PDF and EPUB files,
extracts metadata, flags possible duplicates, and writes results to an Excel file.

Reads only — makes no changes to any source files.

Usage:
    python extract_book_metadata.py /path/to/books output.xlsx
    python extract_book_metadata.py /path/to/books output.xlsx --limit 500

Dependencies (install in virtualenv):
    pip install pymupdf ebooklib openpyxl rapidfuzz

Version: 1.0
"""

import argparse
import hashlib
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pymupdf as fitz
import ebooklib
from ebooklib import epub
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, PatternFill
from openpyxl.utils import get_column_letter
from rapidfuzz import fuzz

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = {".pdf", ".epub"}

# Fuzzy match threshold for title+author deduplication (0-100).
# 92 is strict — catches minor punctuation/spacing differences but not
# genuinely different titles.
FUZZY_THRESHOLD = 92

# How many characters to extract from first page for title guessing
FIRST_PAGE_CHARS = 500


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------

def clean(value):
    """Strip whitespace and return None if empty."""
    if value is None:
        return None
    value = str(value).strip()
    return value if value else None


def extract_isbn(text):
    """Pull first ISBN-10 or ISBN-13 from a string."""
    if not text:
        return None
    match = re.search(r"(?:ISBN[:\s-]*)?(97[89][\d\s-]{10,17}|\d{9}[\dXx])", text)
    if match:
        return re.sub(r"[\s-]", "", match.group(1)).upper()
    return None


def first_page_text(pdf_doc, max_chars=FIRST_PAGE_CHARS):
    """Extract text from first page of a PDF."""
    try:
        page = pdf_doc.load_page(0)
        text = page.get_text("text")
        return text[:max_chars].strip() if text else None
    except Exception:
        return None


def guess_title_from_text(text):
    """
    Heuristic: take the first non-trivial line from first-page text
    as a candidate title. Works well for academic papers; less so for books.
    """
    if not text:
        return None
    lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 10]
    return lines[0] if lines else None


def extract_pdf_metadata(path):
    """Extract metadata from a PDF file. Returns a dict."""
    record = {
        "filepath": str(path),
        "filename": path.name,
        "extension": ".pdf",
        "title": None,
        "author": None,
        "editor": None,
        "year": None,
        "edition": None,
        "publisher": None,
        "isbn": None,
        "title_source": None,
        "error": None,
    }
    try:
        doc = fitz.open(str(path))
        meta = doc.metadata or {}

        record["title"] = clean(meta.get("title"))
        record["author"] = clean(meta.get("author"))
        record["publisher"] = clean(meta.get("producer") or meta.get("creator"))

        # Year: try creationDate field first (format: D:YYYYMMDDHHmmSS)
        raw_date = clean(meta.get("creationDate") or meta.get("modDate"))
        if raw_date:
            year_match = re.search(r"(\d{4})", raw_date)
            if year_match:
                year = int(year_match.group(1))
                # Sanity check: ignore implausible years
                if 1800 <= year <= datetime.now().year + 1:
                    record["year"] = year

        # Subject field sometimes contains ISBN
        subject = clean(meta.get("subject"))
        record["isbn"] = extract_isbn(subject) or extract_isbn(record["title"])

        record["title_source"] = "metadata" if record["title"] else None

        # Fall back to first-page text if no title in metadata
        if not record["title"]:
            text = first_page_text(doc)
            guessed = guess_title_from_text(text)
            if guessed:
                record["title"] = guessed
                record["title_source"] = "first-page (guessed)"

        doc.close()
    except Exception as e:
        record["error"] = str(e)

    return record


def extract_epub_metadata(path):
    """Extract metadata from an EPUB file. Returns a dict."""
    record = {
        "filepath": str(path),
        "filename": path.name,
        "extension": ".epub",
        "title": None,
        "author": None,
        "editor": None,
        "year": None,
        "edition": None,
        "publisher": None,
        "isbn": None,
        "title_source": None,
        "error": None,
    }
    try:
        book = epub.read_epub(str(path), options={"ignore_ncx": True})

        def get_meta(name):
            items = book.get_metadata("DC", name)
            if not items:
                return None
            values = []
            for content, attrs in items:
                if content:
                    values.append(clean(str(content)))
            return "; ".join(v for v in values if v) or None

        record["title"] = get_meta("title")
        record["publisher"] = get_meta("publisher")

        # Authors and editors: DC:creator with role attribute
        creators = book.get_metadata("DC", "creator")
        authors, editors = [], []
        for content, attrs in creators:
            role = (attrs or {}).get("opf:role", "aut")
            name = clean(str(content))
            if not name:
                continue
            if role == "edt":
                editors.append(name)
            else:
                authors.append(name)
        record["author"] = "; ".join(authors) if authors else None
        record["editor"] = "; ".join(editors) if editors else None

        # Date
        date_val = get_meta("date")
        if date_val:
            year_match = re.search(r"(\d{4})", date_val)
            if year_match:
                year = int(year_match.group(1))
                if 1800 <= year <= datetime.now().year + 1:
                    record["year"] = year

        # ISBN from identifier
        identifiers = book.get_metadata("DC", "identifier")
        for content, attrs in identifiers:
            isbn = extract_isbn(str(content))
            if isbn:
                record["isbn"] = isbn
                break

        record["title_source"] = "metadata" if record["title"] else None

    except Exception as e:
        record["error"] = str(e)

    return record


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------

def normalise_for_matching(text):
    """Lowercase, strip punctuation and common noise words."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    # Strip common subtitle noise
    text = re.sub(r"\b(the|a|an|and|of|in|on|for|to|by)\b", " ", text)
    return text.strip()


def make_title_author_key(record):
    """Combined normalised title+author string for fuzzy matching."""
    title = normalise_for_matching(record.get("title") or "")
    author = normalise_for_matching(record.get("author") or record.get("editor") or "")
    return f"{title} {author}".strip()


def detect_duplicates(records):
    """
    Flag duplicates by:
      1. Same ISBN (exact)
      2. Same filename in different paths (exact)
      3. Same title+author (fuzzy, threshold FUZZY_THRESHOLD)

    Returns a dict: filepath -> list of duplicate filepaths
    """
    dup_map = defaultdict(list)  # filepath -> [duplicate filepaths]

    # --- ISBN duplicates ---
    isbn_index = defaultdict(list)
    for r in records:
        if r.get("isbn"):
            isbn_index[r["isbn"]].append(r["filepath"])
    for isbn, paths in isbn_index.items():
        if len(paths) > 1:
            for p in paths:
                others = [x for x in paths if x != p]
                dup_map[p].extend(others)

    # --- Same filename, different path ---
    name_index = defaultdict(list)
    for r in records:
        name_index[r["filename"]].append(r["filepath"])
    for name, paths in name_index.items():
        if len(paths) > 1:
            for p in paths:
                others = [x for x in paths if x != p]
                dup_map[p].extend(others)

    # --- Fuzzy title+author ---
    # Build list of (key, filepath) — only for records with a title
    keyed = [
        (make_title_author_key(r), r["filepath"])
        for r in records
        if r.get("title")
    ]

    for i, (key_i, path_i) in enumerate(keyed):
        for j, (key_j, path_j) in enumerate(keyed):
            if j <= i:
                continue
            if not key_i or not key_j:
                continue
            score = fuzz.token_sort_ratio(key_i, key_j)
            if score >= FUZZY_THRESHOLD:
                if path_j not in dup_map[path_i]:
                    dup_map[path_i].append(path_j)
                if path_i not in dup_map[path_j]:
                    dup_map[path_j].append(path_i)

    # Deduplicate the lists
    return {k: list(dict.fromkeys(v)) for k, v in dup_map.items()}


# ---------------------------------------------------------------------------
# File scanning
# ---------------------------------------------------------------------------

def scan_directory(root, limit=None):
    """Walk root directory and yield paths for supported file types."""
    root = Path(root)
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip hidden directories
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for filename in sorted(filenames):
            if Path(filename).suffix.lower() in SUPPORTED_EXTENSIONS:
                yield Path(dirpath) / filename
                count += 1
                if limit and count >= limit:
                    return


# ---------------------------------------------------------------------------
# Excel output
# ---------------------------------------------------------------------------

COLUMNS = [
    ("filepath",       "File path",            60),
    ("filename",       "Filename",             40),
    ("extension",      "Type",                  6),
    ("title",          "Title",                40),
    ("title_source",   "Title source",         20),
    ("author",         "Author(s)",            30),
    ("editor",         "Editor(s)",            25),
    ("year",           "Year",                  6),
    ("edition",        "Edition",               8),
    ("publisher",      "Publisher",            25),
    ("isbn",           "ISBN",                 18),
    ("duplicate_of",   "Possible duplicate of", 50),
    ("error",          "Error",                30),
]

HEADER_FILL   = PatternFill("solid", fgColor="1F4E79")  # dark navy
ALT_FILL      = PatternFill("solid", fgColor="EBF3FB")  # light blue
DUP_FILL      = PatternFill("solid", fgColor="FFF2CC")  # yellow
ERROR_FILL    = PatternFill("solid", fgColor="FCE4D6")  # salmon

# SANITISE FOR XLSX


def sanitise_for_xlsx(value):
    """Strip illegal XML/xlsx control characters from strings."""
    if not isinstance(value, str):
        return value
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', value)


def write_xlsx(records, dup_map, output_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Book Metadata"

    # Header row
    header_font = Font(name="Arial", bold=True, color="FFFFFF", size=10)
    for col_idx, (key, label, width) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=label)
        cell.font = header_font
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(wrap_text=False, vertical="center")
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    ws.row_dimensions[1].height = 20
    ws.freeze_panes = "A2"

    data_font = Font(name="Arial", size=10)

    for row_idx, record in enumerate(records, start=2):
        dup_list = dup_map.get(record["filepath"], [])
        record["duplicate_of"] = "; ".join(
            Path(p).name for p in dup_list
        ) if dup_list else None

        is_dup   = bool(dup_list)
        has_err  = bool(record.get("error"))
        alt_row  = (row_idx % 2 == 0)

        for col_idx, (key, label, width) in enumerate(COLUMNS, start=1):
            value = record.get(key)
            cell = ws.cell(row=row_idx, column=col_idx, value=sanitise_for_xlsx(value))
            cell.font = data_font
            cell.alignment = Alignment(wrap_text=False, vertical="top")

            if has_err:
                cell.fill = ERROR_FILL
            elif is_dup:
                cell.fill = DUP_FILL
            elif alt_row:
                cell.fill = ALT_FILL

    # Summary sheet
    ws2 = wb.create_sheet("Summary")
    total      = len(records)
    with_title = sum(1 for r in records if r.get("title"))
    with_isbn  = sum(1 for r in records if r.get("isbn"))
    dups       = sum(1 for r in records if dup_map.get(r["filepath"]))
    errors     = sum(1 for r in records if r.get("error"))
    no_title   = total - with_title

    summary_data = [
        ("Total files scanned", total),
        ("Files with title (metadata)", with_title),
        ("Files with title (guessed from text)", sum(
            1 for r in records if r.get("title_source") == "first-page (guessed)"
        )),
        ("Files with no title", no_title),
        ("Files with ISBN", with_isbn),
        ("Possible duplicates flagged", dups),
        ("Files with errors", errors),
        ("Run date", datetime.now().strftime("%Y-%m-%d %H:%M")),
    ]

    ws2["A1"] = "Metric"
    ws2["B1"] = "Value"
    ws2["A1"].font = Font(name="Arial", bold=True)
    ws2["B1"].font = Font(name="Arial", bold=True)

    for i, (label, value) in enumerate(summary_data, start=2):
        ws2.cell(row=i, column=1, value=label).font = Font(name="Arial", size=10)
        ws2.cell(row=i, column=2, value=value).font = Font(name="Arial", size=10)

    ws2.column_dimensions["A"].width = 40
    ws2.column_dimensions["B"].width = 20

    wb.save(output_path)
    print(f"Saved: {output_path}")
    print(f"  {total} files | {with_title} with titles | {dups} possible duplicates | {errors} errors")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Extract metadata from PDF/EPUB files and write to Excel."
    )
    parser.add_argument("source_dir", help="Root directory to scan (can be a mounted volume)")
    parser.add_argument("output_xlsx", help="Path for the output .xlsx file")
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Stop after scanning this many files (useful for testing)"
    )
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    if not source_dir.exists():
        print(f"Error: '{source_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning: {source_dir}")
    if args.limit:
        print(f"Limit: {args.limit} files")

    records = []
    for i, path in enumerate(scan_directory(source_dir, limit=args.limit)):
        ext = path.suffix.lower()
        if i % 100 == 0 and i > 0:
            print(f"  {i} files processed...")
        if ext == ".pdf":
            records.append(extract_pdf_metadata(path))
        elif ext == ".epub":
            records.append(extract_epub_metadata(path))

    print(f"Extracted metadata from {len(records)} files. Detecting duplicates...")
    dup_map = detect_duplicates(records)

    write_xlsx(records, dup_map, args.output_xlsx)


if __name__ == "__main__":
    main()
