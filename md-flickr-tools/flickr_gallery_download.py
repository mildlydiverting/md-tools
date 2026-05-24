#!/usr/bin/env python3
"""
flickr_gallery_download.py
--------------------------
Downloads images from Flickr galleries, with structured JSON metadata.

By default, fetches all galleries owned by the authenticated user.
Pass --gallery-url or --gallery-id to download a specific gallery instead.

Usage:
    python flickr_gallery_download.py                          # All your galleries
    python flickr_gallery_download.py --gallery-url URL        # Specific gallery by URL
    python flickr_gallery_download.py --gallery-id GALLERY_ID  # Specific gallery by ID
    python flickr_gallery_download.py --reset                  # Re-download everything

Output:
    flickr_downloads/
      galleries/
        [gallery-title-slug]/
          _gallery_manifest.json
          55186319833_Photo Title.jpg
          55186319833_Photo Title.json

Requirements:
    pip install flickrapi requests python-dotenv

Setup:
    Copy .env.example to .env and fill in FLICKR_API_KEY and FLICKR_API_SECRET.
    On first run you'll be directed to a URL to authorise access.
    The OAuth token is cached at ~/.flickr/ after first auth.
"""

import os
import re
import sys
import json
import time
import argparse
import datetime
import requests
import flickrapi
from dotenv import load_dotenv

# ─── CONFIG ──────────────────────────────────────────────────────────────────

load_dotenv()

API_KEY    = os.getenv("FLICKR_API_KEY", "")
API_SECRET = os.getenv("FLICKR_API_SECRET", "")

BASE_OUTPUT_DIR = "./flickr_downloads/galleries"

# Rate limit: pause between API calls (seconds)
RATE_DELAY = 0.5

# Image size preference, largest first, capped at ~3K.
# Falls through to next if a size isn't available.
SIZE_PREFERENCE = [
    "X-Large 3K",   # 3072px
    "Large 2048",   # 2048px
    "Large 1600",   # 1600px
    "Large",        # 1024px
    "Medium 800",   # 800px
    "Medium 640",   # 640px
    "Medium",       # 500px
    "Small 400",    # 400px
    "Small",        # 240px
]

# Flickr licence IDs → (name, url)
# https://www.flickr.com/services/api/flickr.photos.licenses.getInfo.html
FLICKR_LICENSES = {
    "0":  ("All Rights Reserved",                    ""),
    "1":  ("Attribution-NonCommercial-ShareAlike 2.0", "https://creativecommons.org/licenses/by-nc-sa/2.0/"),
    "2":  ("Attribution-NonCommercial 2.0",            "https://creativecommons.org/licenses/by-nc/2.0/"),
    "3":  ("Attribution-NonCommercial-NoDerivs 2.0",   "https://creativecommons.org/licenses/by-nc-nd/2.0/"),
    "4":  ("Attribution 2.0",                          "https://creativecommons.org/licenses/by/2.0/"),
    "5":  ("Attribution-ShareAlike 2.0",               "https://creativecommons.org/licenses/by-sa/2.0/"),
    "6":  ("Attribution-NoDerivs 2.0",                 "https://creativecommons.org/licenses/by-nd/2.0/"),
    "7":  ("No known copyright restrictions",          "https://www.flickr.com/commons/usage/"),
    "8":  ("United States Government Work",            "http://www.usa.gov/copyright.shtml"),
    "9":  ("Public Domain Dedication (CC0)",           "https://creativecommons.org/publicdomain/zero/1.0/"),
    "10": ("Public Domain Mark",                       "https://creativecommons.org/publicdomain/mark/1.0/"),
}

# Date granularity codes from Flickr
DATE_GRANULARITY = {
    0: ("exact",  "Exact datetime (owner's local timezone — do not convert)"),
    4: ("month",  "Month and year only"),
    6: ("year",   "Year only"),
    8: ("circa",  "Approximate / circa"),
}


# ─── AUTHENTICATION ───────────────────────────────────────────────────────────

def get_flickr():
    """Authenticate with Flickr via OAuth. Token is cached after first run."""
    if not API_KEY or not API_SECRET:
        sys.exit("Error: FLICKR_API_KEY and FLICKR_API_SECRET must be set in .env")
    flickr = flickrapi.FlickrAPI(API_KEY, API_SECRET, format='parsed-json')
    if not flickr.token_valid(perms='read'):
        flickr.get_request_token(oauth_callback='oob')
        auth_url = flickr.auth_url(perms='read')
        print(f"\nVisit this URL to authorise access:\n\n  {auth_url}\n")
        verifier = input("Paste the verifier code here: ").strip()
        flickr.get_access_token(verifier)
    return flickr


# ─── UTILITIES ───────────────────────────────────────────────────────────────

def slugify(text, max_len=60):
    """Turn a gallery title into a safe directory name."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = text.strip('-')
    return text[:max_len]


def safe_filename(photo_id, title, ext):
    """Construct a safe filename: ID_Title.ext"""
    safe_title = re.sub(r'[^\w\s-]', '', title).strip()
    safe_title = re.sub(r'[\s]+', ' ', safe_title)[:80]
    return f"{photo_id}_{safe_title}{ext}"


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def load_manifest(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_manifest(path, manifest):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


# ─── GALLERY RESOLUTION ───────────────────────────────────────────────────────

def gallery_id_from_url(url):
    """
    Extract gallery ID from a Flickr gallery URL.
    Handles:
      https://www.flickr.com/photos/username/galleries/72157723831831179/
      https://www.flickr.com/photos/username/galleries/72157723831831179/with/PHOTO_ID
    """
    match = re.search(r'/galleries/(\d+)', url)
    if match:
        return match.group(1)
    sys.exit(f"Could not extract gallery ID from URL: {url}")


def get_gallery_info(flickr, gallery_id):
    """Fetch gallery title, description, and owner NSID."""
    resp = flickr.galleries.getInfo(gallery_id=gallery_id)
    gallery = resp['gallery']
    return {
        'gallery_id':    gallery_id,
        'title':         gallery.get('title', {}).get('_content', gallery_id),
        'description':   gallery.get('description', {}).get('_content', ''),
        'owner_nsid':    gallery.get('owner', ''),
        'gallery_url':   gallery.get('url', ''),
        'photo_count':   gallery.get('count_photos', 0),
    }


def get_my_galleries(flickr):
    """Return list of gallery info dicts for the authenticated user."""
    user_resp = flickr.test.login()
    nsid = user_resp['user']['id']

    galleries = []
    page = 1
    while True:
        resp = flickr.galleries.getList(user_id=nsid, per_page=100, page=page)
        items = resp.get('galleries', {}).get('gallery', [])
        if not items:
            break
        for g in items:
            galleries.append({
                'gallery_id':  g['id'],
                'title':       g.get('title', {}).get('_content', g['id']),
                'description': g.get('description', {}).get('_content', ''),
                'owner_nsid':  nsid,
                'gallery_url': g.get('url', ''),
                'photo_count': g.get('count_photos', 0),
            })
        pages = resp.get('galleries', {}).get('pages', 1)
        if page >= pages:
            break
        page += 1
        time.sleep(RATE_DELAY)

    return galleries


# ─── PHOTO FETCHING ───────────────────────────────────────────────────────────

def get_gallery_photos(flickr, gallery_id):
    """Return list of photo dicts (id, title) for a gallery."""
    photos = []
    page = 1
    while True:
        resp = flickr.galleries.getPhotos(
            gallery_id=gallery_id,
            extras='description,tags,owner_name,license,date_upload,date_taken,date_taken_granularity,geo',
            per_page=100,
            page=page,
        )
        items = resp.get('photos', {}).get('photo', [])
        if not items:
            break
        photos.extend(items)
        pages = resp.get('photos', {}).get('pages', 1)
        if page >= pages:
            break
        page += 1
        time.sleep(RATE_DELAY)
    return photos


def get_best_size(flickr, photo_id):
    """Return (url, size_label, ext) for the largest acceptable size."""
    resp = flickr.photos.getSizes(photo_id=photo_id)
    sizes = {s['label']: s for s in resp.get('sizes', {}).get('size', [])}
    for label in SIZE_PREFERENCE:
        if label in sizes:
            src = sizes[label]['source']
            ext = os.path.splitext(src.split('?')[0])[1] or '.jpg'
            return src, label, ext
    # Fallback: largest available
    if sizes:
        largest = list(sizes.values())[-1]
        src = largest['source']
        ext = os.path.splitext(src.split('?')[0])[1] or '.jpg'
        return src, largest['label'], ext
    return None, None, None


def get_photo_info(flickr, photo_id):
    """Fetch full photo info including location."""
    resp = flickr.photos.getInfo(photo_id=photo_id)
    return resp.get('photo', {})


# ─── METADATA BUILDER ────────────────────────────────────────────────────────

def build_metadata(photo_stub, photo_info, gallery_info, src_url, size_label):
    """
    Assemble the metadata dict. Schema kept consistent with flickr_download.py.
    """
    photo_id = photo_stub['id']
    title    = photo_info.get('title', {}).get('_content', '') or photo_stub.get('title', '')

    # Owner
    owner       = photo_info.get('owner', {})
    creator     = owner.get('realname') or owner.get('username', '')
    creator_url = f"https://www.flickr.com/photos/{owner.get('nsid', '')}/"

    # Dates
    dates    = photo_info.get('dates', {})
    taken    = dates.get('taken', '')
    gran_raw = int(dates.get('takengranularity', 0))
    gran_key, gran_note = DATE_GRANULARITY.get(gran_raw, ("exact", ""))
    posted_ts = dates.get('posted', '')
    try:
        posted_date = datetime.datetime.fromtimestamp(
            int(posted_ts), tz=datetime.timezone.utc
        ).strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        posted_date = ''

    # Description
    desc_raw = photo_info.get('description', {}).get('_content', '')

    # Tags
    tags_raw = photo_info.get('tags', {}).get('tag', [])
    tags = [t['raw'] for t in tags_raw] if isinstance(tags_raw, list) else []

    # License
    license_id   = str(photo_info.get('license', '0'))
    license_name, license_url = FLICKR_LICENSES.get(license_id, ('Unknown', ''))

    # Location
    location_data = None
    loc = photo_info.get('location')
    if loc:
        location_data = {
            'latitude':  loc.get('latitude', ''),
            'longitude': loc.get('longitude', ''),
            'locality':  loc.get('locality',  {}).get('_content', ''),
            'region':    loc.get('region',    {}).get('_content', ''),
            'country':   loc.get('country',   {}).get('_content', ''),
        }

    accessed_url = f"https://www.flickr.com/photos/{owner.get('nsid', '')}/{photo_id}"
    date_accessed = now_utc().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    year_accessed = now_utc().strftime('%Y')
    year_created  = taken[:4] if taken else ''

    # Citations
    citation_markdown = (
        f"{creator} ({year_created or year_accessed}). _{title}_. "
        f"[Photograph]. Available at {accessed_url} "
        f"(Accessed {now_utc().strftime('%-d %b %Y')}). {license_name}."
    )

    tasl = (
        f"[{title}]({accessed_url})"
        f" — [{creator}]({creator_url})"
        f" — [{license_name}]({license_url})" if license_url
        else f"[{title}]({accessed_url}) — [{creator}]({creator_url}) — {license_name}"
    )

    return {
        "photo_id":               photo_id,
        "title":                  title,
        "accessed_url":           accessed_url,
        "src_url":                src_url,
        "size_label":             size_label,
        "date_created":           taken,
        "date_created_granularity": gran_raw,
        "date_created_note":      gran_note,
        "date_posted":            posted_date,
        "date_accessed":          date_accessed,
        "medium":                 "Photograph",
        "description":            desc_raw,
        "description_format":     "html",
        "tags":                   tags,
        "gallery": {
            "gallery_id":   gallery_info['gallery_id'],
            "title":        gallery_info['title'],
            "gallery_url":  gallery_info['gallery_url'],
        },
        "creator":              creator,
        "creator_profile_url":  creator_url,
        "institution":          None,
        "institution_location": None,
        "website":              "Flickr",
        "website_url":          "https://www.flickr.com",
        "license_id":           license_id,
        "license_name":         license_name,
        "license_url":          license_url,
        "copyright_line":       None,
        "citation_markdown":    citation_markdown,
        "tasl":                 tasl,
        "location":             location_data,
    }


# ─── DOWNLOADER ───────────────────────────────────────────────────────────────

def download_image(src_url, dest_path):
    """Download an image file to dest_path. Returns True on success."""
    try:
        resp = requests.get(src_url, timeout=30, stream=True)
        resp.raise_for_status()
        with open(dest_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"    ✗ Download failed: {e}")
        return False


# ─── GALLERY PROCESSOR ───────────────────────────────────────────────────────

def process_gallery(flickr, gallery_info, reset=False):
    """Download all photos in a gallery into a slug-named subfolder."""
    slug      = slugify(gallery_info['title']) or gallery_info['gallery_id']
    out_dir   = os.path.join(BASE_OUTPUT_DIR, slug)
    manifest_path = os.path.join(out_dir, '_gallery_manifest.json')

    os.makedirs(out_dir, exist_ok=True)

    manifest = {} if reset else load_manifest(manifest_path)

    print(f"\n{'─'*60}")
    print(f"Gallery: {gallery_info['title']}  ({gallery_info['photo_count']} photos)")
    print(f"Output:  {out_dir}")
    print(f"{'─'*60}")

    photos = get_gallery_photos(flickr, gallery_info['gallery_id'])
    print(f"  Fetched {len(photos)} photo records from API")

    downloaded = 0
    skipped    = 0
    failed     = 0

    for photo in photos:
        photo_id = photo['id']
        title    = photo.get('title', photo_id)

        if photo_id in manifest and not reset:
            skipped += 1
            continue

        print(f"  [{photo_id}] {title[:50]}")

        # Full info (for description, location, dates, license)
        time.sleep(RATE_DELAY)
        photo_info = get_photo_info(flickr, photo_id)

        # Best available size
        time.sleep(RATE_DELAY)
        src_url, size_label, ext = get_best_size(flickr, photo_id)

        if not src_url:
            print(f"    ✗ No downloadable size found — skipping")
            failed += 1
            continue

        filename_base = safe_filename(photo_id, title, '')
        img_path  = os.path.join(out_dir, filename_base + ext)
        json_path = os.path.join(out_dir, filename_base + '.json')

        # Build metadata
        metadata = build_metadata(photo, photo_info, gallery_info, src_url, size_label)

        # Download image
        print(f"    → {size_label}  {src_url[-50:]}")
        ok = download_image(src_url, img_path)
        if not ok:
            failed += 1
            continue

        # Save JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        manifest[photo_id] = {
            'title':      title,
            'filename':   filename_base + ext,
            'downloaded': metadata['date_accessed'],
        }
        save_manifest(manifest_path, manifest)
        downloaded += 1

    print(f"\n  Done: {downloaded} downloaded, {skipped} skipped, {failed} failed")
    return downloaded, skipped, failed


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Download Flickr gallery images with metadata.'
    )
    parser.add_argument('--gallery-url',  help='Full URL of a specific Flickr gallery')
    parser.add_argument('--gallery-id',   help='Numeric ID of a specific Flickr gallery')
    parser.add_argument('--reset',        action='store_true',
                        help='Ignore existing manifest and re-download everything')
    args = parser.parse_args()

    flickr = get_flickr()
    os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)

    # ── Single gallery mode ──────────────────────────────────────────────────
    if args.gallery_url or args.gallery_id:
        gid = args.gallery_id or gallery_id_from_url(args.gallery_url)
        print(f"Fetching info for gallery {gid}…")
        time.sleep(RATE_DELAY)
        gallery_info = get_gallery_info(flickr, gid)
        process_gallery(flickr, gallery_info, reset=args.reset)

    # ── All my galleries mode ────────────────────────────────────────────────
    else:
        print("Fetching your galleries…")
        galleries = get_my_galleries(flickr)
        print(f"Found {len(galleries)} galleries\n")
        for g in galleries:
            process_gallery(flickr, g, reset=args.reset)

    print("\n✓ All done.")


if __name__ == '__main__':
    main()
