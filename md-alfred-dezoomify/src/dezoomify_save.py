#!/usr/bin/env python3
"""
dezoomify_save.py — v1.3
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
  v1.3 - IIIF v2 manifest resolver: dezoomify-rs only parses IIIF
         Presentation v3 manifests. Many museum sites (AIC, Harvard,
         Wellcome, etc.) still serve v2. When the scraper finds a
         manifest.json URL, we now fetch it ourselves, detect v2 vs v3,
         and extract the IIIF Image API info.json URL(s) from the
         canvas/image structure. Also adds AIC site-specific scraper
         using their public API.
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
import tempfile
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

# Alfred sets alfred_workflow_cache to a per-workflow volatile cache dir.
# We download to cache first, then move to SAVE_FOLDER on success.
# This avoids partial files littering the user's save folder on failure.
_cache_dir     = os.environ.get('alfred_workflow_cache', '')
CACHE_DIR      = Path(_cache_dir) if _cache_dir else Path(tempfile.gettempdir()) / 'dezoomify-alfred'

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
    """Build the dezoomify-rs command.

    -l and --max-width are mutually exclusive zoom level selectors:
    - If max_megapixels is set, use --max-width/--max-height to cap the size
      (this also selects the appropriate zoom level, no -l needed)
    - Otherwise, use -l to select the largest level and avoid the interactive
      prompt
    """
    cmd = [DEZOOMIFY_BIN]

    size_limited = False
    if max_megapixels_str:
        try:
            max_mp = float(max_megapixels_str)
            if max_mp > 0:
                max_side = int(math.sqrt(max_mp * 1_000_000))
                cmd += ['--max-width', str(max_side), '--max-height', str(max_side)]
                size_limited = True
        except ValueError:
            pass

    if not size_limited:
        cmd.append('-l')   # -l = select largest; no interactive prompt

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
    safe = message.replace('\\', '\\\\').replace('"', '\\"')
    subprocess.run(
        ['osascript', '-e', f'display alert "Dezoomify Grab" message "{safe}"'],
        capture_output=True
    )


def _log(msg: str):
    """Log to stderr. Visible in Terminal and Alfred's debug log, but not
    in the notification output (which reads stdout)."""
    print(f'[dezoomify] {msg}', file=sys.stderr, flush=True)


def ask_manual_url() -> str | None:
    """Last resort: ask the user to paste a tile URL from their browser's
    network inspector. Returns the URL string, or None if cancelled."""
    script = (
        'display dialog '
        '"Automatic detection failed.\\n\\n'
        'Open the browser Network Inspector, zoom into the image, '
        'and look for tile requests containing server.iip, info.json, '
        'or ImageProperties.xml.\\n\\n'
        'Paste a tile URL below:" '
        'default answer "" '
        'with title "Dezoomify Grab" '
        'buttons {"Cancel", "Try URL"} '
        'default button "Try URL"'
    )
    result = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    match = re.search(r'text returned:(.+)', result.stdout.strip())
    url = match.group(1).strip() if match else ''
    return url if url else None


# ── HTML scraping fallback ─────────────────────────────────────────────────────
#
# When dezoomify-rs can't auto-detect a tiled image from the page URL, we fetch
# the page HTML and search for known patterns. This is modelled on dezoomify
# (web version)'s per-site dezoomer architecture.
#
# Each scraper returns a list of (candidate_url, label) tuples.


def _fetch_html(url: str, timeout: int = 15) -> str:
    """Fetch a page's HTML source. Returns empty string on failure."""
    _log(f'Fetching HTML from {url}')
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
            html = resp.read().decode(charset, errors='replace')
            _log(f'Fetched {len(html)} chars (status {resp.status})')
            return html
    except (URLError, HTTPError, OSError, ValueError) as e:
        _log(f'Fetch failed: {e}')
        return ''


def _scrape_national_gallery(html: str, page_url: str) -> list[tuple[str, str]]:
    """National Gallery (London) — IIPImage server, IIIF tiles.

    The TIFF path may appear in several places:
    - og:image or other meta tags with a server.iip preview URL
    - Inline JS with server.iip?FIF= or server.iip?IIIF= references
    - Bare TIFF path strings in JS data objects
    - Any URL containing server.iip (broadest catch)

    We extract the TIFF path and construct an IIIF info.json URL that
    dezoomify-rs's IIIF dezoomer can handle directly.
    """
    if 'nationalgallery.org.uk' not in page_url:
        return []

    _log('Running National Gallery scraper')
    candidates = []
    seen_tifs = set()

    # Pattern 1: FIF= parameter (IIP native protocol, e.g. in og:image)
    for m in re.finditer(r'server\.iip\?FIF=(/[^&\s"\'<>]+\.tif)', html, re.IGNORECASE):
        tif = m.group(1)
        if tif not in seen_tifs:
            seen_tifs.add(tif)
            _log(f'  Found TIFF via FIF=: {tif}')

    # Pattern 2: IIIF= parameter (IIIF protocol references)
    for m in re.finditer(r'server\.iip\?IIIF=(/[^"\'<>\s]+?\.tif)(?:/|\s|"|\'|$)', html, re.IGNORECASE):
        tif = m.group(1)
        if tif not in seen_tifs:
            seen_tifs.add(tif)
            _log(f'  Found TIFF via IIIF=: {tif}')

    # Pattern 3: DeepZoom= parameter (older NG setup)
    for m in re.finditer(r'server\.iip\?DeepZoom=(/[^"\'<>\s]+?\.tif)\.dzi', html, re.IGNORECASE):
        tif = m.group(1)
        if tif not in seen_tifs:
            seen_tifs.add(tif)
            _log(f'  Found TIFF via DeepZoom=: {tif}')

    # Pattern 4: bare TIFF path in JS (e.g. in a data object or variable)
    for m in re.finditer(r'["\'](/fronts/N-[^"\']+\.tif)["\']', html):
        tif = m.group(1)
        if tif not in seen_tifs:
            seen_tifs.add(tif)
            _log(f'  Found TIFF bare path: {tif}')

    # Pattern 5: og:image or any meta/img tag with server.iip
    # e.g. <meta property="og:image" content="...server.iip?FIF=/fronts/N-0508-...tif&WID=800...">
    for m in re.finditer(r'(?:content|src|href)=["\']([^"\']*server\.iip[^"\']*)["\']', html, re.IGNORECASE):
        iip_url = m.group(1)
        # Extract TIFF path from any IIP parameter
        tif_match = re.search(r'(?:FIF|IIIF|DeepZoom|Zoomify)=(/[^&"\'<>\s]+?\.tif)', iip_url, re.IGNORECASE)
        if tif_match:
            tif = tif_match.group(1)
            if tif not in seen_tifs:
                seen_tifs.add(tif)
                _log(f'  Found TIFF in meta/attr: {tif}')

    if not seen_tifs:
        _log('  No TIFF paths found in static HTML')

    base = 'https://www.nationalgallery.org.uk/server.iip'
    for tif in seen_tifs:
        # IIPImage native (FIF=) — confirmed working with dezoomify-rs's
        # IIPImage dezoomer (see lovasoa/dezoomify#49)
        candidates.append((
            f'{base}?FIF={tif}',
            f'NG IIPImage: {tif.rsplit("/", 1)[-1]}'))
        # DeepZoom fallback
        candidates.append((
            f'{base}?DeepZoom={tif}.dzi',
            f'NG DeepZoom: {tif.rsplit("/", 1)[-1]}'))

    # Also check for manifest URL (altTemplate=PaintingManifest)
    for m in re.finditer(
        r'(https?://[^"\'<>\s]+\?altTemplate=PaintingManifest[^"\'<>\s]*)', html
    ):
        manifest_url = m.group(1).replace('&amp;', '&')
        candidates.append((manifest_url, 'NG IIIF Manifest'))
        _log(f'  Found manifest URL: {manifest_url}')

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


def _scrape_artic(html: str, page_url: str) -> list[tuple[str, str]]:
    """Art Institute of Chicago — IIIF via Mirador viewer.

    AIC's public API returns an image_id (UUID) for each artwork.
    The IIIF info.json URL is: https://www.artic.edu/iiif/2/{image_id}/info.json

    The artwork ID is in the page URL: /artworks/{id}/...
    The manifest at api.artic.edu is IIIF Presentation v2, which dezoomify-rs
    can't parse directly — so we go straight to the info.json via the API.
    """
    if 'artic.edu' not in page_url:
        return []

    _log('Running AIC scraper')

    # Extract artwork ID from URL: /artworks/103887/...
    m = re.search(r'/artworks/(\d+)', page_url)
    if not m:
        _log('  No artwork ID found in URL')
        return []

    artwork_id = m.group(1)
    api_url = f'https://api.artic.edu/api/v1/artworks/{artwork_id}?fields=image_id,title'

    try:
        _log(f'  Fetching AIC API: {api_url}')
        req = Request(api_url, headers={
            'User-Agent': 'dezoomify-alfred/1.3',
            'Accept': 'application/json',
        })
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            image_id = data.get('data', {}).get('image_id')
            title = data.get('data', {}).get('title', '')
            if image_id:
                info_url = f'https://www.artic.edu/iiif/2/{image_id}/info.json'
                _log(f'  Found image_id: {image_id}')
                label = f'AIC IIIF: {title}' if title else f'AIC IIIF: {image_id}'
                return [(info_url, label)]
            else:
                _log('  API returned no image_id')
    except (URLError, HTTPError, OSError, ValueError, KeyError) as e:
        _log(f'  AIC API failed: {e}')

    return []


def _resolve_iiif_manifests(candidates: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Resolve IIIF manifest URLs to info.json URLs.

    dezoomify-rs supports IIIF Presentation v3 manifests but not v2 (which
    use @type/sc:Manifest instead of type/Manifest). Many museum sites still
    serve v2. This function fetches any manifest.json candidates, extracts
    the IIIF Image API service URLs from the canvas structure, and returns
    info.json URLs that dezoomify-rs's IIIF dezoomer can handle directly.

    Non-manifest candidates are passed through unchanged.

    IIIF Presentation v2 structure:
      sequences[].canvases[].images[].resource.service.@id → image service
    IIIF Presentation v3 structure:
      items[].items[].items[].body.service[].id → image service
    """
    resolved = []

    for url, label in candidates:
        # Only process manifest.json URLs
        if not url.endswith('/manifest.json') and 'manifest' not in label.lower():
            resolved.append((url, label))
            continue

        _log(f'  Resolving manifest: {url}')
        try:
            req = Request(url, headers={
                'User-Agent': 'dezoomify-alfred/1.3',
                'Accept': 'application/ld+json, application/json',
            })
            with urlopen(req, timeout=10) as resp:
                manifest = json.loads(resp.read().decode('utf-8'))
        except (URLError, HTTPError, OSError, ValueError) as e:
            _log(f'  Failed to fetch manifest: {e}')
            # Keep the original candidate — dezoomify-rs might handle it
            resolved.append((url, label))
            continue

        info_urls = _extract_image_services(manifest)
        if info_urls:
            _log(f'  Extracted {len(info_urls)} info.json URL(s) from manifest')
            for info_url, info_label in info_urls:
                resolved.append((info_url, info_label))
        else:
            _log('  No image services found in manifest — keeping original')
            resolved.append((url, label))

    return resolved


def _extract_image_services(manifest: dict) -> list[tuple[str, str]]:
    """Extract IIIF Image API service URLs from a parsed manifest.

    Handles both Presentation API v2 and v3 structures.
    Returns a list of (info_json_url, label) tuples.
    """
    results = []

    # ── Detect version ────────────────────────────────────────────────────
    is_v2 = (
        manifest.get('@type') == 'sc:Manifest'
        or 'presentation/2' in manifest.get('@context', '')
    )
    is_v3 = (
        manifest.get('type') == 'Manifest'
        or 'presentation/3' in str(manifest.get('@context', ''))
    )

    if is_v2:
        _log('  Manifest is IIIF Presentation v2')
        for seq in manifest.get('sequences', []):
            for canvas in seq.get('canvases', []):
                canvas_label = canvas.get('label', '')
                for image in canvas.get('images', []):
                    resource = image.get('resource', {})
                    service = resource.get('service', {})
                    # service can be a dict or a list
                    services = service if isinstance(service, list) else [service]
                    for svc in services:
                        svc_id = svc.get('@id') or svc.get('id')
                        if svc_id:
                            info_url = svc_id.rstrip('/') + '/info.json'
                            lbl = canvas_label if canvas_label else svc_id.rsplit('/', 1)[-1]
                            results.append((info_url, f'IIIF v2: {lbl}'))

    elif is_v3:
        _log('  Manifest is IIIF Presentation v3')
        # v3: items (canvases) → items (annotation pages) → items (annotations)
        for canvas in manifest.get('items', []):
            canvas_label = canvas.get('label', {})
            # v3 labels are language maps: {"en": ["Label"]}
            if isinstance(canvas_label, dict):
                for vals in canvas_label.values():
                    if isinstance(vals, list) and vals:
                        canvas_label = vals[0]
                        break
                else:
                    canvas_label = ''
            for anno_page in canvas.get('items', []):
                for anno in anno_page.get('items', []):
                    body = anno.get('body', {})
                    body_service = body.get('service', [])
                    services = body_service if isinstance(body_service, list) else [body_service]
                    for svc in services:
                        svc_id = svc.get('id') or svc.get('@id')
                        if svc_id:
                            info_url = svc_id.rstrip('/') + '/info.json'
                            lbl = canvas_label if canvas_label else svc_id.rsplit('/', 1)[-1]
                            results.append((info_url, f'IIIF v3: {lbl}'))

    else:
        _log('  Manifest version not recognised')

    return results


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
        _log('No HTML returned — cannot scrape')
        return []

    # Run site-specific scrapers first
    candidates = []
    for scraper in [_scrape_national_gallery, _scrape_rijksmuseum, _scrape_ngv,
                    _scrape_artic]:
        results = scraper(html, page_url)
        if results:
            candidates.extend(results)

    # If no site-specific hits, try generic patterns
    if not candidates:
        _log('No site-specific matches; trying generic patterns')
        candidates = _scrape_generic_patterns(html, page_url)

    # Deduplicate by URL, preserving order
    seen = set()
    deduped = []
    for url, label in candidates:
        if url not in seen:
            seen.add(url)
            deduped.append((url, label))

    # Resolve any IIIF manifest URLs to info.json URLs.
    # dezoomify-rs can't parse IIIF Presentation v2 manifests (which use
    # @type/sc:Manifest). We fetch them ourselves and extract the image
    # service info.json URLs that dezoomify-rs's IIIF dezoomer can handle.
    deduped = _resolve_iiif_manifests(deduped)

    _log(f'Scraper found {len(deduped)} candidate(s)')
    for url, label in deduped:
        _log(f'  {label}: {url}')

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


def run_dezoomify(url: str, output_path: Path, max_mp: str,
                  timeout: int = 180) -> tuple[bool, str]:
    """Run dezoomify-rs on a single URL. Returns (success, error_detail).
    timeout is in seconds — use a short value for the initial probe."""
    cmd = build_dezoomify_cmd(url, output_path, max_mp)
    _log(f'Running: {" ".join(cmd[:3])}… (timeout {timeout}s)')
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=timeout
        )
    except subprocess.TimeoutExpired:
        _log(f'Timed out after {timeout}s')
        return False, f'dezoomify-rs timed out after {timeout} seconds.'
    except FileNotFoundError:
        return False, f'Could not run dezoomify-rs at: {DEZOOMIFY_BIN}'

    if result.returncode != 0:
        error_detail = (result.stderr or result.stdout).strip()
        # Log a short excerpt — full error can be very long
        _log(f'Failed: {error_detail[:120]}')
        return False, error_detail

    _log('Success')
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

    # ── Prepare output paths ──────────────────────────────────────────────
    # Download to CACHE_DIR first, then move to SAVE_FOLDER on success.
    # This avoids partial files littering the user's save folder when
    # dezoomify-rs times out, the user cancels, or a retry loop is running.
    SAVE_FOLDER.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    final_path = unique_path(SAVE_FOLDER, filename, IMAGE_FORMAT)
    cache_path = CACHE_DIR / final_path.name

    # ── Try 1: page URL directly (short timeout — fail fast) ────────────
    # dezoomify-rs auto-detects tiled image sources (IIIF, Zoomify, DeepZoom,
    # etc.) from the page URL. Use a 30s timeout: if it can't detect the
    # format quickly, it won't succeed by waiting longer.
    actual_url = URL
    _log(f'Try 1: direct URL → {URL}')
    success, error_detail = run_dezoomify(URL, cache_path, MAX_MEGAPIXELS,
                                          timeout=30)

    # ── Try 2: HTML scraping fallback ─────────────────────────────────────
    # If dezoomify-rs couldn't find a tiled image, fetch the page HTML and
    # search for known tile URL patterns (IIPImage, Micrio, Zoomify, etc.)
    if not success and ('none succeeded' in error_detail.lower()
                        or 'timed out' in error_detail.lower()):
        _log('Try 2: HTML scraping fallback')
        candidates = scrape_tile_url(URL)

        if candidates:
            # Try each candidate URL in order until one works.
            # (Sites like the NG produce multiple URL formats for the same
            # image — IIPImage, DeepZoom, manifest — so we iterate rather
            # than asking the user to choose.)
            for cand_url, cand_label in candidates:
                if cache_path.exists():
                    cache_path.unlink()
                    _log(f'Cleaned up partial file in cache')
                actual_url = cand_url
                _log(f'Trying candidate: {cand_label} → {cand_url}')
                success, error_detail = run_dezoomify(
                    cand_url, cache_path, MAX_MEGAPIXELS, timeout=600)
                if success:
                    break

    # ── Try 3: ask user to paste a URL manually ──────────────────────────
    if not success:
        _log('Try 3: asking user for manual URL')
        manual_url = ask_manual_url()
        if manual_url:
            if cache_path.exists():
                cache_path.unlink()
            actual_url = manual_url
            _log(f'Retrying with manual URL: {manual_url}')
            success, error_detail = run_dezoomify(
                manual_url, cache_path, MAX_MEGAPIXELS, timeout=600)

    # ── Handle final failure ──────────────────────────────────────────────
    if not success:
        # Clean up any partial download in cache
        if cache_path.exists():
            cache_path.unlink()
        alert(f'dezoomify-rs failed:\n\n{error_detail[:300]}')
        sys.exit(1)

    if not cache_path.exists():
        # dezoomify-rs may have chosen a different extension — try to find it
        found = list(CACHE_DIR.glob(f'{filename}.*'))
        if found:
            cache_path = found[0]
            final_path = final_path.with_suffix(cache_path.suffix)
        else:
            alert(
                'dezoomify-rs reported success but no output file was found.\n'
                f'Check: {CACHE_DIR}'
            )
            sys.exit(1)

    # ── Move to final save folder ──────────────────────────────────────────
    shutil.move(str(cache_path), str(final_path))
    _log(f'Saved to {final_path}')

    # ── Write metadata sidecar ─────────────────────────────────────────────
    write_metadata(final_path, dezoomify_version, actual_url)

    # ── Output for Alfred notification step ───────────────────────────────
    w, h = get_image_dimensions(final_path)
    size_str = f' ({w}×{h}px)' if w and h else ''
    print(f'{final_path.name}{size_str}')


if __name__ == '__main__':
    main()
