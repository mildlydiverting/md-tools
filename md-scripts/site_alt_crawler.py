#!/usr/bin/env python3
"""Crawl a website, download its images, and write one Markdown file per page
with the images linked and their alt text recorded.

Standard library only (Python 3.9+).

Usage:
    python3 site_alt_crawler.py https://example.com
    python3 site_alt_crawler.py https://example.com -o my-site --delay 2 --max-pages 50

Output:
    <out>/index.md          list of pages, with image and missing-alt counts
    <out>/pages/<slug>.md   one per page: title, source URL, each image + its alt text
    <out>/images/           every image downloaded (shared across pages)

Notes:
    - Stays on the same host (www. and non-www. are treated as the same site).
    - Obeys robots.txt and its Crawl-delay, and pauses between requests.
    - Distinguishes between a MISSING alt attribute and an EMPTY one (alt=""),
      because the second is a deliberate "decorative image" signal.
    - Re-running is safe: images already on disk are not downloaded again.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import deque
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

USER_AGENT = "site-alt-crawler/1.0 (personal archive script; polite)"
MAX_PAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_BYTES = 50 * 1024 * 1024

# Links with these extensions are not crawled as pages.
SKIP_EXTENSIONS = {
    ".pdf", ".zip", ".gz", ".tar", ".dmg", ".exe", ".mp3", ".mp4", ".mov",
    ".avi", ".wav", ".css", ".js", ".json", ".xml", ".rss", ".atom",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".avif", ".ico",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
}
IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".avif", ".bmp",
    ".ico", ".tif", ".tiff",
}
CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
    "image/webp": ".webp", "image/svg+xml": ".svg", "image/avif": ".avif",
    "image/bmp": ".bmp", "image/x-icon": ".ico", "image/vnd.microsoft.icon": ".ico",
    "image/tiff": ".tif",
}


# --------------------------------------------------------------------------
# HTML parsing
# --------------------------------------------------------------------------

class PageParser(HTMLParser):
    """Collects the title, <base href>, links and <img> elements of a page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.base: str | None = None
        self.title = ""
        self._in_title = False
        self.links: list[str] = []
        self.images: list[tuple[str, str | None]] = []  # (src, alt or None)

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v if v is not None else "") for k, v in attrs}
        if tag == "base" and a.get("href") and self.base is None:
            self.base = a["href"]
        elif tag == "title":
            self._in_title = True
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag == "img":
            src = best_image_source(a)
            if src:
                self.images.append((src, a.get("alt")))  # None if attribute absent

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def best_image_source(attrs: dict[str, str]) -> str | None:
    """Pick the largest srcset candidate if there is one, otherwise src / lazy-load src."""
    for key in ("srcset", "data-srcset"):
        srcset = attrs.get(key, "").strip()
        if srcset:
            best_url, best_score = None, -1.0
            for candidate in re.split(r",\s+", srcset):
                parts = candidate.split()
                if not parts:
                    continue
                url = parts[0].rstrip(",")
                score = 1.0
                if len(parts) > 1 and parts[1][:-1].replace(".", "", 1).isdigit():
                    score = float(parts[1][:-1])
                if score > best_score:
                    best_url, best_score = url, score
            if best_url:
                return best_url
    for key in ("src", "data-src", "data-lazy-src", "data-original"):
        if attrs.get(key, "").strip():
            return attrs[key].strip()
    return None


# --------------------------------------------------------------------------
# Networking
# --------------------------------------------------------------------------

def fetch(url: str, limit: int, timeout: int = 30):
    """Return (final_url, headers, body_bytes). Raises on HTTP/network errors."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read(limit + 1)
        if len(body) > limit:
            raise ValueError(f"larger than {limit // (1024 * 1024)} MB limit")
        return resp.geturl(), resp.headers, body


def decode_page(headers, body: bytes) -> str:
    charset = headers.get_content_charset()
    if not charset:
        m = re.search(rb'<meta[^>]+charset=["\']?\s*([\w-]+)', body[:4096], re.I)
        charset = m.group(1).decode("ascii", "ignore") if m else "utf-8"
    try:
        return body.decode(charset, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def load_robots(start_url: str) -> RobotFileParser:
    p = urlparse(start_url)
    robots_url = f"{p.scheme}://{p.netloc}/robots.txt"
    rp = RobotFileParser()
    try:
        _, headers, body = fetch(robots_url, limit=512 * 1024, timeout=15)
        rp.parse(decode_page(headers, body).splitlines())
    except Exception:
        rp.parse([])  # no usable robots.txt: allow everything
    return rp


# --------------------------------------------------------------------------
# URL / filename helpers
# --------------------------------------------------------------------------

def host_key(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def page_key(url: str) -> tuple[str, str, str]:
    p = urlparse(url)
    return (host_key(url), p.path.rstrip("/") or "/", p.query)


def slug_for(url: str, used: set[str]) -> str:
    p = urlparse(url)
    path = re.sub(r"\.html?$", "", unquote(p.path).strip("/"), flags=re.I)
    base = re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-") or "index"
    if p.query:
        base += "-" + hashlib.sha1(p.query.encode()).hexdigest()[:6]
    base = base[:100]
    slug, n = base, 2
    while slug in used:
        slug, n = f"{base}-{n}", n + 1
    used.add(slug)
    return slug


def image_filename(url: str, content_type: str) -> str:
    digest = hashlib.sha1(url.encode()).hexdigest()[:8]
    name = Path(unquote(urlparse(url).path)).name
    stem, ext = Path(name).stem, Path(name).suffix.lower()
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-")[:60] or "image"
    if ext not in IMAGE_EXTENSIONS:
        ext = CONTENT_TYPE_EXTENSIONS.get(content_type, ".img")
    return f"{digest}-{stem}{ext}"


def is_crawlable(url: str, start_host: str) -> bool:
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        return False
    if host_key(url) != start_host:
        return False
    return Path(p.path).suffix.lower() not in SKIP_EXTENSIONS


# --------------------------------------------------------------------------
# Markdown output
# --------------------------------------------------------------------------

def clean_alt(alt: str) -> str:
    return re.sub(r"\s+", " ", alt).strip()


def md_alt(alt: str) -> str:
    return clean_alt(alt).replace("[", "\\[").replace("]", "\\]")


def alt_status(alt: str | None) -> str:
    if alt is None:
        return "*Missing alt attribute*"
    if not clean_alt(alt):
        return "*Empty alt (marked decorative)*"
    return clean_alt(alt)


def write_page_markdown(path: Path, url: str, title: str, images: list[dict]) -> None:
    lines = [
        "---",
        f"url: {json.dumps(url)}",
        f"title: {json.dumps(title)}",
        f"crawled: {date.today().isoformat()}",
        f"images: {len(images)}",
        "---",
        "",
        f"# {title or url}",
        "",
        f"Source: <{url}>",
        "",
    ]
    if not images:
        lines += ["*No images found on this page.*", ""]
    for i, img in enumerate(images, 1):
        lines += [f"## Image {i}", ""]
        if img["file"]:
            lines += [f"![{md_alt(img['alt'] or '')}](../images/{img['file']})", ""]
        else:
            lines += [f"*Not downloaded: {img['note']}*", ""]
        lines += [
            f"- **Alt text:** {alt_status(img['alt'])}",
            f"- **Image URL:** {img['url'] if not img['url'].startswith('data:') else '(inline data URI)'}",
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_index(out: Path, start_url: str, pages: list[dict]) -> None:
    total_images = sum(p["images"] for p in pages)
    total_missing = sum(p["missing"] for p in pages)
    lines = [
        f"# Alt text crawl: {urlparse(start_url).netloc}",
        "",
        f"- Start URL: <{start_url}>",
        f"- Crawled: {date.today().isoformat()}",
        f"- Pages: {len(pages)}",
        f"- Images found: {total_images}",
        f"- Images with a missing alt attribute: {total_missing}",
        "",
        "| Page | Images | Missing alt |",
        "| --- | ---: | ---: |",
    ]
    for p in pages:
        label = (p["title"] or p["url"]).replace("|", "\\|")
        lines.append(f"| [{label}](pages/{p['slug']}.md) | {p['images']} | {p['missing']} |")
    lines.append("")
    (out / "index.md").write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------
# Crawl
# --------------------------------------------------------------------------

def download_image(url: str, images_dir: Path, cache: dict, delay: float) -> tuple[str | None, str]:
    """Return (filename or None, note). Results are cached by URL."""
    if url in cache:
        return cache[url]
    digest = hashlib.sha1(url.encode()).hexdigest()[:8]
    existing = next(images_dir.glob(f"{digest}-*"), None)
    if existing:
        cache[url] = (existing.name, "")
        return cache[url]
    try:
        time.sleep(delay)
        _, headers, body = fetch(url, limit=MAX_IMAGE_BYTES)
        ctype = headers.get_content_type()
        if not ctype.startswith("image/"):
            raise ValueError(f"not an image (got {ctype})")
        name = image_filename(url, ctype)
        (images_dir / name).write_bytes(body)
        cache[url] = (name, "")
    except Exception as exc:
        cache[url] = (None, str(exc))
    return cache[url]


def crawl(start_url: str, out: Path, delay: float, max_pages: int | None) -> None:
    pages_dir, images_dir = out / "pages", out / "images"
    pages_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    start_host = host_key(start_url)
    robots = load_robots(start_url)
    crawl_delay = robots.crawl_delay(USER_AGENT)
    if crawl_delay:
        delay = max(delay, float(crawl_delay))

    queue: deque[str] = deque([urldefrag(start_url)[0]])
    seen = {page_key(queue[0])}
    used_slugs: set[str] = set()
    image_cache: dict[str, tuple[str | None, str]] = {}
    done: list[dict] = []

    try:
        while queue and (max_pages is None or len(done) < max_pages):
            url = queue.popleft()
            if not robots.can_fetch(USER_AGENT, url):
                print(f"  skipped (robots.txt): {url}")
                continue

            print(f"[{len(done) + 1}] {url}")
            try:
                time.sleep(delay)
                final_url, headers, body = fetch(url, limit=MAX_PAGE_BYTES)
            except (urllib.error.URLError, ValueError, OSError) as exc:
                print(f"  failed: {exc}")
                continue
            if host_key(final_url) != start_host:
                print("  redirected off-site, skipped")
                continue
            if headers.get_content_type() not in ("text/html", "application/xhtml+xml"):
                continue

            parser = PageParser()
            parser.feed(decode_page(headers, body))
            base = urljoin(final_url, parser.base) if parser.base else final_url

            for href in parser.links:
                link = urldefrag(urljoin(base, href))[0]
                if is_crawlable(link, start_host) and page_key(link) not in seen:
                    seen.add(page_key(link))
                    queue.append(link)

            images, seen_images = [], set()
            for src, alt in parser.images:
                if src.startswith("data:"):
                    images.append({"url": src, "alt": alt, "file": None,
                                   "note": "inline data URI"})
                    continue
                img_url = urldefrag(urljoin(base, src))[0]
                if (img_url, alt) in seen_images:
                    continue
                seen_images.add((img_url, alt))
                if urlparse(img_url).scheme not in ("http", "https"):
                    continue
                file, note = download_image(img_url, images_dir, image_cache, min(delay, 0.3))
                images.append({"url": img_url, "alt": alt, "file": file, "note": note})
                if not file:
                    print(f"  image failed: {img_url} ({note})")

            title = re.sub(r"\s+", " ", parser.title).strip()
            slug = slug_for(final_url, used_slugs)
            write_page_markdown(pages_dir / f"{slug}.md", final_url, title, images)
            done.append({
                "url": final_url, "title": title, "slug": slug,
                "images": len(images),
                "missing": sum(1 for i in images if i["alt"] is None),
            })
    except KeyboardInterrupt:
        print("\nStopped early; writing index for what was crawled so far.")
    finally:
        write_index(out, start_url, done)

    print(f"\nDone: {len(done)} pages, {sum(p['images'] for p in done)} images -> {out}/")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Crawl a site; save images and one Markdown file of alt text per page.")
    ap.add_argument("url", help="Start URL, e.g. https://example.com")
    ap.add_argument("-o", "--out", help="Output folder (default: <host>-alt-text)")
    ap.add_argument("--delay", type=float, default=1.0,
                    help="Seconds to wait between page requests (default 1.0)")
    ap.add_argument("--max-pages", type=int, default=None,
                    help="Stop after this many pages (default: no limit)")
    args = ap.parse_args()

    url = args.url if "://" in args.url else "https://" + args.url
    out = Path(args.out) if args.out else Path(f"{urlparse(url).netloc}-alt-text")
    crawl(url, out, args.delay, args.max_pages)
    return 0


if __name__ == "__main__":
    sys.exit(main())
