#!/usr/bin/env python3
"""
fix_pinterest_frontmatter.py — v0.1
Normalise Pinterest-export notes in obsidian-general-to-import/ to the
canonical metadata-mapping.md schema.

Detects two export shapes seen in the vault:
  - "rich":  has a `tags:` list in frontmatter + a downloaded local image
  - "crude": no tags, remote pinimg.com URLs only, empty title

Does NOT rename or delete files, and does NOT apply the @/col:/class: tag
ontology (that's a judgement call — see --apply-ontology flag, off by default).
Writes new frontmatter + prints a report. Dry-run unless --apply is passed.

Usage:
    python3 fix_pinterest_frontmatter.py /path/to/vault/obsidian-general-to-import          # dry run, prints report
    python3 fix_pinterest_frontmatter.py /path/to/vault/obsidian-general-to-import --apply   # writes changes
"""

import argparse
import re
import sys
from pathlib import Path
from collections import defaultdict

try:
    import yaml
except ImportError:
    sys.exit("Missing dependency. Run: pip install pyyaml --break-system-packages")

FM_RE = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.DOTALL)


class Post:
    """Minimal frontmatter reader/writer, parsed with PyYAML (avoids the
    python-frontmatter dependency, which isn't always installed)."""

    def __init__(self, metadata, content):
        self.metadata = metadata
        self.content = content

    def get(self, key, default=None):
        return self.metadata.get(key, default)

    @classmethod
    def load(cls, path):
        raw = path.read_text(encoding="utf-8")
        m = FM_RE.match(raw)
        if not m:
            return cls({}, raw)
        fm_text, body = m.groups()
        metadata = yaml.safe_load(fm_text) or {}
        return cls(metadata, body)

    def dump(self):
        fm_text = yaml.safe_dump(self.metadata, sort_keys=False, allow_unicode=True).strip()
        return f"---\n{fm_text}\n---\n{self.content}"


class frontmatter:  # shim so the rest of the script reads the same as with python-frontmatter
    @staticmethod
    def load(path):
        return Post.load(path)

    @staticmethod
    def dump(post, f):
        f.write(post.dump().encode("utf-8"))


PIN_ID_RE = re.compile(r"pinterest\.com/pin/(\d+)")
IMG_RE = re.compile(r"https://i\.pinimg\.com/\S+\.(?:jpg|jpeg|png|webp)")
WIKILINK_IMG_RE = re.compile(r"!\[\[([^\]]+)\]\]")


def extract_pin_id(post):
    link = post.get("pinterest-link", "") or ""
    m = PIN_ID_RE.search(link)
    return m.group(1) if m else None


def extract_title(post):
    """Priority: non-empty H1 > gridTitle line in body > None."""
    body = post.content
    h1 = re.search(r"^#[ \t]+(\S.*)$", body, re.MULTILINE)
    if h1 and h1.group(1).strip():
        return h1.group(1).strip()
    grid = re.search(r"gridTitle:\s*(.+)", body)
    if grid and grid.group(1).strip():
        return grid.group(1).strip()
    return None


def extract_image_url(post):
    """Prefer a local wikilink attachment; fall back to the largest remote pinimg URL."""
    body = post.content
    wikilink = WIKILINK_IMG_RE.search(body)
    if wikilink:
        return wikilink.group(1), "local"
    remote = IMG_RE.findall(body)
    if remote:
        # prefer "originals" or the largest dimension tag if present
        remote.sort(key=lambda u: ("original" not in u, u), reverse=False)
        return remote[0], "remote"
    return None, None


def extract_description(post):
    body = post.content
    desc = re.search(r"^description:\s*(.+)$", body, re.MULTILINE)
    return desc.group(1).strip() if desc and desc.group(1).strip() else None


def extract_date_str(post):
    created = post.get("created")
    if not created:
        return None
    # created may already be a datetime (PyYAML parses ISO strings) or a string
    s = str(created)
    return s[:10] if s else None  # YYYY-MM-DD


def build_canonical_frontmatter(post, path):
    pin_id = extract_pin_id(post)
    board = post.get("pinterest-board")
    date_str = extract_date_str(post)
    fallback_bits = [b for b in [pin_id, board, date_str] if b]
    fallback_title = "Pinterest pin " + " ".join(fallback_bits) if fallback_bits else "Pinterest pin (untitled)"
    title = extract_title(post) or fallback_title
    source_url = post.get("source") or None
    image_url, image_source = extract_image_url(post)
    description = extract_description(post)
    tags = post.get("tags") or []  # unnormalised, pass through as-is

    new_fm = {
        "title": title,
        "creator": None,  # ⚠️ not available from Pinterest export
        "source_url": source_url,
        "image_url": image_url,
        "image_source": image_source,  # "local" | "remote" | None — flags which still need downloading
        "description": description,
        "website": "Pinterest",
        "website_url": "https://www.pinterest.com",
        "photo_id": pin_id,
        "date_posted": post.get("created"),
        "gallery": {
            "gallery_id": None,
            "title": board,
            "gallery_url": f"https://www.pinterest.com/mildlydiverting/{board.lower().replace(' ', '-')}/" if board else None,
        },
        "tags": tags,
        "tags_normalised": [],  # left empty — ontology pass is separate, see --apply-ontology
        "eagle_imported": False,
        "arena_block_id": None,
    }
    return new_fm


def process_file(path, apply_ontology=False):
    post = frontmatter.load(path)
    shape = "rich" if post.get("tags") else "crude"
    new_fm = build_canonical_frontmatter(post, path)
    needs_image_download = new_fm["image_source"] == "remote"
    return post, new_fm, shape, needs_image_download


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vault_path", type=Path, help="Path to obsidian-general-to-import/ folder")
    ap.add_argument("--apply", action="store_true", help="Write changes (default: dry run)")
    ap.add_argument("--limit", type=int, default=None, help="Only process first N files (for testing)")
    args = ap.parse_args()

    md_files = sorted(args.vault_path.glob("*.md"))
    if args.limit:
        md_files = md_files[: args.limit]

    pin_id_to_files = defaultdict(list)
    report_rows = []
    needs_download = []

    for path in md_files:
        try:
            post, new_fm, shape, needs_img = process_file(path)
        except Exception as e:
            print(f"SKIP (error): {path.name} — {e}")
            continue

        if new_fm["photo_id"]:
            pin_id_to_files[new_fm["photo_id"]].append(path.name)

        report_rows.append((path.name, shape, new_fm["title"], new_fm["photo_id"], new_fm["image_source"]))

        if needs_img:
            needs_download.append((path.name, new_fm["image_url"]))

        if args.apply:
            post.metadata = new_fm
            with open(path, "wb") as f:
                frontmatter.dump(post, f)

    # --- report ---
    print(f"\n{'APPLIED' if args.apply else 'DRY RUN'} — {len(report_rows)} files processed\n")
    print(f"{'file':50} {'shape':6} {'title':40} {'pin_id':>18} image")
    print("-" * 130)
    for name, shape, title, pin_id, img_src in report_rows:
        print(f"{name[:50]:50} {shape:6} {title[:40]:40} {str(pin_id):>18} {img_src}")

    dupes = {pid: files for pid, files in pin_id_to_files.items() if len(files) > 1}
    if dupes:
        print(f"\n⚠ {len(dupes)} duplicate pin(s) found under multiple filenames (not merged — review manually):")
        for pid, files in dupes.items():
            print(f"  pin {pid}: {', '.join(files)}")

    if needs_download:
        print(f"\n⚠ {len(needs_download)} file(s) still point at remote pinimg.com URLs — image not archived locally:")
        for name, url in needs_download[:10]:
            print(f"  {name} → {url}")
        if len(needs_download) > 10:
            print(f"  ...and {len(needs_download) - 10} more")

    if not args.apply:
        print("\nThis was a dry run — no files were changed. Re-run with --apply to write.")


if __name__ == "__main__":
    main()
