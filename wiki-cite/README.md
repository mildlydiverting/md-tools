# wiki-cite

A Safari bookmarklet for extracting a citation from any Wikipedia or Wikimedia Commons `File:` page.

Click the bookmarklet while viewing a file page and a floating panel appears with the citation in five formats:

- **YAML** — frontmatter block, machine-readable, every field present
- **Markdown (yours)** — your preferred smush format: `Author (yyyy) _Title_. [Medium][Dimensions]. Org, Location. Available at [url](url) (Accessed yyyy-mm-dd). Licensed under [License](license-url).`
- **TASL** — Creative Commons recommended practice: Title - Author - from Source under License
- **Eagle** — plain `Key: value` list for pasting into Eagle's notes field
- **JSON** — same fields as YAML, as JSON

Each tab has a Copy button, plus "Copy all formats" for a bundle.

## Install (Safari)

1. Open `bookmarklet.txt`, select the entire contents, copy.
2. In Safari, Bookmarks → Edit Bookmarks → Favourites.
3. Right-click → Add Bookmark. Call it something like **wiki-cite**.
4. Edit the bookmark and paste the `javascript:...` URL into the Address field.
5. Visit any `File:` page on en.wikipedia.org or commons.wikimedia.org and click the bookmark.

The bookmarklet is 26 KB — well within Safari's URL limits.

## What it pulls, and from where

| Field | Source |
|---|---|
| Creator (artist) | Wikidata P170 → P50 → `imageinfo.extmetadata.Artist` |
| Title | Wikidata item label → `ObjectName` → `ImageDescription` → filename |
| Date | Wikidata P571 (handles circa via P1480, and start/end via P580/P582) → `DateTimeOriginal` |
| Medium | Wikidata P186 |
| Dimensions | Wikidata P2048 (height) × P2049 (width), with unit |
| Institution | Wikidata P195 (collection) |
| Location in institution | Wikidata P276 |
| Inventory number | Wikidata P217 |
| Canonical collection URL | Wikidata P973 (described at URL) |
| Permalink | `imageinfo.descriptionurl` + `?oldid=<revid>` |
| Image URL | `imageinfo.url` |
| License | `extmetadata.LicenseShortName` + `LicenseUrl` |
| Usage terms | `extmetadata.UsageTerms` |
| Credit | `extmetadata.Credit` |
| Date uploaded | `imageinfo.timestamp` |
| Date accessed | now |
| Linked Wikidata item | SDC P6243 (digital representation of) → P180 (depicts) → pageprops.wikibase_item |

Everything comes from three MediaWiki APIs:

- `imageinfo` with `iiprop=extmetadata` on the current wiki
- `wbgetentities` on Commons for the file's M-id (Structured Data on Commons)
- `wbgetentities` on Wikidata for the depicted work and all referenced Q-ids (for human-readable labels)

All three support CORS with `origin=*`, so no proxy or extension permissions needed.

## Format reference

Your citation formats note: `_citation-formats-tasl-harvard-apa.md` in `md-pkim-library`.

- TASL: Creative Commons recommended attribution — <https://wiki.creativecommons.org/wiki/Recommended_practices_for_attribution>
- MediaWiki `imageinfo` API: <https://www.mediawiki.org/wiki/API:Imageinfo>
- Structured Data on Commons: <https://commons.wikimedia.org/wiki/Commons:Structured_data>
- Wikidata property reference for artworks: <https://www.wikidata.org/wiki/Wikidata:WikiProject_Visual_arts/Item_structure>

## Possible futures

- **Full extension**: this is roughly 60% of what a real browser extension would do; the panel UI, API fetches and formatting would all port directly to a Safari Web Extension. The missing piece is settings (which formats, custom template strings) and multi-page capture.
- **Obsidian Clipper template**: once the panel supports per-field extraction, the data model here (`creator`, `title`, `date`, etc.) maps cleanly onto Obsidian Clipper's `{{variable|filter}}` template syntax. Could be contributed as a built-in template for Wikipedia/Commons File pages — see `src/utils/fixtures/templates/` in the clipper source.
- **Other sources**: Flickr (needs API key), Europeana (public API, rich metadata), Rijksstudio, museum collection pages — each would need its own extractor module.
- **Fallback DOM parse**: if the API is down or returns nothing, scrape the Information template directly from the page. Not yet implemented.

## Known limits

- Only Wikipedia-family File: pages. Won't work on article pages or museum sites.
- For files not linked to a Wikidata work item, dimensions/medium/institution won't appear — those live only on the item, not in the file's own metadata.
- Circa dates: handles `P1480 → Q5727902` and start/end-time qualifiers, but exotic date qualifiers may just come through as the main value.
- Only pulls English labels. Easy to extend if you want others.
