#!/usr/bin/env python3
"""
flickr_download.py
------------------
Downloads images from your Flickr favourites and galleries.
Saves each image alongside a JSON metadata file with full citation fields.

Usage:
    python flickr_download.py           # Normal run — skips already-downloaded images
    python flickr_download.py --reset   # Clears manifest and re-downloads everything

Requirements:
    pip install flickrapi requests

Setup:
    1. Get a Flickr API key at https://www.flickr.com/services/apps/create/
    2. Fill in API_KEY and API_SECRET below
    3. On first run, you'll be asked to authorise via a browser URL

API methods used:
    flickr.test.login           — confirm auth, retrieve user ID
    flickr.favorites.getList    — fetch all favourited photos
    flickr.galleries.getList    — fetch all galleries belonging to user
    flickr.galleries.getPhotos  — fetch photos within a gallery
    flickr.photos.getInfo       — per-photo: dates, license, owner, location
    flickr.photos.getSizes      — per-photo: available download sizes
"""

import os
import json
import time
import argparse
import datetime
import requests
import flickrapi

# ─── CONFIG ──────────────────────────────────────────────────────────────────

API_KEY    = "YOUR_API_KEY"
API_SECRET = "YOUR_API_SECRET"

OUTPUT_DIR = "./flickr_downloads"
MANIFEST   = os.path.join(OUTPUT_DIR, "_manifest.json")

RATE_DELAY = 0.5  # seconds between API calls

# Image size preference, largest first, capped at ~3K (3072px on longest side).
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

# Flickr license IDs → (name, url)
# https://www.flickr.com/services/api/flickr.photos.licenses.getInfo.html
FLICKR_LICENSES = {
    "0":  ("All Rights Reserved",               None),
    "1":  ("CC BY-NC-SA 2.0",                   "https://creativecommons.org/licenses/by-nc-sa/2.0/"),
    "2":  ("CC BY-NC 2.0",                      "https://creativecommons.org/licenses/by-nc/2.0/"),
    "3":  ("CC BY-NC-ND 2.0",                   "https://creativecommons.org/licenses/by-nc-nd/2.0/"),
    "4":  ("CC BY 2.0",                         "https://creativecommons.org/licenses/by/2.0/"),
    "5":  ("CC BY-SA 2.0",                      "https://creativecommons.org/licenses/by-sa/2.0/"),
    "6":  ("CC BY-ND 2.0",                      "https://creativecommons.org/licenses/by-nd/2.0/"),
    "7":  ("No Known Copyright Restrictions",   "https://www.flickr.com/commons/usage/"),
    "8":  ("United States Government Work",     "http://www.usa.gov/copyright.shtml"),
    "9":  ("CC0 1.0 Public Domain Dedication",  "https://creativecommons.org/publicdomain/zero/1.0/"),
    "10": ("Public Domain Mark 1.0",            "https://creativecommons.org/publicdomain/mark/1.0/"),
}

# Flickr takengranularity values
# https://www.flickr.com/services/api/misc.dates.html
DATE_GRANULARITY = {
    0: "Exact datetime (owner's local timezone — do not convert)",
    4: "Approximate: month precision (Y-m)",
    6: "Approximate: year precision (Y)",
    8: "Circa",
}

# Tags that suggest non-photographic medium
MEDIUM_HINTS = {
    "illustration":        "Illustration",
    "digitalillustration": "Digital Illustration",
    "digitalart":          "Digital Art",
    "digitalpainting":     "Digital Painting",
    "painting":            "Painting",
    "drawing":             "Drawing",
    "sketch":              "Drawing",
    "cgi":                 "CGI",
    "3d":                  "CGI",
    "3drender":            "CGI",
    "render":              "CGI",
    "generativeart":       "Generative Art",
    "aiart":               "AI-Generated Image",
    "aiimage":             "AI-Generated Image",
}


# ─── AUTHENTICATION ───────────────────────────────────────────────────────────

def get_flickr():
    flickr = flickrapi.FlickrAPI(API_KEY, API_SECRET, format='parsed-json')
    if not flickr.token_valid(perms='read'):
        flickr.get_request_token(oauth_callback='oob')
        auth_url = flickr.auth_url(perms='read')
        print(f"\nVisit this URL to authorise access:\n\n  {auth_url}\n")
        verifier = input("Paste the verifier code here: ").strip()
        flickr.get_access_token(verifier)
    return flickr


# ─── MANIFEST ────────────────────────────────────────────────────────────────

def load_manifest():
    if os.path.exists(MANIFEST):
        with open(MANIFEST) as f:
            return json.load(f)
    return {}

def save_manifest(manifest):
    with open(MANIFEST, 'w') as f:
        json.dump(manifest, f, indent=2)


# ─── FETCH FAVOURITES ────────────────────────────────────────────────────────

def get_favourites(flickr):
    print("Fetching favourites...")
    photos = []
    page = 1
    while True:
        resp = flickr.favorites.getList(
            per_page=500, page=page,
            extras='owner_name,title,description,tags,date_faved'
        )
        batch = resp['photos']['photo']
        photos.extend(batch)
        total_pages = int(resp['photos']['pages'])
        print(f"  Page {page}/{total_pages} ({len(batch)} photos)")
        if page >= total_pages:
            break
        page += 1
        time.sleep(RATE_DELAY)
    print(f"  Total favourites: {len(photos)}\n")
    return {p['id']: p for p in photos}


# ─── FETCH GALLERIES ─────────────────────────────────────────────────────────

def get_galleries(flickr, user_id):
    print("Fetching galleries...")
    galleries = []
    page = 1
    while True:
        resp = flickr.galleries.getList(user_id=user_id, per_page=500, page=page)
        batch = resp['galleries']['gallery']
        galleries.extend(batch)
        total_pages = int(resp['galleries']['pages'])
        if page >= total_pages:
            break
        page += 1
        time.sleep(RATE_DELAY)
    print(f"  Total galleries: {len(galleries)}\n")
    return galleries

def get_gallery_photos(flickr, gallery):
    photos = []
    page = 1
    while True:
        resp = flickr.galleries.getPhotos(
            gallery_id=gallery['id'], per_page=500, page=page,
            extras='owner_name,title,description,tags'
        )
        batch = resp['photos']['photo']
        photos.extend(batch)
        total_pages = int(resp['photos']['pages'])
        if page >= total_pages:
            break
        page += 1
        time.sleep(RATE_DELAY)
    return photos


# ─── BUILD COMBINED INDEX ────────────────────────────────────────────────────

def build_index(flickr, user_id):
    favs      = get_favourites(flickr)
    galleries = get_galleries(flickr, user_id)
    index     = {}

    for pid, photo in favs.items():
        index[pid] = {'photo': photo, 'occurrences': [{'type': 'favourite'}]}

    for gallery in galleries:
        title = gallery.get('title', {}).get('_content', gallery['id'])
        print(f"  Fetching gallery: {title}")
        gphotos = get_gallery_photos(flickr, gallery)
        for photo in gphotos:
            pid = photo['id']
            occurrence = {
                'type':          'gallery',
                'gallery_id':    gallery['id'],
                'gallery_title': title,
            }
            if pid in index:
                index[pid]['occurrences'].append(occurrence)
            else:
                index[pid] = {'photo': photo, 'occurrences': [occurrence]}
        time.sleep(RATE_DELAY)

    print(f"\nTotal unique photos: {len(index)}\n")
    return index


# ─── PHOTO INFO ───────────────────────────────────────────────────────────────

def get_photo_info(flickr, photo_id):
    """
    flickr.photos.getInfo — dates, license, owner details, location (if public).
    One API call per photo.
    """
    try:
        resp = flickr.photos.getInfo(photo_id=photo_id)
        return resp.get('photo')
    except Exception as e:
        print(f"    Could not fetch info for {photo_id}: {e}")
        return None


# ─── IMAGE SIZE SELECTION ─────────────────────────────────────────────────────

def get_best_size_url(flickr, photo_id):
    """
    flickr.photos.getSizes — returns all available sizes.
    We try each preferred size in order; fall through if unavailable
    (e.g. owner has restricted downloads).
    """
    try:
        resp = flickr.photos.getSizes(photo_id=photo_id)
        available = {s['label']: s['source'] for s in resp['sizes']['size']}
        for label in SIZE_PREFERENCE:
            if label in available:
                return available[label], label
        for s in resp['sizes']['size']:
            if s['label'].lower() != 'original':
                return s['source'], s['label']
    except Exception as e:
        print(f"    Could not retrieve sizes for {photo_id}: {e}")
    return None, None


# ─── LOCATION ────────────────────────────────────────────────────────────────

def extract_location(info):
    """
    Pull location from getInfo response if present and public.
    Returns a dict or None.
    """
    loc = info.get('location') if info else None
    if not loc:
        return None
    def content(field):
        val = loc.get(field)
        if isinstance(val, dict):
            return val.get('_content') or None
        return val or None
    return {
        "latitude":  loc.get('latitude')  or None,
        "longitude": loc.get('longitude') or None,
        "accuracy":  loc.get('accuracy')  or None,
        "locality":  content('locality'),
        "county":    content('county'),
        "region":    content('region'),
        "country":   content('country'),
    }


# ─── CITATION HELPERS ────────────────────────────────────────────────────────

def format_access_date(iso_string):
    """'2026-04-21T12:00:00Z' → '21 Apr 2026'"""
    dt = datetime.datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
    return dt.strftime("%-d %b %Y")

def infer_medium(tags):
    """Default to Photograph; sniff tag array for evidence of other media."""
    for tag in tags:
        if tag.lower() in MEDIUM_HINTS:
            return MEDIUM_HINTS[tag.lower()]
    return "Photograph"

def build_citation(creator, year, title, medium, institution, institution_location,
                   accessed_url, access_date_str, license_name, license_url):
    """
    Harvard-adjacent citation in Markdown.
    Author (yyyy). _Title_. [Medium]. Institution, Location.
    Available at [URL](URL) (Accessed dd mmm yyyy). Licensed under [Licence](url).
    """
    parts = [f"{creator} ({year}). _{title}_. [{medium}]."]
    if institution:
        loc = f"{institution}, {institution_location}" if institution_location else institution
        parts.append(f" {loc}.")
    parts.append(f" Available at [{accessed_url}]({accessed_url}) (Accessed {access_date_str}).")
    if license_url:
        parts.append(f" Licensed under [{license_name}]({license_url}).")
    else:
        parts.append(f" {license_name}.")
    return "".join(parts)

def build_tasl(title, accessed_url, creator, creator_url, license_name, license_url):
    """
    TASL attribution line in Markdown.
    [Title](page url) — [Author](profile url) — [Licence](url)
    """
    title_part   = f"[{title}]({accessed_url})"
    creator_part = f"[{creator}]({creator_url})" if creator_url else creator
    license_part = f"[{license_name}]({license_url})" if license_url else license_name
    return f"{title_part} — {creator_part} — {license_part}"


# ─── DOWNLOAD ────────────────────────────────────────────────────────────────

def download_image(url, filepath):
    r = requests.get(url, stream=True, timeout=30)
    r.raise_for_status()
    with open(filepath, 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

def safe_filename(s, max_len=60):
    return "".join(c if c.isalnum() or c in ' _-' else '_' for c in s)[:max_len].strip()

def process_photo(flickr, photo_id, entry, output_dir, manifest):
    photo = entry['photo']
    title = photo.get('title', '') or photo_id
    base  = f"{photo_id}_{safe_filename(title)}"
    img_path  = os.path.join(output_dir, f"{base}.jpg")
    json_path = os.path.join(output_dir, f"{base}.json")

    if photo_id in manifest:
        print(f"  [skip]  {title}")
        return

    # Extended info — flickr.photos.getInfo
    time.sleep(RATE_DELAY)
    info = get_photo_info(flickr, photo_id)

    # Best available size — flickr.photos.getSizes
    time.sleep(RATE_DELAY)
    src_url, size_label = get_best_size_url(flickr, photo_id)

    if not src_url:
        print(f"  [error] No downloadable URL for {photo_id} — {title}")
        return

    try:
        download_image(src_url, img_path)
    except Exception as e:
        print(f"  [error] Download failed for {photo_id} ({title}): {e}")
        return

    # ── Dates ──────────────────────────────────────────────────────────────

    date_created             = None
    date_created_granularity = None
    date_created_note        = None
    date_posted              = None
    year                     = None

    if info:
        dates           = info.get('dates', {})
        raw_taken       = dates.get('taken')        # "2004-11-19 12:51:19" local time
        raw_posted      = dates.get('posted')       # Unix timestamp string (UTC)
        granularity_raw = dates.get('takengranularity')

        if raw_taken:
            date_created             = raw_taken[:10]  # "yyyy-mm-dd"
            year                     = raw_taken[:4]
            date_created_granularity = int(granularity_raw) if granularity_raw is not None else 0
            date_created_note        = DATE_GRANULARITY.get(date_created_granularity,
                                           f"Unknown granularity ({date_created_granularity})")

        if raw_posted:
            # posted is UTC Unix timestamp
            dt_posted   = datetime.datetime.fromtimestamp(int(raw_posted), datetime.UTC)
            date_posted = dt_posted.strftime('%Y-%m-%d')
            if not year:
                year = date_posted[:4]

    date_accessed = datetime.datetime.now(datetime.UTC).isoformat().replace('+00:00', 'Z')
    access_date   = format_access_date(date_accessed)

    # ── License ────────────────────────────────────────────────────────────

    license_id                = str(info.get('license', '0')) if info else '0'
    license_name, license_url = FLICKR_LICENSES.get(license_id, ("All Rights Reserved", None))

    # ── Creator ────────────────────────────────────────────────────────────

    owner_obj   = info.get('owner', {}) if info else {}
    creator     = (owner_obj.get('realname') or owner_obj.get('username')
                   or photo.get('ownername', photo.get('owner', '')))
    owner_nsid  = owner_obj.get('nsid') or photo.get('owner', '')
    creator_url = f"https://www.flickr.com/photos/{owner_nsid}/" if owner_nsid else None

    # ── Description (kept as raw HTML; labelled below) ─────────────────────

    description = photo.get('description', '')
    if isinstance(description, dict):
        description = description.get('_content', '')
    if not description and info:
        description = info.get('description', {}).get('_content', '')

    # ── Tags → array ───────────────────────────────────────────────────────

    raw_tags = photo.get('tags', '')
    if not raw_tags and info:
        raw_tags = ' '.join(t.get('raw', '') for t in info.get('tags', {}).get('tag', []))
    tags = [t for t in raw_tags.split() if t] if isinstance(raw_tags, str) else raw_tags

    # ── Medium ─────────────────────────────────────────────────────────────

    medium = infer_medium(tags)

    # ── Location ───────────────────────────────────────────────────────────

    location = extract_location(info)

    # ── URLs ───────────────────────────────────────────────────────────────

    accessed_url = f"https://www.flickr.com/photos/{owner_nsid}/{photo_id}"

    # ── Copyright line ─────────────────────────────────────────────────────

    copyright_line = None
    if license_id == '0' and creator and year:
        copyright_line = f"© {year} {creator}"

    # ── Citations ──────────────────────────────────────────────────────────

    citation_markdown = build_citation(
        creator=creator,
        year=year or 'n.d.',
        title=title,
        medium=medium,
        institution=None,
        institution_location=None,
        accessed_url=accessed_url,
        access_date_str=access_date,
        license_name=license_name,
        license_url=license_url,
    )

    tasl = build_tasl(
        title=title,
        accessed_url=accessed_url,
        creator=creator,
        creator_url=creator_url,
        license_name=license_name,
        license_url=license_url,
    )

    # ── Assemble ───────────────────────────────────────────────────────────

    metadata = {
        # About the image
        "photo_id":                    photo_id,
        "title":                       title,
        "accessed_url":                accessed_url,
        "src_url":                     src_url,
        "size_label":                  size_label,
        "date_created":                date_created,
        "date_created_granularity":    date_created_granularity,
        "date_created_note":           date_created_note,
        "date_posted":                 date_posted,
        "date_accessed":               date_accessed,
        "medium":                      medium,

        # Extended data
        "description":                 description,
        "description_format":          "html",
        "tags":                        tags,
        "occurrences":                 entry['occurrences'],
        "location":                    location,

        # About the creator
        "creator":                     creator,
        "creator_profile_url":         creator_url,
        "institution":                 None,
        "institution_location":        None,
        "website":                     "Flickr",
        "website_url":                 "https://www.flickr.com",

        # Rights
        "license_id":                  license_id,
        "license_name":                license_name,
        "license_url":                 license_url,
        "copyright_line":              copyright_line,

        # Citations
        "citation_markdown":           citation_markdown,
        "tasl":                        tasl,
    }

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    manifest[photo_id] = {
        'date_accessed': date_accessed,
        'filename':      f"{base}.jpg",
        'size_label':    size_label,
    }

    print(f"  [done]  {title} ({size_label})")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Download Flickr favourites and gallery images with full citation metadata.'
    )
    parser.add_argument(
        '--reset', action='store_true',
        help='Clear the download manifest and re-download everything'
    )
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if args.reset and os.path.exists(MANIFEST):
        os.remove(MANIFEST)
        print("Manifest cleared. All images will be re-downloaded.\n")

    manifest = load_manifest()
    flickr   = get_flickr()

    user_info = flickr.test.login()
    user_id   = user_info['user']['id']
    username  = user_info['user']['username']['_content']
    print(f"Logged in as: {username} ({user_id})\n")

    index = build_index(flickr, user_id)

    already_done = sum(1 for pid in index if pid in manifest)
    to_download  = len(index) - already_done
    print(f"Photos in index:      {len(index)}")
    print(f"Already downloaded:   {already_done}")
    print(f"To download now:      {to_download}\n")

    for i, (photo_id, entry) in enumerate(index.items(), 1):
        print(f"[{i}/{len(index)}]", end=' ')
        process_photo(flickr, photo_id, entry, output_dir=OUTPUT_DIR, manifest=manifest)
        save_manifest(manifest)

    print(f"\nFinished. {len(manifest)} photos in manifest.")
    print(f"Files saved to: {os.path.abspath(OUTPUT_DIR)}")


if __name__ == '__main__':
    main()
