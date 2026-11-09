---
title: wiki-cite — handoff note
date: 2026-11-09
author: Kim Plowright (with Claude)
status: working, v1
---

# wiki-cite

A Safari bookmarklet that extracts a citation from any Wikipedia or Wikimedia Commons `File:` page and shows it in a floating panel with five formats ready to copy.

Lives at `md-tools-pkim/wiki-cite/`. Companion (much weaker) Obsidian Clipper template lives at `md-tools-pkim/obsidian-clipper-templates/`.

## What's here

- `wiki-cite.js` — readable source (~22 KB). Edit this.
- `bookmarklet.txt` — the compiled `javascript:…` one-liner, ~26 KB. Regenerated from the source.
- `README.md` — install instructions, field-mapping table, data sources.
- `HANDOFF.md` — this file.

## What it does

Click the bookmarklet on a File page. A floating panel appears with tabs:

- **Markdown** — the preferred Harvard smush format: `Author (yyyy) _Title_. [Medium][Dimensions]. Org, Location. Available at [url](url) (Accessed yyyy-mm-dd). Licensed under [License](license-url).`
- **TASL** — Creative Commons recommended practice: Title - Author - from Source under License.
- **Eagle** — plain `Key: value` list for pasting into Eagle's notes field.
- **YAML** — frontmatter block with every field, machine-readable.
- **JSON** — same fields as YAML, as JSON.

Each tab has a Copy button; "Copy all formats" bundles the lot.

## How it works

The bookmarklet runs in the page, so it inherits the user's logged-in state and bypasses CORS by using `origin=*` on three MediaWiki APIs:

1. **`imageinfo` + `extmetadata`** on the current wiki — artist, title, date, license, credit, usage terms, upload date.
2. **`wbgetentities` on Commons** for the file's M-id — Structured Data on Commons (SDC). Reads P6243 "digital representation of" → artwork's Wikidata Q-id.
3. **`wbgetentities` on Wikidata** for the depicted work and all referenced Q-ids — pulls creator (P170), inception (P571, with circa/earliest-latest qualifier handling), medium (P186), dimensions (P2048 × P2049), collection (P195), location in institution (P276), inventory number (P217), canonical collection URL (P973), plus human-readable labels for every linked entity.

All three APIs are public and CORS-open, so no extension permissions, no proxy, nothing to install beyond the bookmarklet itself.

## Install (Safari)

1. Open `bookmarklet.txt`, copy the entire contents.
2. Safari → Bookmarks → Edit Bookmarks → Favourites → right-click → Add Bookmark.
3. Name it **wiki-cite**, paste the `javascript:…` into Address.
4. Visit any `File:` page on `commons.wikimedia.org` or `en.wikipedia.org` and click the bookmark.

## Development

Edit `wiki-cite.js` directly. To rebuild `bookmarklet.txt`:

```bash
node -e "
const fs = require('fs');
let src = fs.readFileSync('wiki-cite.js', 'utf8');
src = src.replace(/^\s*\/\*![\s\S]*?\*\/\s*/, '');
src = src.replace(/\n\s*\/\/[^\n]*/g, '');
src = src.replace(/^\s+/gm, '');
src = src.replace(/\s*\n\s*/g, ' ');
src = src.replace(/\s{2,}/g, ' ');
fs.writeFileSync('bookmarklet.txt', 'javascript:' + encodeURIComponent(src));
"
```

Then re-add the new `bookmarklet.txt` contents to the Safari bookmark (Safari doesn't hot-reload bookmarklet URLs — you have to replace them).

The minifier strips the top banner comment and line comments only — it does not touch inline `//` comments, so don't add any in `wiki-cite.js` (they'll swallow the rest of their line after newlines collapse). Use `/* … */` block comments instead.

## Known limits

- **Only Wikipedia-family File: pages.** Not for article pages, not for museum sites.
- **Fields that live only on Wikidata won't appear** unless the file is linked to a Wikidata item via SDC P6243 or the file page's own `wikibase_item`. Older Commons files uploaded without SDC may be thinner.
- **Circa dates**: handles P1480 → Q5727902 and P580/P582 earliest/latest qualifiers. Exotic date qualifiers come through as the main value.
- **English labels only.** The Wikidata fetches request `languages=en`. Easy to extend if you want British English specifically (rare for this data) or multilingual.
- **No fallback DOM parse.** If the API call fails for a given field, that field is empty. Could be added: on empty, scrape the Information template directly from the current page's DOM.

## Future directions

### Short-term

- **Fallback DOM parse** for when the API returns thin data. Would catch legacy Commons uploads that pre-date SDC.
- **Language preference**: add a setting (stored in `localStorage`) for preferred label language.
- **Customise formats**: let the user tweak the Markdown template strings in-UI, save to `localStorage`.

### Medium-term

- **Safari Web Extension**: the bookmarklet's three API calls, panel UI, and format logic port directly to a WebExtension. The missing pieces are (a) settings UI, (b) a proper options page, (c) permissions handling for arbitrary wikis. Chromium/Firefox builds come for free with the same manifest.
- **Obsidian Clipper template upstream**: the clipper template in `../obsidian-clipper-templates/` has the right shape for `src/utils/fixtures/templates/` in the obsidian-clipper repo. The DOM-only limits are real but a minimal version could be a useful contribution — <https://github.com/obsidianmd/obsidian-clipper>.

### Longer-term

- **Other sources**: Flickr (needs API key), Europeana (public API, rich metadata), Rijksstudio, direct museum collection pages (each would need its own extractor module). The bookmarklet architecture — detect source → gather → assemble → format — ports cleanly to each.
- **Universal web-ingest browser extension** (see `/areas/web-clipper-extension.md` in memory): this bookmarklet is one strand of that larger idea, alongside dezoomify, metadata sniffing, batch image download, multi-source clipping into Eagle / Obsidian / Are.na.

## Related work

- **Obsidian Clipper template**: `../obsidian-clipper-templates/wikipedia-commons-artwork.json` — DOM-only, much weaker than this bookmarklet because Commons' DOM is hostile to extraction (hidden QuickStatements metadata leaks into text content, creator tables carry inline CSS). Lives in the same project but should be treated as a stub-note-maker rather than a citation builder. See its README for current state (v5 is the latest iteration; several versions still in the folder for comparison).
- **Citation formats reference**: `_citation-formats-tasl-harvard-apa.md` in the `md-pkim-library` vault — the source of the format conventions used here.
- **md-pkim-classification**: the ontology work this feeds into.

## References

- [MediaWiki API: Imageinfo](https://www.mediawiki.org/wiki/API:Imageinfo)
- [Structured Data on Commons](https://commons.wikimedia.org/wiki/Commons:Structured_data)
- [Wikidata WikiProject Visual Arts item structure](https://www.wikidata.org/wiki/Wikidata:WikiProject_Visual_arts/Item_structure)
- [Creative Commons Recommended Practices for Attribution](https://wiki.creativecommons.org/wiki/Recommended_practices_for_attribution)
