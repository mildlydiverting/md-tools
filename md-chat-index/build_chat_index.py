#!/usr/bin/env python3
"""Build `<slug>-chat-index.csv` and `<slug>-summary.md` from one data file.

Usage:
    build_chat_index.py DATA.json --out-dir DIR [--carry-from OLD_SUMMARY.md]

DATA.json (see examples/md-pkim-and-tools.example.json):
{
  "project":   "project name, written into every CSV row",
  "slug":      "file-name prefix, e.g. md-pkim-and-tools",
  "generated": "ISO timestamp for the summary front matter",
  "intro":     "one italic line under the title (optional)",
  "chats": [  {"id","last_updated","title","summary"}, ... ],
  "sections": [
    {"heading": "arena-palette — ...",     # no leading number; added on output
     "body": "Description.\\n\\n### Sub-areas\\n- ...",
     "carry_from": 3,                      # optional: reuse description + sub-areas
                                           # of section 3 in --carry-from file
     "extra_body": "- extra sub-area",     # optional: appended after carried body
     "chat_ids": ["uuid", ...],
     "todos": ["...", "...", "..."]}
  ],
  "notes": ["ambiguity 1", ...]
}

Checks: every chat id appears in at least one section; every section has
three todos; chat ids are unique. Chat links are built from ids, so titles
and URLs in the summary can never drift from the CSV.
Standard library only.
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

URL = "https://claude.ai/chat/{}"


def load_carried(path):
    """Return {number: (heading, body)} from an earlier summary file."""
    text = Path(path).read_text(encoding="utf-8")
    out = {}
    for part in re.split(r"\n## (?=\d+\. )", text)[1:]:
        num = int(re.match(r"(\d+)\. ", part).group(1))
        head, rest = part.split("\n", 1)
        body = rest.split("### Chats")[0].rstrip().rstrip("-").rstrip()
        out[num] = (re.sub(r"^\d+\. ", "", head), body)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("data")
    ap.add_argument("--out-dir", required=True, help="where to write the two files")
    ap.add_argument("--carry-from", help="earlier summary .md to reuse sections from")
    args = ap.parse_args()

    d = json.load(open(args.data, encoding="utf-8"))
    chats = {c["id"]: c for c in d["chats"]}
    if len(chats) != len(d["chats"]):
        sys.exit("duplicate chat ids in data")
    carried = load_carried(args.carry_from) if args.carry_from else {}
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    slug = d["slug"]

    # CSV
    with open(out / f"{slug}-chat-index.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["title", "url", "summary", "last_updated", "project"])
        for c in d["chats"]:
            w.writerow([c["title"], URL.format(c["id"]), c["summary"], c["last_updated"], d["project"]])

    # Summary
    lines = ["---", f"timestamp: {d['generated']}", "---", f"# Project Summary: {d['project']}", ""]
    if d.get("intro"):
        lines += [d["intro"], ""]
    lines += ["---", ""]
    used = set()
    for n, s in enumerate(d["sections"], 1):
        heading, body = s["heading"], s.get("body", "")
        if "carry_from" in s:
            old_head, old_body = carried[s["carry_from"]]
            heading = s.get("heading") or old_head
            body = old_body + ("\n" + s["extra_body"] if s.get("extra_body") else "")
        if len(s["todos"]) != 3:
            sys.exit(f"section {n} ({heading}) needs exactly 3 todos")
        rows = sorted((chats[i] for i in s["chat_ids"]), key=lambda c: c["last_updated"], reverse=True)
        used.update(s["chat_ids"])
        lines += [f"## {n}. {heading}", "", body.strip(), "", "### Chats"]
        lines += [f"- [{c['title']}]({URL.format(c['id'])}) — {c['last_updated'][:10]}" for c in rows]
        lines += ["", "### Next todos"] + [f"{k}. {t}" for k, t in enumerate(s["todos"], 1)] + ["", "---", ""]
    missing = set(chats) - used
    if missing:
        sys.exit("chats not placed in any section: " + ", ".join(chats[i]["title"] for i in missing))
    if d.get("notes"):
        lines += ["## Notes on ambiguities", ""] + [f"- {n}" for n in d["notes"]] + [""]
    (out / f"{slug}-summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {slug}-chat-index.csv ({len(chats)} rows) and {slug}-summary.md ({len(d['sections'])} sections) to {out}")


if __name__ == "__main__":
    main()
