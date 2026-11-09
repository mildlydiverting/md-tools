#!/usr/bin/env python3
"""Turn saved `recent_chats` tool-result files into a compact JSON list.

Why: recent_chats output for a long project is large and arrives in two
shapes (a generated "Summary:" for older chats, a raw transcript for newer
Claude Code / Cowork sessions). This normalises both so you can read ~700
characters per chat instead of the whole payload.

Usage:
    parse_recent_chats.py PAGE1.json [PAGE2.json ...] [--chars 700] > chats-raw.json

Each PAGE is the persisted tool-result file (a JSON list of {"type":"text",
"text": "<chat url=... updated_at=...>...</chat>..."} objects). Pages are
merged, de-duplicated by chat id and sorted newest first.
Output: [{"id","url","updated_at","title","excerpt"}, ...]
"""
import argparse
import html
import json
import re
import sys


def parse_page(path, chars):
    data = json.load(open(path, encoding="utf-8"))
    text = "".join(x.get("text", "") for x in data)
    out = []
    for part in re.split(r"(?=<chat url=')", text):
        m = re.match(r"<chat url='([^']+)' updated_at='([^']+)'>", part)
        if not m:
            continue
        body = html.unescape(part[m.end():])
        body = re.sub(r"<system-reminder>.*?</system-reminder>", "", body, flags=re.S)
        body = re.sub(r"</?chat>", "", body)
        t = re.search(r"Title: ([^\n]*)", body)
        title = t.group(1).strip() if t else ""
        if "Summary:" in body[:400]:
            excerpt = body.split("Summary:", 1)[1]
        else:
            excerpt = body.split("Title:", 1)[-1].split("\n", 1)[-1]
        excerpt = re.sub(r"\*\*Conversation [Oo]verview:?\*\*", "", excerpt)
        excerpt = re.sub(r"\s+", " ", excerpt).strip()[:chars]
        out.append({
            "id": m.group(1).rsplit("/", 1)[-1],
            "url": m.group(1),
            "updated_at": m.group(2)[:19] + "+00:00" if m.group(2).endswith(("+00:00", "Z")) else m.group(2),
            "title": title,
            "excerpt": excerpt,
        })
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pages", nargs="+", help="saved recent_chats result files")
    ap.add_argument("--chars", type=int, default=700, help="excerpt length per chat")
    args = ap.parse_args()
    seen, chats = set(), []
    for p in args.pages:
        for c in parse_page(p, args.chars):
            if c["id"] not in seen:
                seen.add(c["id"])
                chats.append(c)
    chats.sort(key=lambda c: c["updated_at"], reverse=True)
    json.dump(chats, sys.stdout, indent=1, ensure_ascii=False)
    print(f"\n{len(chats)} chats", file=sys.stderr)


if __name__ == "__main__":
    main()
