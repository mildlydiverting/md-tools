#!/usr/bin/env python3
"""
dezoomify_save.py — v1.1
Alfred workflow script: download a tiled image from the current browser tab
using dezoomify-rs, prompt for a filename, and save image + metadata.

Reads from Alfred workflow environment variables
(set these in the workflow's User Configuration or via variable steps):

  url             - source page URL              [set by get_browser_info.js]
  page_title      - browser tab title            [set by get_browser_info.js]
  selected_text   - text selected before invoke  [set by get_browser_info.js]
  save_folder     - destination folder           [user config, see README]
  dezoomify_bin   - path to dezoomify-rs binary  [user config, optional]
  image_format    - output format: jpg or png    [user config, default: jpg]
  max_megapixels  - cap output size, e.g. "200"  [user config, optional]
                    translates to --max-width / --max-height in dezoomify-rs
                    leave blank for no limit (downloads full resolution)

Changelog:
  v1.1 - Extended metadata: dezoomify-rs version, image dimensions + file
         size (via macOS sips), parsed title components, eagle_item_id
         placeholder. Added max_megapixels → dezoomify-rs size limiting.
  v1.0 - Initial release.
"""

import os
import sys
import json
import subprocess
import re
import shutil
import math
import datetime
from pathlib import Path


# ── Configuration ──────────────────────────────────────────────────────────────

def find_dezoomify():
    """Locate dezoomify-rs: bundled binary → Homebrew (Apple Silicon) →
    Homebrew (Intel) → PATH."""
    candidates = [
        Path(__file__).parent / 'bin' / 'dezoomify-rs',   # bundled in workflow
        Path('/opt/homebrew/bin/dezoomify-rs'),             # Homebrew, Apple Silicon
        Path('/usr/local/bin/dezoomify-rs'),                # Homebrew, Intel
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return shutil.which('dezoomify-rs')                     # last resort: PATH


URL            = os.environ.get('url',            '').strip()
PAGE_TITLE     = os.environ.get('page_title',     '').strip()
SELECTED_TEXT  = os.environ.get('selected_text',  '').strip()
IMAGE_FORMAT   = os.environ.get('image_format',   'jpg').strip().lower().lstrip('.')
MAX_MEGAPIXELS = os.environ.get('max_megapixels', '').strip()

_raw_folder    = os.environ.get('save_folder',  '~/Pictures/dezoomify')
SAVE_FOLDER    = Path(_raw_folder).expanduser()

_bin_override  = os.environ.get('dezoomify_bin', '').strip()
DEZOOMIFY_BIN  = _bin_override if _bin_override else find_dezoomify()


# ── Helpers ────────────────────────────────────────────────────────────────────

def sanitise_filename(name: str) -> str:
    """Strip characters that are illegal in filenames and tidy whitespace."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:80] or 'dezoomify_image'


def ask_filename(suggested: str) -> str | None:
    """Show a macOS dialog so the user can confirm or edit the filename.
    Returns the confirmed string, or None if the user cancelled."""
    safe = suggested.replace('\\', '\\\\').replace('"', '\\"')
    script = (
        f'display dialog "Save image as:" '
        f'default answer "{safe}" '
        f'with title "Dezoomify Grab" '
        f'buttons {{"Cancel", "Save"}} '
        f'default button "Save"'
    )
    result = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        return None  # user hit Cancel (or Escape)
    match = re.search(r'text returned:(.+)', result.stdout.strip())
    return match.group(1).strip() if match else suggested


def unique_path(folder: Path, stem: str, suffix: str) -> Path:
    """Return a non-colliding Path, appending _1, _2 … if needed."""
    candidate = folder / f'{stem}.{suffix}'
    counter = 1
    while candidate.exists():
        candidate = folder / f'{stem}_{counter}.{suffix}'
        counter += 1
    return candidate


def get_dezoomify_version(bin_path: str) -> str:
    """Return the dezoomify-rs version string, e.g. 'dezoomify-rs 2.5.0'."""
    try:
        r = subprocess.run([bin_path, '--version'], capture_output=True, text=True, timeout=5)
        return (r.stdout or r.stderr).strip().splitlines()[0]
    except Exception:
        return 'unknown'


def get_image_dimensions(path: Path) -> tuple[int | None, int | None]:
    """Read pixel dimensions from a saved image using macOS sips.
    No Pillow dependency — sips ships with every macOS install."""
    try:
        r = subprocess.run(
            ['sips', '-g', 'pixelWidth', '-g', 'pixelHeight', str(path)],
            capture_output=True, text=True, timeout=10
        )
        width = height = None
        for line in r.stdout.splitlines():
            line = line.strip()
            if line.startswith('pixelWidth:'):
                width = int(line.split(':', 1)[1].strip())
            elif line.startswith('pixelHeight:'):
                height = int(line.split(':', 1)[1].strip())
        return width, height
    except Exception:
        return None, None


def parse_title_components(title: str) -> list[str]:
    """Naively split a page title into components using common museum/gallery
    separators. Returns a list the user can rename into artist, work, etc.

    Common formats seen in the wild:
      "Girl with a Pearl Earring — Vermeer | Mauritshuis"
      "Vermeer: Girl with a Pearl Earring - Google Arts & Culture"
      "Mona Lisa | Leonardo da Vinci | The Louvre"
    """
    for sep in [' — ', ' | ', ' – ', ' : ', ' - ']:
        parts = [p.strip() for p in title.split(sep) if p.strip()]
        if len(parts) > 1:
            return parts
    return [title]


def build_dezoomify_cmd(url: str, output_path: Path, max_megapixels_str: str) -> list[str]:
    """-l selects the largest available zoom level automatically, avoiding the
    interactive prompt. max_megapixels adds --max-width/--max-height caps."""
    cmd = [DEZOOMIFY_BIN, '-l']   # -l = select largest; no interactive prompt

    if max_megapixels_str:
        try:
            max_mp = float(max_megapixels_str)
            if max_mp > 0:
                max_side = int(math.sqrt(max_mp * 1_000_000))
                cmd += ['--max-width', str(max_side), '--max-height', str(max_side)]
        except ValueError:
            pass

    cmd += [url, str(output_path)]
    return cmd


def parse_artwork_filename(page_title: str, selected_text: str, url: str) -> str:
    """Derive a sensible filename suggestion from available metadata.

    Priority:
    1. Structured fields in selected text ("Title: X", "Creator: X") → "Artist — Title"
    2. First line of selected text if short (< 100 chars)
    3. First component of page title (before first separator)
    4. Fallback: domain + datetime → "artsandculture_2026-05-02_1430"
    """
    from urllib.parse import urlparse

    # ── 1. Structured fields in selected text ─────────────────────────────
    if selected_text:
        lines = [l.strip() for l in selected_text.replace('\r', '\n').splitlines()]
        fields = {}
        for line in lines:
            for key in ('Title', 'Creator', 'Artist', 'Author'):
                if line.lower().startswith(key.lower() + ':'):
                    val = line.split(':', 1)[1].strip()
                    if val:
                        fields[key.lower()] = val
                        break

        title  = fields.get('title')
        artist = fields.get('creator') or fields.get('artist') or fields.get('author')

        if title and artist:
            return f'{artist} — {title}'
        if title:
            return title

    # ── 2. First line of selected text if short ───────────────────────────
    if selected_text:
        first_line = selected_text.replace('\r', '\n').splitlines()[0].strip()
        if first_line and len(first_line) < 100:
            return first_line

    # ── 3. First component of page title ─────────────────────────────────
    if page_title:
        for sep in [' | ', ' — ', ' – ', ' - ', ' : ']:
            parts = page_title.split(sep)
            if len(parts) > 1:
                return parts[0].strip()
        return page_title.strip()

    # ── 4. Domain + datetime fallback ─────────────────────────────────────
    try:
        domain = urlparse(url).netloc.replace('www.', '').split('.')[0]
    except Exception:
        domain = 'dezoomify'
    dt = datetime.datetime.now().strftime('%Y-%m-%d_%H%M')
    return f'{domain}_{dt}' 


def write_metadata(image_path: Path, dezoomify_version: str) -> Path:
    """Write a JSON sidecar file alongside the image."""
    width, height = get_image_dimensions(image_path)
    file_size_bytes = image_path.stat().st_size

    meta = {
        # ── Provenance ────────────────────────────────────────────────────
        'source_url':    URL,
        'page_title':    PAGE_TITLE,
        'title_parts':   parse_title_components(PAGE_TITLE),
        # title_parts is a naive split on common separators — edit to taste.
        # e.g. ["Girl with a Pearl Earring", "Vermeer", "Mauritshuis"]
        # could become: artist, work_title, institution fields.

        # ── Notes ─────────────────────────────────────────────────────────
        'notes':         SELECTED_TEXT,
        # Any text selected in the browser before the hotkey was pressed.
        # Often a caption, artist statement, or accession number.

        # ── Timestamps ────────────────────────────────────────────────────
        'saved_at':      datetime.datetime.now().isoformat(),

        # ── Image file ────────────────────────────────────────────────────
        'image_file':    image_path.name,
        'image': {
            'width_px':        width,
            'height_px':       height,
            'megapixels':      round((width * height) / 1_000_000, 2) if width and height else None,
            'file_size_bytes': file_size_bytes,
            'file_size_mb':    round(file_size_bytes / (1024 * 1024), 2),
        },

        # ── Capture provenance ────────────────────────────────────────────
        'capture': {
            'dezoomify_rs_version': dezoomify_version,
            'image_format':         IMAGE_FORMAT,
            'max_megapixels_limit': float(MAX_MEGAPIXELS) if MAX_MEGAPIXELS else None,
        },

        # ── Eagle integration (future) ────────────────────────────────────
        'eagle_item_id': None,
        # Populated if/when Eagle import is added. Eagle's local API returns
        # an item ID on import; store it here to link back to the library.
    }

    meta_path = image_path.with_suffix('.json')
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    return meta_path


def alert(message: str):
    """Show a simple macOS alert (used for errors that need user attention)."""
    subprocess.run(
        ['osascript', '-e', f'display alert "Dezoomify Grab" message "{message}"'],
        capture_output=True
    )


# ── Main ───────────────────────────────────────────────────────────────────────

def main():

    # ── Validate ───────────────────────────────────────────────────────────
    if not URL:
        alert('No URL found. Make sure the browser info step ran successfully.')
        sys.exit(1)

    if not DEZOOMIFY_BIN:
        alert(
            'dezoomify-rs not found.\n\n'
            'Install via Homebrew:  brew install dezoomify-rs\n'
            'Or set dezoomify_bin in the workflow User Configuration.'
        )
        sys.exit(1)

    # Capture version early so it goes in the metadata even if something
    # else fails later — useful for debugging.
    dezoomify_version = get_dezoomify_version(DEZOOMIFY_BIN)

    # ── Suggest a filename ─────────────────────────────────────────────────
    suggested = sanitise_filename(parse_artwork_filename(PAGE_TITLE, SELECTED_TEXT, URL))

    # ── Ask user to confirm / edit ─────────────────────────────────────────
    filename = ask_filename(suggested)
    if filename is None:
        sys.exit(0)  # user cancelled — exit silently

    filename = sanitise_filename(filename)

    # ── Prepare output path ────────────────────────────────────────────────
    SAVE_FOLDER.mkdir(parents=True, exist_ok=True)
    output_path = unique_path(SAVE_FOLDER, filename, IMAGE_FORMAT)

    # ── Run dezoomify-rs ───────────────────────────────────────────────────
    # dezoomify-rs auto-detects tiled image sources (IIIF, Zoomify, DeepZoom,
    # etc.) from the page URL and writes directly to output_path.
    cmd = build_dezoomify_cmd(URL, output_path, MAX_MEGAPIXELS)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,  # prevent hanging on interactive prompts
            timeout=180  # 3 min — high-res tiles can take a while
        )
    except subprocess.TimeoutExpired:
        alert('dezoomify-rs timed out after 3 minutes.')
        sys.exit(1)
    except FileNotFoundError:
        alert(f'Could not run dezoomify-rs at:\n{DEZOOMIFY_BIN}')
        sys.exit(1)

    if result.returncode != 0:
        error_detail = (result.stderr or result.stdout).strip()
        alert(f'dezoomify-rs failed:\n\n{error_detail[:300]}')
        sys.exit(1)

    if not output_path.exists():
        # dezoomify-rs may have chosen a different extension — try to find it
        found = list(SAVE_FOLDER.glob(f'{filename}.*'))
        if found:
            output_path = found[0]
        else:
            alert(
                'dezoomify-rs reported success but no output file was found.\n'
                f'Check: {SAVE_FOLDER}'
            )
            sys.exit(1)

    # ── Write metadata sidecar ─────────────────────────────────────────────
    write_metadata(output_path, dezoomify_version)

    # ── Output for Alfred notification step ───────────────────────────────
    w, h = get_image_dimensions(output_path)
    size_str = f' ({w}×{h}px)' if w and h else ''
    print(f'{output_path.name}{size_str}')


if __name__ == '__main__':
    main()
