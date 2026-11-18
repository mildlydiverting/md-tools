---
title: Obsidian Clipper templates — handoff note
date: 2026-11-09
author: Kim Plowright (with Claude)
status: working, with caveats
---

# obsidian-clipper-templates

Obsidian Web Clipper templates for art-reference workflows. Companion to the `wiki-cite` bookmarklet next door — see `../wiki-cite/HANDOFF.md`.

**TL;DR**: for Wikimedia Commons citation work, the bookmarklet in `../wiki-cite/` is the better tool. It uses MediaWiki + Wikidata APIs and produces clean, correct, structured data. This Clipper template is a best-effort DOM-only extractor that catches the easy fields and drops the rest. Use it to make a quick Obsidian note stub; curate manually or paste the bookmarklet's output in.

## What's here

- `wikipedia-commons-artwork.json` — the current (v5) template, same content as `wikipedia-commons-artwork-v5.json`. Import this one into Clipper.
- `wikipedia-commons-artwork-v5.json` — latest iteration, kept as a named backup.
- `wikipedia-commons-artwork-3.json` and `-4.json` — older iterations, kept for comparison. Not for use.
- `README.md` — install instructions and selector strategy (written against v3/v4; some details stale, see below).

## Install

1. Obsidian Web Clipper → **Settings → Templates → Import**.
2. Pick `wikipedia-commons-artwork.json`.
3. Delete any older versions of the same template that are already imported (Clipper doesn't deduplicate on re-import).
4. The template auto-fires on URLs matching `https://commons.wikimedia.org/wiki/File:…`. It does **not** fire on en.wikipedia.org File: pages — those render the Commons Artwork template with its hidden QuickStatements metadata leaking into text content, and the output is unusable. If you need to clip an en.wiki File page, click through to the Commons original first.

Save path defaults to `Clippings/Artworks/` — change in the template settings if you want.

## What the template extracts (and what breaks)

**Reliable**:
- `permalink` — current page URL.
- `date` / `year` — from `#fileinfotpl_date` on the Information template, or `_art_date` on the Artwork template. Regex-extracts the first 4-digit year for the `year` property.
- `license` / `license_url` — the first `.licensetpl_short` / `.licensetpl_link` via `:first-of-type`.
- `image_url` — `#file a?href` with `utm_source` stripped and protocol-relative URLs upgraded to `https://`.
- `website`, `date_accessed`, `tags` — constants.

**Fragile** (works on some pages, breaks on others):
- `artist` — targets the first anchor in the artist cell (`#fileinfotpl_aut + td a` with `|nth:1`). On files with a `commons-creator-table` carrying 10+ authority-file links (VIAF, ISNI, ULAN, LCCN, NLA, WorldCat, …), `|nth:1` is expected to pick the first anchor but sometimes returns the whole array.
- `title` — targets the first `[lang]` div in the title cell. On multilingual files the first language varies by uploader.
- `medium` / `dimensions` — field-label-aware QS-strip regex (`/medium ?QS:.*/gis` etc.). Should strip the hidden QuickStatements metadata that leaks into the DOM.

**Known-broken / missing on this template**:
- `institution`, `institution_url`, `department`, `accession_number`, `collection_url` — on many Commons artwork pages these fields aren't filled in at all. The data lives on the linked Wikidata item instead, which Clipper can't reach (DOM-only).

## Why this is harder than it looks

Obsidian Clipper runs **DOM selectors against the current page only**. It cannot call the MediaWiki or Wikidata APIs. Commons' DOM is hostile to extraction:

1. **QuickStatements metadata** (`title QS:P1476,...`, `medium QS:P186,...`) is rendered into the HTML as hidden `<span>` elements. CSS normally hides them; `textContent` extraction grabs them anyway, concatenated directly against the real value with no separator (so you get `canvasmedium QS:P186,...` where the field label "medium" is welded to the content "canvas"). Field-specific regex strips help but require the right label per field.
2. **Multilingual titles** render as multiple `<div lang="xx">` siblings. All visible. There's no "preferred language" signal — Clipper picks whichever one comes first in the DOM.
3. **The Creator template** emits a `commons-creator-table` div with inline `<style>` blocks (the CSS text leaks into `textContent`) and a dozen authority-file anchors. Picking just "the artist name" requires knowing the DOM path.
4. **Many fields live only on Wikidata**, not in the Commons DOM. Dimensions on simple files live in the Artwork template; on richer files they're inferred from Wikidata P2048/P2049 and don't appear in the rendered HTML at all.

The `wiki-cite` bookmarklet avoids all of this by going via the APIs. If citation quality matters, use that.

## Version history

- **v1, v2** (not in this folder): first drafts. v1 triggered on both en.wiki and commons. v2 scoped to Commons-only and removed `truncate` filter (which doesn't exist in Clipper).
- **v3** (`wikipedia-commons-artwork-3.json`): added field-label QS-strip regex, language-prefix strip for title, artist-dates strip for filename. Regex didn't fire — suspected Clipper requires `g` flag.
- **v4** (`wikipedia-commons-artwork-4.json`): switched from `~ td` (general sibling) to `+ td` (adjacent), tried `:first-of-type` to pick first-match. Worked for license (siblings-same-parent), failed for artist (anchors in different parents in the creator table).
- **v5** (`wikipedia-commons-artwork-v5.json` and `wikipedia-commons-artwork.json`): added `|nth:1` filter to pick first array element, `g` flag on all regexes, field-label-aware QS-strip patterns. Partial improvement.

## Future directions

### Short-term

- **A plain-Information-template sibling** for non-artwork files (photographs, snapshots, documents). Would use `#fileinfotpl_credit`, `#fileinfotpl_aut`, `#fileinfotpl_date` and give up on medium/dimensions/institution. Much simpler and more reliable.
- **A Wikipedia article-page template** for `en.wikipedia.org/wiki/<Article>` — reads the article infobox (which is cleaner-structured than the File page). Useful for clipping artworks while reading about them.

### Medium-term

- **Clipper interpreter**: Obsidian Clipper has an LLM-powered interpreter mode that can clean up extracted content. Could feed the raw cell HTML to a prompt and get back clean fields. Costs API calls per clip but would fix the DOM-pollution problems in one go.
- **Contribute upstream**: if this template stabilises, the shape matches Clipper's `src/utils/fixtures/templates/` fixtures (`imdb.json`, `goodreads.json`, `youtube.json`). PR candidate against <https://github.com/obsidianmd/obsidian-clipper>.

### Longer-term

- Supersede with the Safari Web Extension path described in `../wiki-cite/HANDOFF.md`. That extension would subsume both this template and the bookmarklet, and could write directly to Obsidian via URI scheme or local file write.

## Related

- `../wiki-cite/` — the bookmarklet. Use this for anything that needs rich, accurate data.
- `../wiki-cite/HANDOFF.md` — bookmarklet handoff note with API details.
- `_citation-formats-tasl-harvard-apa.md` (md-pkim-library vault) — the citation format reference these templates target.

## References

- [Obsidian Web Clipper documentation](https://help.obsidian.md/web-clipper)
- [Clipper variables and filters](https://help.obsidian.md/web-clipper/variables)
- [Clipper repo](https://github.com/obsidianmd/obsidian-clipper)
- [MediaWiki Artwork template](https://commons.wikimedia.org/wiki/Template:Artwork)
- [MediaWiki Information template](https://commons.wikimedia.org/wiki/Template:Information)
