#!/usr/bin/env python3
"""
wf_checkin.py: Three Things check-in, backed by Workflowy.

Standard library only. Runs and exits; no server.

Commands
  fetch                 Write checkin-data.js for the check-in page.
  show                  Print today's three things and any slips.
  add "text"            Add a todo to the Workflowy Inbox. Prints its id.
  add "text" --today    ...and mirror it onto today's Three things.
  mirror ID             Mirror an existing task onto today's Three things.
  complete ID           Mark a task done (mirrors complete their origin).
  unmirror ID           Remove a mirror (the original task is untouched).

Options
  --date YYYY-MM-DD     Act as if this were today (for testing or catch-up).
  --out PATH            Where fetch writes the data file.
  --dry-run             Print what would change; write nothing.

API key, first found wins:
  1. WORKFLOWY_API_KEY environment variable
  2. macOS Keychain item named "workflowy-api":
       security add-generic-password -a "$USER" -s workflowy-api -w
Get a key at https://workflowy.com/api-key

Model
  calendar > YYYY-MM-DD > "Three things" (h2) > mirrors of real tasks
  The original task lives in the Inbox or a project. A task's first date is
  the earliest day it was mirrored onto. Open + first date before today
  = slipping. Carry-over = mirror it onto today as well; old mirrors stay,
  so the history stays visible.

Changelog
  v1.0 (2026-11-21): First version.
"""

import argparse
import datetime as dt
import html
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

VERSION = "1.0"
BASE = "https://workflowy.com/api/v1"
HEADING = "Three things"      # name of the h2 under each day node
WINDOW_DAYS = 14              # how far back to look for slips
HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "checkin-data.js"


# ---- API ---------------------------------------------------------------

class NotFound(Exception):
    pass


class Api:
    def __init__(self, key, dry_run=False):
        self.key = key
        self.dry_run = dry_run

    def request(self, method, path, body=None, query=None):
        url = BASE + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", "Bearer " + self.key)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise NotFound(path)
            if e.code == 401:
                sys.exit("Workflowy said the API key is not valid (401).")
            if e.code == 429:
                sys.exit("Workflowy rate limit hit. nodes-export allows one "
                         "call a minute. Try again shortly.")
            sys.exit(f"Workflowy error {e.code} on {method} {path}: "
                     f"{e.read().decode(errors='replace')[:300]}")
        except urllib.error.URLError as e:
            sys.exit(f"Couldn't reach Workflowy: {e.reason}")

    def get(self, path, query=None):
        return self.request("GET", path, query=query)

    def post(self, path, body):
        if self.dry_run:
            print(f"[dry run] POST {path} {json.dumps(body)}")
            return {"item_id": "DRY-RUN", "status": "ok"}
        return self.request("POST", path, body=body)

    def delete(self, path):
        if self.dry_run:
            print(f"[dry run] DELETE {path}")
            return {"status": "ok"}
        return self.request("DELETE", path)



def get_key():
    key = os.environ.get("WORKFLOWY_API_KEY", "").strip()
    if key:
        return key
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", "workflowy-api", "-w"],
            capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        sys.exit("No API key. Set WORKFLOWY_API_KEY or add a Keychain item "
                 "called workflowy-api (see the top of this file).")


# ---- Helpers -----------------------------------------------------------

def plain(name):
    """Workflowy names carry inline HTML. Strip it for display."""
    return html.unescape(re.sub(r"<[^>]+>", "", name or "")).strip()


def day_key(d):
    return d.isoformat()


def find_heading(api, day):
    """Return the id of the day's Three things node, or None."""
    try:
        kids = api.get("/nodes", {"parent_id": day_key(day)})["nodes"]
    except NotFound:
        return None
    for n in kids:
        if plain(n.get("name")) == HEADING:
            return n["id"]
    return None


def ensure_heading(api, day):
    """Find or create the day's Three things node. Creating it also
    creates the calendar day, which the API only does on create."""
    hid = find_heading(api, day)
    if hid:
        return hid
    r = api.post("/nodes", {"parent_id": day_key(day), "name": HEADING,
                            "layoutMode": "h2", "position": "top"})
    return r["item_id"]


def collect(api, today, window=WINDOW_DAYS):
    """Read the last `window` days of Three things.

    Calendar day nodes are found by date key, one call each (a missing day
    is a 404, which is fine). Then one nodes-export call gives every node,
    so we can read each origin's completed state and name."""
    days = {}
    for i in range(window, -1, -1):
        d = today - dt.timedelta(days=i)
        hid = find_heading(api, d)
        if hid:
            days[d] = hid
    nodes = {n["id"]: n for n in api.get("/nodes-export")["nodes"]}

    children = {}
    for n in nodes.values():
        children.setdefault(n.get("parent_id"), []).append(n)
    for kids in children.values():
        kids.sort(key=lambda n: n.get("priority", 0))

    tasks = {}   # origin id -> record
    for d in sorted(days):
        for pos, child in enumerate(children.get(days[d], [])):
            mirror = (child.get("data") or {}).get("mirror") or {}
            origin_id = mirror.get("origin_id") or child["id"]
            origin = nodes.get(origin_id, child)
            rec = tasks.setdefault(origin_id, {
                "id": origin_id,
                "text": plain(origin.get("name")),
                "done": bool(origin.get("completed")),
                "completed_at": origin.get("completedAt"),
                "first_date": day_key(d),
                "dates": [],
                "mirror_ids": {},
            })
            rec["dates"].append(day_key(d))
            rec["mirror_ids"][day_key(d)] = child["id"]
            if d == today:
                rec["today_pos"] = pos

    t = day_key(today)
    for rec in tasks.values():
        first = dt.date.fromisoformat(rec["first_date"])
        rec["days_on"] = (today - first).days
        rec["on_today"] = t in rec["dates"]
        rec["slipping"] = (not rec["done"]) and rec["days_on"] > 0

    today_items = [r for r in tasks.values() if r["on_today"]]
    today_items.sort(key=lambda r: r["today_pos"])
    slipping = sorted((r for r in tasks.values() if r["slipping"]),
                      key=lambda r: -r["days_on"])
    inbox = [n for n in children.get(_inbox_id(api), [])
             if not n.get("completed")]
    return {
        "version": VERSION,
        "generated": dt.datetime.now().astimezone().isoformat(timespec="minutes"),
        "today": t,
        "today_items": today_items,
        "slipping": slipping,
        "inbox_open": len(inbox),
    }


def _inbox_id(api):
    try:
        return api.get("/nodes/inbox")["node"]["id"]
    except NotFound:
        return None


# ---- Commands ----------------------------------------------------------

def cmd_fetch(api, today, out):
    data = collect(api, today)
    js = ("// Written by wf_checkin.py. Do not edit by hand.\n"
          "window.CHECKIN_DATA = " + json.dumps(data, indent=2) + ";\n")
    if api.dry_run:
        print(js)
        return
    tmp = Path(str(out) + ".tmp")
    tmp.write_text(js, encoding="utf-8")
    tmp.replace(out)          # atomic, so the page never reads half a file
    print(f"Wrote {out}")


def cmd_show(api, today):
    data = collect(api, today)
    print(f"Three things for {data['today']}:")
    if not data["today_items"]:
        print("  (none yet)")
    for r in data["today_items"]:
        tick = "x" if r["done"] else " "
        extra = f"  (day {r['days_on'] + 1})" if r["days_on"] else ""
        print(f"  [{tick}] {r['text']}{extra}   id:{r['id']}")
    off = [r for r in data["slipping"] if not r["on_today"]]
    if off:
        print("\nOpen from earlier days, not on today:")
        for r in off:
            print(f"  - {r['text']}  (first {r['first_date']}, "
                  f"{r['days_on']} days)   id:{r['id']}")
    print(f"\nInbox: {data['inbox_open']} open")


def cmd_add(api, today, text, also_today):
    r = api.post("/nodes", {"parent_id": "inbox", "name": text,
                            "layoutMode": "todo", "position": "bottom"})
    print(f"Added to Inbox   id:{r['item_id']}")
    if also_today:
        cmd_mirror(api, today, r["item_id"])


def cmd_mirror(api, today, node_id):
    hid = ensure_heading(api, today)
    r = api.post(f"/nodes/{node_id}/mirror",
                 {"parent_id": hid, "position": "bottom"})
    print(f"Mirrored onto {day_key(today)}   mirror id:{r['item_id']}")


def cmd_complete(api, node_id):
    api.post(f"/nodes/{node_id}/complete", {})
    print("Marked done.")


def cmd_unmirror(api, node_id):
    api.delete(f"/nodes/{node_id}/mirror")
    print("Mirror removed. The original task is untouched.")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("command",
                   choices=["fetch", "show", "add", "mirror", "complete",
                            "unmirror"])
    p.add_argument("arg", nargs="?")
    p.add_argument("--today", action="store_true",
                   help="with add: also mirror onto today")
    p.add_argument("--date", help="act as if today were YYYY-MM-DD")
    p.add_argument("--out", default=str(DEFAULT_OUT))
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)

    today = dt.date.fromisoformat(a.date) if a.date else dt.date.today()
    api = Api(get_key(), dry_run=a.dry_run)

    if a.command in ("add", "mirror", "complete", "unmirror") and not a.arg:
        p.error(f"{a.command} needs a value")
    if a.command == "fetch":
        cmd_fetch(api, today, Path(a.out))
    elif a.command == "show":
        cmd_show(api, today)
    elif a.command == "add":
        cmd_add(api, today, a.arg, a.today)
    elif a.command == "mirror":
        cmd_mirror(api, today, a.arg)
    elif a.command == "complete":
        cmd_complete(api, a.arg)
    elif a.command == "unmirror":
        cmd_unmirror(api, a.arg)


if __name__ == "__main__":
    main()
