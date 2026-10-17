#!/usr/bin/env python3
"""
palette_report.py — read a named-colour markdown file, audit it, sort it, group it.

Input format (definition-list style, as exported from a palette tool):

    Group Heading

    colour-name
    : #AABBCC

Depends on palette_sort.py sitting alongside it. Separate script on purpose:
parsing and auditing are a different job from sorting and rendering.
"""

import argparse
import math
from collections import defaultdict
from pathlib import Path

import palette_sort as ps


def parse(path):
    """Returns list of Swatch, each carrying .name and .group."""
    swatches, group, pending = [], "(ungrouped)", None
    for raw in Path(path).read_text().splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(':'):
            hexv = line.lstrip(':').strip()
            swatches.append(ps.Swatch(hexv, name=pending, group=group))
            pending = None
        else:
            # a bare line following a bare line is a group heading
            if pending is not None:
                group = pending
            pending = line
    return swatches


def delta(a, b):
    """Euclidean distance in Oklab. Not CIEDE2000, but the skill-standard
    fast approximation -- fine for 'are these the same colour' questions."""
    return ps.dist(a.lab, b.lab)


def audit(sw):
    """Name collisions, exact hex repeats, and perceptual near-duplicates."""
    by_name, by_hex = defaultdict(list), defaultdict(list)
    for s in sw:
        by_name[s.name].append(s)
        by_hex[s.hex].append(s)

    name_collisions = {
        n: v for n, v in by_name.items()
        if len(v) > 1 and len({s.hex for s in v}) > 1
    }
    exact_repeats = {h: v for h, v in by_hex.items() if len(v) > 1}

    # near-duplicates across different names
    uniq = list({s.hex: s for s in sw}.values())
    near = []
    for i in range(len(uniq)):
        for j in range(i + 1, len(uniq)):
            d = delta(uniq[i], uniq[j])
            if d < 0.02:
                near.append((d, uniq[i], uniq[j]))
    near.sort(key=lambda t: t[0])
    return name_collisions, exact_repeats, near


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("infile")
    ap.add_argument("--k", type=int, default=7)
    ap.add_argument("--out", default="palette.png")
    ap.add_argument("--dedupe", action="store_true",
                    help="collapse exact hex repeats before sorting")
    args = ap.parse_args()

    sw = parse(args.infile)
    print(f"Parsed {len(sw)} entries across "
          f"{len({s.group for s in sw})} groups\n")

    collisions, repeats, near = audit(sw)

    print("## Name collisions (same name, different hex)")
    for n, v in sorted(collisions.items()):
        print(f"  {n}: " + ", ".join(f"{s.hex} [{s.group}]" for s in v))

    print(f"\n## Exact hex repeats ({len(repeats)})")
    for h, v in sorted(repeats.items()):
        names = ", ".join(sorted({f"{s.name} [{s.group}]" for s in v}))
        print(f"  {h} x{len(v)}: {names}")

    print(f"\n## Near-duplicates, Oklab dE < 0.02 ({len(near)})")
    for d, a, b in near:
        print(f"  dE {d:.4f}  {a.hex} {a.name:<18} / {b.hex} {b.name}")

    if args.dedupe:
        seen, work = set(), []
        for s in sw:  # keep FIRST occurrence so source group stays faithful
            if s.hex not in seen:
                seen.add(s.hex); work.append(s)
    else:
        work = sw
    print(f"\nSorting {len(work)} swatches"
          f"{' (deduped)' if args.dedupe else ''}")

    sections = [
        ("Ordered by lightness (OKLCh L)",
         [("darkest to lightest", ps.order_lightness(work))]),
        ("Ordered by hue (OKLCh H, neutrals first)",
         [("neutrals, then hue angle", ps.order_hue(work))]),
        ("Grouped by hue family", ps.group_family(work)),
        ("Grouped by character", ps.group_character(work)),
        (f"Grouped by k-means in Oklab (k={args.k})",
         ps.group_kmeans(work, k=args.k)),
        ("As supplied, by source group",
         [(g, sorted([s for s in work if s.group == g], key=lambda s: s.L))
          for g in dict.fromkeys(s.group for s in work)]),
    ]

    ps.render(sections, args.out)

    for title, blocks in sections:
        print(f"\n## {title}")
        for label, rows in blocks:
            print(f"  {label} ({len(rows)}): "
                  + " ".join(s.hex for s in rows))
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
