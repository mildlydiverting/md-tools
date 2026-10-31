# Obsidian Clipper template — Wikipedia / Commons artwork

Companion to `wiki-cite` (the bookmarklet). Where that one builds citations in a floating panel for copying out, this one clips the file page straight into Obsidian as a note with structured frontmatter.

## Install

1. Open Obsidian Web Clipper → **Settings** → **Templates**.
2. Click **Import** and select `wikipedia-commons-artwork.json`.
3. The template will fire automatically on any URL matching:
   - `https://commons.wikimedia.org/wiki/File:…`
   - `https://*.wikipedia.org/wiki/File:…`

Save path defaults to `Clippings/Artworks/` — change in the template settings if you want.

## What it does

On a Commons / Wikipedia File page using the **Artwork** template, the clip gets:

**Frontmatter**: `title`, `artist`, `artist_url`, `date`, `year`, `medium`, `dimensions`, `institution`, `institution_url`, `department`, `accession_number`, `source`, `collection_url`, `license`, `license_url`, `permalink`, `image_url`, `website`, `date_accessed`, `tags`.

**Body**: image embed, header line (artist · title · date), medium · dimensions, institution, description, and two markdown citations — TASL and your Harvard smush — followed by file / full image / collection page links.

Note name: `Artist – YYYY – Title`, truncated and `safe_name`-filtered so it's filesystem-safe.

## Selector strategy

Commons renders the Artwork template as a `<table class="fileinfotpl-type-artwork vevent">` whose label cells carry stable IDs: `#fileinfotpl_art_artist`, `_title`, `_date`, `_medium`, `_dimensions`, `_institution`, `_dept`, `_accession`, `_source`. The value is always in the adjacent `<td>`, which this template grabs with `~ td` (general sibling, more forgiving than `+`).

The license comes from the Commons license template: `.licensetpl_short` (name) and `.licensetpl_link` (URL).

The full image URL comes from `#file a?href` with a `replace` to upgrade protocol-relative `//upload.wikimedia.org/…` to `https://`.

## Limits (compared with the `wiki-cite` bookmarklet)

Obsidian Clipper runs DOM selectors against the current page. It cannot call MediaWiki or Wikidata APIs. So:

- Dates come through as rendered on the page, e.g. `circa 1629–1630`. The `year` property extracts the first 4-digit number via a regex `replace`. No handling of P1480 / earliest-latest qualifiers like the bookmarklet does.
- Artwork records that live only on Wikidata (not shown in the Commons Information or Artwork template) won't appear.
- Non-artwork File pages (using the generic Information template) will leave the `_art_*` selectors empty. The clip still works but most frontmatter will be blank — the template is deliberately tuned for artwork pages. A sibling template for plain Information-template pages would use `#fileinfotpl_credit`, `#fileinfotpl_aut`, `#fileinfotpl_date` instead.
- Older Commons art pages that pre-date the Artwork template won't have the `_art_*` IDs. Rare, but possible.

If frontmatter comes through empty on a page you expected to work, open DevTools and check whether the table has class `fileinfotpl-type-artwork`. If not, the page is using a different template and will need a variant.

## Giving it back to the Clipper project

Obsidian Clipper has a `src/utils/fixtures/templates/` folder with sample templates (`imdb.json`, `goodreads.json`, `youtube.json`, etc.). This template is in the same shape and would be a reasonable contribution — PR against <https://github.com/obsidianmd/obsidian-clipper> adding `wikipedia-commons-artwork.json` to that fixtures folder, plus a test fixture page.

Also worth considering: a plain-Wikipedia-article template (news articles get decent Defuddle output already, but encyclopedia articles need the infobox pulled out specifically) and a Wikimedia Commons category / search page template.

## Related

- `wiki-cite/` — the Safari bookmarklet; richer data via APIs, but no save-to-Obsidian step.
- `_citation-formats-tasl-harvard-apa.md` (md-pkim-library) — the format reference these were built against.
- MediaWiki Artwork template documentation: <https://commons.wikimedia.org/wiki/Template:Artwork>
- Obsidian Clipper variables & filters: <https://help.obsidian.md/web-clipper/variables>
