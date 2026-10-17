#!/usr/bin/env python3
"""
palette_sort.py — arrange hex colours chromatically and group them into subsets.

Pure stdlib + Pillow. No colour library dependency: the sRGB -> OKLab -> OKLCh
chain is ~40 lines (Ottosson's coefficients), so there's nothing to install.

Orderings
  hue        hue angle, lightness as tiebreak; neutrals pulled out to the front
  lightness  OKLCh L ascending, hue as tiebreak
  path       greedy nearest-neighbour walk through Oklab (smoothest ribbon)

Groupings
  family     named hue bins (red/orange/yellow/green/cyan/blue/purple/pink + neutral)
  character  pale / muted / deep / vivid / dark / neutral, from L and C only
  kmeans     Lloyd's algorithm in Oklab, k-means++ init, fixed seed

Usage
  python3 palette_sort.py "#aabbcc,#ddeeff,..." --k 5 --out palette.png
  python3 palette_sort.py --file codes.txt --out palette.png
"""

import argparse
import math
import random
import re
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# Colour conversion: sRGB -> linear -> OKLab -> OKLCh
# Coefficients: Björn Ottosson, https://bottosson.github.io/posts/oklab/
# --------------------------------------------------------------------------

def hex_to_rgb(h):
    h = h.strip().lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"not a hex colour: {h}")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgb_to_oklab(rgb):
    r, g, b = (srgb_to_linear(c) for c in rgb)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def oklab_to_oklch(lab):
    L, a, b = lab
    C = math.hypot(a, b)
    H = math.degrees(math.atan2(b, a)) % 360.0
    return L, C, H


# Chroma below this and the hue angle is numerical noise, not a colour.
# 0.03 is too aggressive on a muted palette -- it swallows sages and slates
# that clearly read as green and blue. 0.02 keeps them; raise it if you want
# a tighter chromatic set.
NEUTRAL_C = 0.02


class Swatch:
    def __init__(self, hexcode):
        self.hex = '#' + hexcode.strip().lstrip('#').lower()
        if len(self.hex) == 4:
            self.hex = '#' + ''.join(c * 2 for c in self.hex[1:])
        self.rgb = hex_to_rgb(self.hex)
        self.lab = rgb_to_oklab(self.rgb)
        self.L, self.C, self.H = oklab_to_oklch(self.lab)
        # HSL hue, used only to pick a *name* for the hue family
        mx, mn = max(self.rgb), min(self.rgb)
        if mx == mn:
            self.hsl_h = 0.0
        else:
            r, g, b = self.rgb
            d = mx - mn
            if mx == r:
                self.hsl_h = ((g - b) / d) % 6
            elif mx == g:
                self.hsl_h = (b - r) / d + 2
            else:
                self.hsl_h = (r - g) / d + 4
            self.hsl_h = (self.hsl_h * 60.0) % 360.0

    @property
    def neutral(self):
        return self.C < NEUTRAL_C

    def __repr__(self):
        return f"{self.hex} L={self.L:.2f} C={self.C:.3f} H={self.H:.0f}"


# --------------------------------------------------------------------------
# Orderings
# --------------------------------------------------------------------------

def order_hue(sw):
    """Hue angle ascending; neutrals hived off to the front, sorted by L."""
    neutrals = sorted([s for s in sw if s.neutral], key=lambda s: s.L)
    chromatic = sorted([s for s in sw if not s.neutral], key=lambda s: (s.H, s.L))
    return neutrals + chromatic


def order_lightness(sw):
    return sorted(sw, key=lambda s: (s.L, s.H))


def order_path(sw):
    """Greedy nearest-neighbour walk in Oklab. Start from the darkest."""
    if not sw:
        return []
    remaining = list(sw)
    current = min(remaining, key=lambda s: s.L)
    remaining.remove(current)
    out = [current]
    while remaining:
        nxt = min(remaining, key=lambda s: dist(s.lab, current.lab))
        remaining.remove(nxt)
        out.append(nxt)
        current = nxt
    return out


def dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


# --------------------------------------------------------------------------
# Groupings
# --------------------------------------------------------------------------

# Named hue ranges, mrmrs / random-display-p3-color.
# https://github.com/mrmrs/random-display-p3-color
#
# IMPORTANT: these boundaries are HSL/HSV degrees. OKLCh hue angles are
# distributed quite differently -- an ochre sits at HSL 42 deg (orange) but
# OKLCh 86 deg, which lands inside the OKLCh green region. So bin on HSL hue
# for *naming*, and use OKLCh for ordering and distance, where it's better.
HUE_BINS = [
    ("red", 345, 360), ("red", 0, 15), ("orange", 15, 45), ("yellow", 45, 70),
    ("green", 70, 165), ("cyan", 165, 195), ("blue", 195, 260),
    ("purple", 260, 310), ("pink", 310, 345),
]
FAMILY_ORDER = ["neutral", "red", "orange", "yellow", "green",
                "cyan", "blue", "purple", "pink"]


def group_family(sw):
    out = {}
    for s in sw:
        if s.neutral:
            name = "neutral"
        else:
            name = next((n for n, lo, hi in HUE_BINS if lo <= s.hsl_h < hi), "red")
        out.setdefault(name, []).append(s)
    for v in out.values():
        v.sort(key=lambda s: s.L)
    return [(k, out[k]) for k in FAMILY_ORDER if k in out]


CHARACTER_ORDER = ["neutral", "pale", "muted", "vivid", "deep", "dark"]


def character_of(s):
    """Chroma + lightness only. Hue is a weaker predictor of a palette's feel
    than chroma and lightness are, so these bands often cut more usefully
    than hue families do."""
    if s.neutral:
        return "neutral"
    if s.L < 0.35:
        return "dark"
    if s.C >= 0.14:
        return "vivid"
    if s.L >= 0.78:
        return "pale"
    if s.C >= 0.09:
        return "deep"
    return "muted"


def group_character(sw):
    out = {}
    for s in sw:
        out.setdefault(character_of(s), []).append(s)
    for v in out.values():
        v.sort(key=lambda s: (s.H, s.L))
    return [(k, out[k]) for k in CHARACTER_ORDER if k in out]


def group_kmeans(sw, k=5, seed=7, iters=60):
    """Lloyd's algorithm in Oklab. Euclidean distance there is a reasonable
    proxy for perceptual difference, which is the whole point of using it."""
    k = min(k, len(sw))
    if k < 1:
        return []
    rng = random.Random(seed)

    # k-means++ init
    centres = [rng.choice(sw).lab]
    while len(centres) < k:
        d2 = [min(dist(s.lab, c) ** 2 for c in centres) for s in sw]
        total = sum(d2)
        if total == 0:
            centres.append(rng.choice(sw).lab)
            continue
        r, acc = rng.random() * total, 0.0
        for s, w in zip(sw, d2):
            acc += w
            if acc >= r:
                centres.append(s.lab)
                break

    assign = [0] * len(sw)
    for _ in range(iters):
        changed = False
        for i, s in enumerate(sw):
            best = min(range(k), key=lambda c: dist(s.lab, centres[c]))
            if best != assign[i]:
                assign[i], changed = best, True
        for c in range(k):
            members = [sw[i].lab for i in range(len(sw)) if assign[i] == c]
            if members:
                centres[c] = tuple(sum(m[j] for m in members) / len(members)
                                   for j in range(3))
        if not changed:
            break

    clusters = {}
    for i, s in enumerate(sw):
        clusters.setdefault(assign[i], []).append(s)
    # order clusters by mean lightness so output is stable and readable
    ordered = sorted(clusters.values(), key=lambda g: sum(s.L for s in g) / len(g))
    return [(f"cluster {i + 1}", g) for i, g in enumerate(ordered)]


# --------------------------------------------------------------------------
# PNG rendering
# --------------------------------------------------------------------------

def render(sections, path, sw_w=86, sw_h=86, gap=8, pad=28, label_h=18):
    from PIL import Image, ImageDraw, ImageFont

    def font(sz, bold=False):
        name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        try:
            return ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{name}", sz)
        except OSError:
            return ImageFont.load_default()

    f_head = font(15, bold=True)
    f_sub = font(11)
    f_lab = font(10)

    max_cols = max((len(rows) for _, rows in sections for rows in [rows]), default=1)
    max_cols = max(len(r) for _, blocks in sections for _, r in blocks) if sections else 1

    width = pad * 2 + max_cols * (sw_w + gap) - gap
    width = max(width, 560)

    # measure height
    y = pad
    for title, blocks in sections:
        y += 26
        for _, rows in blocks:
            y += 16 + sw_h + label_h + gap
        y += 14
    height = y + pad

    img = Image.new("RGB", (width, height), "#ffffff")
    d = ImageDraw.Draw(img)

    y = pad
    for title, blocks in sections:
        d.text((pad, y), title, font=f_head, fill="#111111")
        y += 26
        for label, rows in blocks:
            d.text((pad, y), label, font=f_sub, fill="#666666")
            y += 16
            for i, s in enumerate(rows):
                x = pad + i * (sw_w + gap)
                d.rectangle([x, y, x + sw_w, y + sw_h], fill=s.hex,
                            outline="#dddddd")
                d.text((x, y + sw_h + 4), s.hex, font=f_lab, fill="#444444")
            y += sw_h + label_h + gap
        y += 14

    img.save(path)
    return path


# --------------------------------------------------------------------------

def parse_codes(text):
    return [Swatch(h) for h in re.findall(r'#?[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b', text)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("codes", nargs="?", default="")
    ap.add_argument("--file")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--out", default="palette.png")
    args = ap.parse_args()

    text = Path(args.file).read_text() if args.file else args.codes
    if not text:
        text = sys.stdin.read()
    sw = parse_codes(text)
    if not sw:
        sys.exit("No hex codes found.")

    sections = [
        ("Orderings", [
            ("by hue (OKLCh H, neutrals first)", order_hue(sw)),
            ("by lightness (OKLCh L)", order_lightness(sw)),
            ("nearest-neighbour path (Oklab)", order_path(sw)),
        ]),
        ("Grouped by hue family", group_family(sw)),
        ("Grouped by character", group_character(sw)),
        (f"Grouped by k-means (k={args.k})", group_kmeans(sw, k=args.k)),
    ]

    render(sections, args.out)

    for title, blocks in sections:
        print(f"\n## {title}")
        for label, rows in blocks:
            print(f"{label}: {' '.join(s.hex for s in rows)}")
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
