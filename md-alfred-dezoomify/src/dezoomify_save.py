#!/usr/bin/env python3
"""
dezoomify_save.py — v1.2
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
  v1.2 - HTML scraping fallback: when dezoomify-rs can't auto-detect the
         tiled image from the page URL, fetches the page HTML and extracts
         candidate tile URLs using site-specific scrapers. Supports:
         National Gallery (IIPImage/IIIF), Rijksmuseum (Micrio/IIIF),
         NGV (Zoomify), plus generic IIIF/DeepZoom/Zoomify patterns.
         Extracted run_dezoomify() for retry logic. Metadata now records
         the actual URL used (which may differ from the page URL).
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
from urllib.request import urlopen, Request
from urllib.parse import urlparse, urljoin
from urllib.error import URLError, HTTPError


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


def write_metadata(image_path: Path, dezoomify_version: str, actual_url: str = '') -> Path:
    """Write a JSON sidecar file alongside the image."""
    width, height = get_image_dimensions(image_path)
    file_size_bytes = image_path.stat().st_size

    meta = {
        # ── Provenance ────────────────────────────────────────────────────
        'source_url':    URL,
        'tile_url':      actual_url if actual_url != URL else None,
        # tile_url records the URL actually passed to dezoomify-rs, if it
        # differs from the page URL (i.e. the scraper found a different
        # endpoint). None means the page URL worked directly.
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


# ── HTML scraping fallback ─────────────────────────────────────────────────────
#
# When dezoomify-rs can't auto-detect a tiled image from the page URL, we fetch
# the page HTML and search for known patterns. This is modelled on dezoomify
# (web version)'s per-site dezoomer architecture.
#
# Each scraper returns a list of (candidate_url, label) tuples.


def _fetch_html(url: str, timeout: int = 15) -> str:
    """Fetch a page's HTML source. Returns empty string on failure."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                       'AppleWebKit/605.1.15 (KHTML, like Gecko) '
                       'Version/17.0 Safari/605.1.15',
        'Accept': 'text/html,application/xhtml+xml,*/*',
    }
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or 'utf-8'
            return resp.read().decode(charset, errors='replace')
    except (URLError, HTTPError, OSError, ValueError) as e:
        # Log but don't crash — the caller will handle an empty result
        print(f'[scraper] Could not fetch {url}: {e}', file=sys.stderr)
        return ''


def _scrape_national_gallery(html: str, page_url: str) -> list[tuple[str, str]]:
    """National Gallery (London) — IIPImage server, IIIF tiles.

    The page source contains references to server.iip with TIFF paths like:
      server.iip?FIF=/fronts/N-0508-00-000032-XL-PYR.tif&...
      server.iip?IIIF=/fronts/N-0508-00-000032-XL-PYR.tif/...

    We extract the TIFF path and construct an IIIF info.json URL that
    dezoomify-rs's IIIF dezoomer can handle directly.
    """
    if 'nationalgallery.org.uk' not in page_url:
        return []

    candidates = []
    seen_tifs = set()

    # Pattern 1: FIF= parameter (IIP native protocol references)
    for m in re.finditer(r'server\.iip\?FIF=(/[^&\s"\']+\.tif)', html, re.IGNORECASE):
        tif = m.group(1)
        if tif not in seen_tifs:
            seen_tifs.add(tif)

    # Pattern 2: IIIF= parameter (IIIF protocol references)
    # The TIFF path is followed by IIIF coordinates: /x,y,w,h/size/...
    # Match up to .tif before the next /digit or end of value
    for m in re.finditer(r'server\.iip\?IIIF=(/[^"\'<>\s]+?\.tif)(?:/|\s|"|\'|$)', html, re.IGNORECASE):
        tif = m.group(1)
        if tif not in seen_tifs:
            seen_tifs.add(tif)

    # Pattern 3: bare TIFF path in JS (e.g. in a data object or variable)
    for m in re.finditer(r'["\'](/fronts/N-[^"\']+\.tif)["\']', html):
        tif = m.group(1)
        if tif not in seen_tifs:
            seen_tifs.add(tif)

    base = 'https://www.nationalgallery.org.uk/server.iip?IIIF='
    for tif in seen_tifs:
        info_url = f'{base}{tif}/info.json'
        label = tif.rsplit('/', 1)[-1]  # e.g. N-0508-00-000032-XL-PYR.tif
        candidates.append((info_url, f'NG: {label}'))

    return candidates


def _scrape_rijksmuseum(html: str, page_url: str) -> list[tuple[str, str]]:
    """Rijksmuseum — Micrio viewer, IIIF tiles.

    The Micrio image ID (e.g. 'PJEZO') is embedded in the page JS.
    The IIIF info.json URL is: https://iiif.micr.io/{ID}/info.json
    """
    if 'rijksmuseum.nl' not in page_url:
        return []

    candidates = []
    seen_ids = set()

    # Micrio IDs are short alphanumeric strings, typically 5 chars
    # They appear in iiif.micr.io URLs or as micrio-id attributes
    for m in re.finditer(r'iiif\.micr\.io/([A-Za-z0-9]{4,8})', html):
        mid = m.group(1)
        if mid not in seen_ids:
            seen_ids.add(mid)

    # Also check for data attributes or JS variables
    for m in re.finditer(r'micr(?:io)?[_-]?id["\s:=]+["\']?([A-Za-z0-9]{4,8})', html, re.IGNORECASE):
        mid = m.group(1)
        if mid not in seen_ids:
            seen_ids.add(mid)

    for mid in seen_ids:
        info_url = f'https://iiif.micr.io/{mid}/info.json'
        candidates.append((info_url, f'Micrio: {mid}'))

    return candidates


def _scrape_ngv(html: str, page_url: str) -> list[tuple[str, str]]:
    """NGV (National Gallery of Victoria) — Zoomify tiles.

    The page source contains a Zoomify URL in an ol.source.Zoomify block:
      var url = 'https://content.ngv.vic.gov.au/col-images/zooms/{ID}/'
    """
    if 'ngv.vic.gov.au' not in page_url:
        return []

    candidates = []
    for m in re.finditer(
        r'(https?://content\.ngv\.vic\.gov\.au/col-images/zooms/[^/\s"\']+/)', html
    ):
        zoom_url = m.group(1)
        props_url = zoom_url + 'ImageProperties.xml'
        label = zoom_url.rstrip('/').rsplit('/', 1)[-1]
        candidates.append((props_url, f'NGV Zoomify: {label}'))

    return candidates


def _scrape_generic_patterns(html: str, page_url: str) -> list[tuple[str, str]]:
    """Generic patterns: catch IIIF info.json, manifests, and DZI files
    that appear anywhere in the page source."""
    candidates = []
    seen = set()

    # IIIF info.json URLs
    for m in re.finditer(r'(https?://[^\s"\'<>]+/info\.json)', html):
        url = m.group(1)
        if url not in seen:
            seen.add(url)
            candidates.append((url, f'IIIF: {urlparse(url).netloc}'))

    # IIIF manifest URLs
    for m in re.finditer(r'(https?://[^\s"\'<>]+/manifest\.json)', html):
        url = m.group(1)
        if url not in seen:
            seen.add(url)
            candidates.append((url, f'Manifest: {urlparse(url).netloc}'))

    # DeepZoom .dzi files
    for m in re.finditer(r'(https?://[^\s"\'<>]+\.dzi)', html, re.IGNORECASE):
        url = m.group(1)
        if url not in seen:
            seen.add(url)
            candidates.append((url, f'DeepZoom: {urlparse(url).netloc}'))

    # Zoomify ImageProperties.xml
    for m in re.finditer(r'(https?://[^\s"\'<>]+ImageProperties\.xml)', html, re.IGNORECASE):
        url = m.group(1)
        if url not in seen:
            seen.add(url)
            candidates.append((url, f'Zoomify: {urlparse(url).netloc}'))

    # IIPImage FIF= URLs (generic, not NG-specific)
    for m in re.finditer(r'(https?://[^\s"\'<>]+server\.iip\?FIF=[^\s"\'<>&]+)', html, re.IGNORECASE):
        url = m.group(1)
        if url not in seen:
            seen.add(url)
            candidates.append((url, f'IIPImage: {urlparse(url).netloc}'))

    return candidates


def scrape_tile_url(page_url: str) -> list[tuple[str, str]]:
    """Fetch the page HTML and extract candidate tiled image URLs.

    Returns a deduplicated list of (url, label) tuples. Site-specific
    scrapers run first (they're more reliable), then generic patterns
    fill in anything they missed.
    """
    html = _fetch_html(page_url)
    if not html:
        return []

    # Run site-specific scrapers first
    candidates = []
    for scraper in [_scrape_national_gallery, _scrape_rijksmuseum, _scrape_ngv]:
        results = scraper(html, page_url)
        if results:
            candidates.extend(results)

    # If no site-specific hits, try generic patterns
    if not candidates:
        candidates = _scrape_generic_patterns(html, page_url)

    # Deduplicate by URL, preserving order
    seen = set()
    deduped = []
    for url, label in candidates:
        if url not in seen:
            seen.add(url)
            deduped.append((url, label))

    return deduped


def choose_candidate(candidates: list[tuple[str, str]]) -> str | None:
    """Show a macOS choose-from-list dialog if there are multiple candidates.
    Returns the chosen URL, or None if cancelled."""
    if len(candidates) == 1:
        return candidates[0][0]

    labels = [f'{label}  →  {url}' for url, label in candidates]
    items = ', '.join(f'"{l}"' for l in labels)
    script = (
        f'choose from list {{{items}}} '
        f'with title "Dezoomify Grab" '
        f'with prompt "Multiple tiled images found. Which to download?" '
        f'default items {{"{labels[0]}"}}'
    )
    result = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return None  # user cancelled

    chosen_label = result.stdout.strip()
    if chosen_label == 'false':
        return None

    # Map the chosen label back to its URL
    for url, label in candidates:
        display = f'{label}  →  {url}'
        if display == chosen_label:
            return url

    # Fallback: return the first candidate
    return candidates[0][0]


def run_dezoomify(url: str, output_path: Path, max_mp: str) -> tuple[bool, str]:
    """Run dezoomify-rs on a single URL. Returns (success, error_detail)."""
    cmd = build_dezoomify_cmd(url, output_path, max_mp)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=180
        )
    except subprocess.TimeoutExpired:
        return False, 'dezoomify-rs timed out after 3 minutes.'
    except FileNotFoundError:
        return False, f'Could not run dezoomify-rs at: {DEZOOMIFY_BIN}'

    if result.returncode != 0:
        error_detail = (result.stderr or result.stdout).strip()
        return False, error_detail

    return True, ''


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

    # ── Try 1: page URL directly ──────────────────────────────────────────
    # dezoomify-rs auto-detects tiled image sources (IIIF, Zoomify, DeepZoom,
    # etc.) from the page URL.
    actual_url = URL
    success, error_detail = run_dezoomify(URL, output_path, MAX_MEGAPIXELS)

    # ── Try 2: HTML scraping fallback ─────────────────────────────────────
    # If dezoomify-rs couldn't find a tiled image, fetch the page HTML and
    # search for known tile URL patterns (IIPImage, Micrio, Zoomify, etc.)
    if not success and 'none succeeded' in error_detail.lower():
        print('[scraper] Direct URL failed, trying HTML scraping…', file=sys.stderr)
        candidates = scrape_tile_url(URL)

        if candidates:
            chosen = choose_candidate(candidates)
            if chosen:
                actual_url = chosen
                success, error_detail = run_dezoomify(chosen, output_path, MAX_MEGAPIXELS)

    # ── Handle final failure ──────────────────────────────────────────────
    if not success:
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
    write_metadata(output_path, dezoomify_version, actual_url)

    # ── Output for Alfred notification step ───────────────────────────────
    w, h = get_image_dimensions(output_path)
    size_str = f' ({w}×{h}px)' if w and h else ''
    print(f'{output_path.name}{size_str}')


if __name__ == '__main__':
    main()
