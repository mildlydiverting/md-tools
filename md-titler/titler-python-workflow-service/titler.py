#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
titler.py - turn URLs in text into Markdown links with page titles.

A Python 3 (standard library only) rewrite of Brett Terpstra's 2015 titler.rb,
without the affiliate-link features. Reads text on STDIN, writes text on STDOUT.

Arguments (on the command line, or on a first line of the input starting "::"):
  l | links   output only a Markdown list of the links found
  c | clipboard  copy result to the clipboard (pbcopy) and print a count
  d | debug   print progress and errors to STDERR
  <number>    truncate titles to that many characters

  cat notes.md | titler.py
  cat notes.md | titler.py links 40
"""
import html
import re
import subprocess
import sys
import shutil
from urllib.parse import urlparse

CURL = "/usr/bin/curl" if shutil.which("/usr/bin/curl") else (shutil.which("curl") or "curl")
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
              "(KHTML, like Gecko) Version/17.0 Safari/605.1.15")
MAX_BYTES = 1024 * 1024

DEBUG = False


def log(*a):
    if DEBUG:
        print(*a, file=sys.stderr)


# --------------------------------------------------------------------------
# Fetching and extracting titles
# --------------------------------------------------------------------------

def fetch_html(url):
    """Fetch a page with curl (system certs, redirects, compression). Returns bytes."""
    cmd = [CURL, "-sSL", "--compressed", "-m", "20", "--max-filesize", str(8 * MAX_BYTES),
           "-A", USER_AGENT, "-H", "Accept-Language: en-GB,en;q=0.9", url]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0 and not res.stdout:
        raise RuntimeError(res.stderr.decode("utf-8", "replace").strip() or
                           "curl exited %d" % res.returncode)
    return res.stdout[:MAX_BYTES]


def decode_body(raw):
    """Decode page bytes using a declared charset where there is one."""
    head = raw[:4096].decode("ascii", "ignore")
    m = (re.search(r'<meta[^>]+charset\s*=\s*["\']?\s*([\w\-]+)', head, re.I) or
         re.search(r'charset\s*=\s*([\w\-]+)', head, re.I))
    for enc in ([m.group(1)] if m else []) + ["utf-8"]:
        try:
            return raw.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("utf-8", "replace")


def extract_title(body):
    """Return the cleaned <title> text, or ''. Accepts attributes on the tag."""
    m = re.search(r"<title\b[^>]*>(.*?)</title\s*>", body, re.I | re.S)
    if not m:
        return ""
    t = m.group(1)
    t = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", t, flags=re.S)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)              # &amp; &#x27; &#8217; &eacute; &ndash; ...
    t = t.replace(" ", " ")
    return re.sub(r"\s+", " ", t).strip()


# --------------------------------------------------------------------------
# Title tidying
# --------------------------------------------------------------------------

SEPARATOR_RE = re.compile(r"(\s+[|«»\-–—·:]\s+)")


def squash(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def remove_seo(title, url):
    """Strip a site-name segment from the start or end: 'Home | Site' -> 'Home'.
    Only the ends are touched, so separators inside the real title survive."""
    try:
        parsed = urlparse(url)
        host = re.sub(r"^www\.", "", (parsed.hostname or "").lower())
        bits = [squash(p) for p in host.split(".")[:-1]]
        bits = [b for b in bits if len(b) >= 3]
        if not bits or parsed.path in ("", "/"):
            return title

        def is_site(part):
            sp = squash(part)
            return len(sp) >= 3 and any(b in sp or sp in b for b in bits)

        # split keeps separators: [part, sep, part, sep, part ...]
        pieces = SEPARATOR_RE.split(title)
        for _ in range(5):
            if len(pieces) < 3:
                break
            if is_site(pieces[-1]):
                pieces = pieces[:-2]
            elif is_site(pieces[0]):
                pieces = pieces[2:]
            else:
                break
        result = "".join(pieces).strip()
        return result if len(result) > 5 else title
    except Exception as e:  # never let tidying break a link
        log("Error tidying title:", e)
        return title


def truncate(title, limit):
    if len(title) <= limit:
        return title
    limit -= 3
    out = ""
    for w in title.split():
        if len(out) + len(w) + 1 > limit:
            break
        out += (" " if out else "") + w
    return (out or title.split()[0]) if title.split() else title


def close_punctuation(title):
    """If a title was cut inside a bracket or quote, close it."""
    pairs = {"“": "”", "‘": "’", "[": "]", "(": ")", "<": ">"}
    if not any(c in title for c in pairs):
        return title
    stack = []
    for ch in title:
        if ch in pairs:
            stack.append(ch)
        elif ch in pairs.values():
            for opener in reversed(stack):
                if pairs[opener] == ch:
                    stack.remove(opener)
                    break
    tail = "".join(pairs[c] for c in reversed(stack))
    if tail:
        title = re.sub(r"[^A-Za-z)\]’”.…]+$", "...", title).strip()
    return title + tail


def md_escape(title):
    return title.replace("[", "\\[").replace("]", "\\]")


# --------------------------------------------------------------------------
# Link handling
# --------------------------------------------------------------------------

LINK_RE = re.compile(
    r"((?:\[(.*?)\])?(?:\(|: +))?"                      # 1 head, 2 existing md text
    r"((?:https?://)(?:[\da-z.-]+)\.(?:[a-z.]{2,6})"    # 3 url
    r"(?:[/\w.\-()_+=?&%#:~@,;!*$']*?))"
    r'( ".*?")?(\))?([\s]|$)',                          # 4 title attr, 5 ")", 6 ws
    re.I | re.M | re.S)


def clean_url(u):
    u = re.sub(r"[?&]utm_.*", "", u.strip())
    return re.sub(r"(%EF|%BB|%BF)+$", "", u)


class Titler:
    def __init__(self, max_len=0, links_only=False, clean_seo=True):
        self.max_len = max_len
        self.links_only = links_only
        self.clean_seo = clean_seo
        self.cache = {}
        self.count = 0

    def title_for(self, url):
        if url in self.cache:
            return self.cache[url]
        title = ""
        try:
            title = extract_title(decode_body(fetch_html(url)))
        except Exception as e:
            log("Error retrieving title for %s: %s" % (url, e))
        if title and self.clean_seo:
            title = remove_seo(title, url)
        self.cache[url] = title
        return title

    def finish_title(self, title, url, fallback=""):
        if not title:
            log("Warning: missing title for", url)
            title = fallback or re.sub(r"^https?://|/.*$", "", url)
        full = None
        if self.max_len > 0 and len(title) > self.max_len:
            full = title
            title = truncate(title, self.max_len)
        return close_punctuation(title), full

    def replace_one(self, m):
        head, md_title, raw_url, alt, _close, ws = m.groups()
        head, md_title, alt = head or "", md_title or "", alt or ""
        tail_ws = ws or ""
        url = clean_url(raw_url)
        if not url.lower().startswith("http"):
            url = "http://" + url
        self.count += 1
        title, full = self.finish_title(self.title_for(url), url, md_title)
        if full and not alt:
            alt = ' "%s"' % full.replace('"', "'")
        if re.match(r"^\[.*?\]:", head):               # reference link: [id]: url
            return '%s%s "%s"%s' % (head, url, title.replace('"', "'"), tail_ws)
        return "[%s](%s%s)%s" % (md_escape(title), url, alt, tail_ws)

    def replace_links(self, text):
        def safe(m):
            try:
                return self.replace_one(m)
            except Exception as e:
                log("Error processing %r: %s" % (m.group(0), e))
                return m.group(0)
        return LINK_RE.sub(safe, text)

    def list_links(self, text):
        out, seen = [], set()
        for m in LINK_RE.finditer(text):
            url = clean_url(m.group(3))
            if url in seen:
                continue
            seen.add(url)
            self.count += 1
            title, full = self.finish_title(self.title_for(url), url, m.group(2) or "")
            alt = ' "%s"' % full.replace('"', "'") if full else ""
            out.append("- [%s](%s%s)" % (md_escape(title), url, alt))
        return "\n".join(out)


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def parse_args(argv, text):
    args = list(argv)
    first, nl, rest = text.partition("\n")
    m = re.match(r"^::(.*)$", first)
    if m:
        args += m.group(1).split()
        text = rest
    opts = {"links": False, "clipboard": False, "debug": False, "max": 0}
    for a in args:
        if re.match(r"^l(inks)?$", a, re.I):
            opts["links"] = True
        elif re.match(r"^c(lipboard)?$", a, re.I):
            opts["clipboard"] = True
        elif re.match(r"^d(ebug)?$", a, re.I):
            opts["debug"] = True
        elif re.match(r"^\d+$", a):
            opts["max"] = int(a)
        elif re.match(r"^-{0,2}h(elp)?$", a, re.I):
            print(__doc__)
            sys.exit(0)
        # 'a'/'aff' (affiliate) deliberately ignored in this version
    return opts, text


def main():
    global DEBUG
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    text = sys.stdin.buffer.read().decode("utf-8", "replace")
    opts, text = parse_args(sys.argv[1:], text)
    DEBUG = opts["debug"]
    if not text.strip():
        log("No input received on STDIN")
        return 0

    t = Titler(max_len=opts["max"], links_only=opts["links"])
    output = t.list_links(text) if opts["links"] else t.replace_links(text)
    log("%d links found" % t.count)

    if opts["clipboard"]:
        if t.count == 0:
            print("No links found")
        else:
            subprocess.run(["pbcopy"], input=output.encode("utf-8"))
            print("%d links updated" % t.count)
    else:
        sys.stdout.write(output + ("\n" if opts["links"] else ""))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
