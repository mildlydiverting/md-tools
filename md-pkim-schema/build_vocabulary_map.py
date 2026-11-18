#!/usr/bin/env python3
"""Check pkim-vocabulary.yaml and rebuild the single-file visual map.

Usage:
    python3 build_vocabulary_map.py                 # default paths (below)
    python3 build_vocabulary_map.py --check         # check only, write nothing
    python3 build_vocabulary_map.py VOCAB.yaml OUT.html

Needs PyYAML (pip install pyyaml, inside a venv).
Version 1.0, 2026-11-16. See _development-notes/md-tools-pkim-notes/pkim-schema/.
"""
import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
NOTES = Path.home() / "Development" / "_development-notes" / "md-tools-pkim-notes" / "pkim-schema"
TEMPLATE = HERE / "vocabulary-map.template.html"
MARK = "/*VOCAB_JSON*/"
COUNTING = ("exact", "close")
RELATIONS = COUNTING + ("broader", "narrower", "related")


def check(d):
    """Return a list of problems. An empty list means the file is sound."""
    problems = []
    ids = [c["id"] for c in d["concepts"]]
    for i in sorted({i for i in ids if ids.count(i) > 1}):
        problems.append("duplicate concept id: " + i)
    idset = set(ids)
    kinds = {k["id"] for k in d["kinds"]}
    schemes = {s["id"] for s in d["schemes"]}
    sources = {s["id"] for s in d["tag_sources"]}
    alias_owner = {}
    for c in d["concepts"]:
        cid = c["id"]
        if cid != cid.lower() or not cid.isascii() or " " in cid:
            problems.append("id must be lower-case ASCII with no spaces: " + cid)
        if c.get("kind") not in kinds:
            problems.append(cid + ": unknown kind " + str(c.get("kind")))
        if c.get("status") not in ("active", "proposed", "deprecated"):
            problems.append(cid + ": unknown status " + str(c.get("status")))
        if c.get("status") == "deprecated" and c.get("replaced_by") not in idset:
            problems.append(cid + ": deprecated concepts need a valid replaced_by")
        for s in c.get("schemes", []):
            if s not in schemes:
                problems.append(cid + ": unknown scheme " + s)
        for key in ("broader", "related"):
            for t in c.get(key, []):
                if t not in idset:
                    problems.append(cid + ": " + key + " points at missing concept " + t)
                if t == cid:
                    problems.append(cid + ": " + key + " points at itself")
        for a in c.get("aliases", []):
            al = str(a).lower()
            if al in idset and al != cid:
                problems.append(cid + ": alias " + al + " is another concept's id")
            if alias_owner.get(al, cid) != cid:
                problems.append(cid + ": alias " + al + " is also claimed by " + alias_owner[al])
            alias_owner[al] = cid
    for m in d.get("mappings", []):
        where = "mapping " + m["source"] + "/" + m["tag"]
        if m["source"] not in sources:
            problems.append(where + ": unknown tag source")
        if m["relation"] not in RELATIONS:
            problems.append(where + ": unknown relation " + m["relation"])
        if ":" not in m["to"] and m["to"] not in idset:
            problems.append(where + ": target is not a concept: " + m["to"])
    return problems


def main(argv):
    only_check = "--check" in argv
    paths = [a for a in argv if not a.startswith("--")]
    vocab = Path(paths[0]) if paths else NOTES / "pkim-vocabulary.yaml"
    out = Path(paths[1]) if len(paths) > 1 else NOTES / "04-vocabulary-map.html"
    data = yaml.safe_load(vocab.read_text(encoding="utf-8"))
    problems = check(data)
    for p in problems:
        print("PROBLEM: " + p)
    print(str(len(data["concepts"])) + " concepts, " + str(len(data.get("mappings", []))) + " mappings, " + str(len(problems)) + " problems")
    if problems:
        return 1
    if only_check:
        return 0
    template = TEMPLATE.read_text(encoding="utf-8")
    if MARK not in template:
        print("PROBLEM: marker missing from template")
        return 1
    payload = json.dumps(data, ensure_ascii=False, default=str).replace("</", "<\\/")
    out.write_text(template.replace(MARK, payload), encoding="utf-8")
    print("wrote " + str(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
