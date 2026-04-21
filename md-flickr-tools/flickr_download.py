#!/usr/bin/env python3
"""
flickr_download.py
------------------
Downloads images from your Flickr favourites and galleries.
Saves each image alongside a JSON metadata file.

Usage:
    python flickr_download.py           # Normal run — skips already-downloaded images
    python flickr_download.py --reset   # Clears manifest and re-downloads everything

Requirements:
    pip install flickrapi requests

Setup:
    1. Get a Flickr API key at https://www.flickr.com/services/apps/create/
    2. Fill in API_KEY and API_SECRET below
    3. On first run, you'll be asked to authorise via a browser URL
"""

import os
import sys
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

# Rate limit: pause between API calls (seconds)
RATE_DELAY = 0.5

# Image size preference, largest first, capped at ~3K (3072px on longest side).
# Flickr getSizes labels: https://www.flickr.com/services/api/misc.urls.html
# If a size is not available (e.g. restricted), we fall through to the next.
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


# ─── AUTHENTICATION ───────────────────────────────────────────────────────────

def get_flickr():
    """Authenticate with Flickr via OAuth. Token is cached after first run."""
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
    """Load the record of previously downloaded photos."""
    if os.path.exists(MANIFEST):
        with open(MANIFEST) as f:
            return json.load(f)
    return {}

def save_manifest(manifest):
    with open(MANIFEST, 'w') as f:
        json.dump(manifest, f, indent=2)


# ─── FETCH FAVOURITES ────────────────────────────────────────────────────────

def get_favourites(flickr):
    """Fetch all photos the user has favourited, handling pagination."""
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
    """Fetch all galleries belonging to the user."""
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
    """Fetch all photos in a single gallery, handling pagination."""
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
    """
    Build a combined index of all unique photos across favourites and galleries.
    Each entry records where the photo appears (favourites and/or which galleries).
    """
    favs     = get_favourites(flickr)
    galleries = get_galleries(flickr, user_id)

    # index: photo_id -> { 'photo': {...}, 'occurrences': [...] }
    index = {}

    # Add favourites
    for pid, photo in favs.items():
        index[pid] = {
            'photo': photo,
            'occurrences': [{'type': 'favourite'}]
        }

    # Add gallery photos (may overlap with favourites)
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
                index[pid] = {
                    'photo': photo,
                    'occurrences': [occurrence]
                }
        time.sleep(RATE_DELAY)

    print(f"\nTotal unique photos to download: {len(index)}\n")
    return index


# ─── IMAGE SIZE SELECTION ─────────────────────────────────────────────────────

def get_best_size_url(flickr, photo_id):
    """
    Fetch available sizes for a photo and return the URL for the
    largest size that fits within the SIZE_PREFERENCE cap.
    Falls back through the list if a larger size is unavailable
    (e.g. due to owner restrictions).
    """
    try:
        resp = flickr.photos.getSizes(photo_id=photo_id)
        available = {s['label']: s['source'] for s in resp['sizes']['size']}

        for label in SIZE_PREFERENCE:
            if label in available:
                return available[label], label

        # Last resort: use anything except Original
        for s in resp['sizes']['size']:
            if s['label'].lower() != 'original':
                return s['source'], s['label']

    except Exception as e:
        print(f"    Could not retrieve sizes for {photo_id}: {e}")

    return None, None


# ─── DOWNLOAD ────────────────────────────────────────────────────────────────

def download_image(url, filepath):
    r = requests.get(url, stream=True, timeout=30)
    r.raise_for_status()
    with open(filepath, 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

def safe_filename(s, max_len=60):
    """Strip problematic characters and truncate for use in filenames."""
    return "".join(c if c.isalnum() or c in ' _-' else '_' for c in s)[:max_len].strip()

def process_photo(flickr, photo_id, entry, output_dir, manifest):
    photo = entry['photo']
    title = photo.get('title', '') or photo_id
    base  = f"{photo_id}_{safe_filename(title)}"
    img_path  = os.path.join(output_dir, f"{base}.jpg")
    json_path = os.path.join(output_dir, f"{base}.json")

    # Skip if already in manifest
    if photo_id in manifest:
        print(f"  [skip]  {title}")
        return

    # Get best available size URL
    time.sleep(RATE_DELAY)
    url, size_label = get_best_size_url(flickr, photo_id)

    if not url:
        print(f"  [error] No downloadable URL for {photo_id} — {title}")
        return

    # Download image
    try:
        download_image(url, img_path)
    except Exception as e:
        print(f"  [error] Download failed for {photo_id} ({title}): {e}")
        return

    # Build and save metadata JSON
    downloaded_at = datetime.datetime.utcnow().isoformat() + 'Z'

    description = photo.get('description', '')
    if isinstance(description, dict):
        description = description.get('_content', '')

    metadata = {
        'photo_id':       photo_id,
        'title':          photo.get('title', ''),
        'owner':          photo.get('ownername', photo.get('owner', '')),
        'description':    description,
        'tags':           photo.get('tags', ''),
        'occurrences':    entry['occurrences'],
        'downloaded_url': url,
        'size_label':     size_label,
        'downloaded_at':  downloaded_at,
        'flickr_url':     f"https://www.flickr.com/photos/{photo.get('owner', '')}/{photo_id}",
    }

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    manifest[photo_id] = {
        'downloaded_at': downloaded_at,
        'filename':      f"{base}.jpg",
        'size_label':    size_label,
    }

    print(f"  [done]  {title} ({size_label})")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Download Flickr favourites and gallery images.'
    )
    parser.add_argument(
        '--reset', action='store_true',
        help='Clear the download manifest and re-download everything from scratch'
    )
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if args.reset and os.path.exists(MANIFEST):
        os.remove(MANIFEST)
        print("Manifest cleared. All images will be re-downloaded.\n")

    manifest = load_manifest()
    flickr   = get_flickr()

    # Confirm authenticated user
    user_info = flickr.test.login()
    user_id   = user_info['user']['id']
    username  = user_info['user']['username']['_content']
    print(f"Logged in as: {username} ({user_id})\n")

    # Build combined index across favourites + galleries
    index = build_index(flickr, user_id)

    already_done = sum(1 for pid in index if pid in manifest)
    to_download  = len(index) - already_done
    print(f"Photos in index:      {len(index)}")
    print(f"Already downloaded:   {already_done}")
    print(f"To download now:      {to_download}\n")

    for i, (photo_id, entry) in enumerate(index.items(), 1):
        print(f"[{i}/{len(index)}]", end=' ')
        process_photo(flickr, photo_id, entry, OUTPUT_DIR, manifest)
        save_manifest(manifest)  # save after each photo so partial runs are safe

    print(f"\nFinished. {len(manifest)} photos in manifest.")
    print(f"Files saved to: {os.path.abspath(OUTPUT_DIR)}")


if __name__ == '__main__':
    main()
