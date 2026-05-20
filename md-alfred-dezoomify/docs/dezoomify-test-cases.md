# Dezoomify Test Cases & Site Research

Reference document for testing dezoomify-rs Alfred workflow against museum/gallery collection pages.
Tracks which sites work, which fail, what tile technology each uses, and what approach to take for fixes.

**Last updated**: 2026-05-20

---

## The dezoomify ecosystem

Three tools, different layers — understanding what exists avoids reinventing things.

### dezoomify-rs (Rust CLI — what our Alfred workflow uses)

Built-in dezoomers: Google Arts & Culture, Zoomify, DeepZoom (DZI/Seadragon), IIIF, Zoomify PFF, krpano, IIPImage, NYPL, generic (URL template with `{{X}}`/`{{Y}}`), custom YAML.

- Repo: https://github.com/lovasoa/dezoomify-rs
- Docs on custom YAML: https://github.com/lovasoa/dezoomify-rs/wiki/Usage-example-for-the-custom-YAML-dezoomer
- DeepWiki ref: https://deepwiki.com/lovasoa/dezoomify-rs/3.6-custom-and-generic-formats

### dezoomify (JS web app)

Has some **site-specific dezoomers the Rust version doesn't**:
- `nationalgallery.js` — National Gallery's own format
- `xlimage.js` — Italian company format (used on several sites)
- `topviewer.js` — TopViewer format
- `fsi.js` — FSI Server
- `vls.js` — VLS viewer
- Picturae (several Dutch sites)

Also has: zoomify, seadragon (DeepZoom), iipimage, zoomify-pff, iiif, krpano, generic, automatic.

- Repo: https://github.com/lovasoa/dezoomify
- Dezoomers source: https://github.com/lovasoa/dezoomify/tree/master/dezoomers
- How to add a new site: https://github.com/lovasoa/dezoomify/wiki/How-to-add-support-for-a-new-website

### dezoomify-extension (browser extension)

Intercepts network requests and pattern-matches URLs to find tile/manifest endpoints. This is what finds the hidden IIIF/Zoomify/DZI URL that isn't in the page URL. The Chrome version is unmaintained (Manifest V2); a V3 fork exists at https://github.com/jbenton/dezoomify-extension-chromefix.

- Repo: https://github.com/lovasoa/dezoomify-extension
- Firefox: https://addons.mozilla.org/en-US/firefox/addon/dezoomify/
- Chrome V3 fork: https://chromewebstore.google.com/detail/dezoomify-v3/phjngidoalpcjbhgkdopmajfimmaocde

### What this means for us

Our Alfred workflow currently passes the browser URL straight to dezoomify-rs. When that fails, we have three possible fix strategies per site:

1. **Scraper** — Python fetches page HTML, extracts the tile/manifest URL, retries dezoomify-rs with that. Good for sites where the IIIF/Zoomify URL is in the page source but not the page URL.
2. **Custom YAML** — Write a `.yaml` tile definition. Good for sites with predictable tile URL patterns that dezoomify-rs doesn't auto-detect. Requires knowing tile dimensions per-image (so still needs a lightweight metadata extractor).
3. **Port a JS dezoomer** — Some JS dezoomers handle site-specific quirks (National Gallery, XLimage). Could port the logic to Python for our fallback, or contribute a Rust dezoomer upstream.

---

## Status key

| Status | Meaning |
|--------|---------|
| ✅ Working | dezoomify-rs handles the page URL directly |
| ⚠️ Indirect | Works if you give it the manifest/tile URL, not the page URL |
| 🔧 In progress | Scraper or fix partially built |
| ❌ Fails | dezoomify-rs can't find a dezoomer |
| 🔲 Todo | Not yet tested |
| 🚫 Not zoomable | Site doesn't serve tiled/zoomable images |

---

## Test cases

| Site | CLI | Web | Alfred | Test URL | Tile tech | Notes |
|------|-----|-----|--------|----------|-----------|-------|
| Art Institute of Chicago | ✅ Working | 🔲 Todo | ✅ Working | <https://www.artic.edu/artworks/216746/cat> | IIIF v2 | From dezoomify-rs GitHub issues. IIIF path extracted from page source. |
| Art Institute of Chicago | ✅ Working | 🔲 Todo | 🔲 Todo | <https://www.artic.edu/artworks/103887/a-young-lady-with-a-parrot> | IIIF v2 | Fixed a manifest issue where dezoomify was not seeing the manifest in Python. |
| Barnes Foundation | 🔲 Todo | 🔲 Todo | 🔲 Todo | <https://collection.barnesfoundation.org/objects/5663/Young-Woman-Writing-(Jeune-femme-ecrivant)/> | Unknown | Pierre Bonnard, "Young Woman Writing" |
| Courtauld Gallery | ❌ Fails | 🔲 Todo | 🔲 Todo | <https://gallerycollections.courtauld.ac.uk/object-d-1952-rw-219> | Unknown | |
| Danish Royal Library (KB.dk) | 🔲 Todo | 🔲 Todo | 🔲 Todo | <https://digitalesamlinger.kb.dk/pamphlets/dasmaa/2008/feb/daellsvarehus/object74001/en/> | Unknown | Pamphlet collection |
| Frick Collection | ❌ Fails | 🔲 Todo | 🔲 Todo | <https://collections.frick.org/objects/100/sir-thomas-more?ctx=60f15eabaf5ab42062d92a044cd5fb556130f057&idx=7> | Unknown | |
| Google Arts & Culture | ✅ Working | 🔲 Todo | ✅ Working  | <https://artsandculture.google.com/asset/light-in-the-dark/ZQFouDGMVmsI2w> | GAC native | Pesenti, "Light in the Dark". Documented known-good. Google caps resolution. |
| Google Arts & Culture | ✅ Working | 🔲 Todo | ✅ Working  | <https://artsandculture.google.com/asset/leichtes-light-kandinsky-vassily/BgH3g-qr8YpCGA> | GAC native | Kandinsky, "Leichtes (Light)" |
| Google Arts & Culture | ✅ Working | 🔲 Todo | ✅ Working  | <https://artsandculture.google.com/asset/ingres's-violin-man-ray/kQGJ3YIoasGh0A> | GAC native | Man Ray, "Ingres's Violin" |
| Google Arts & Culture | ✅ Working | 🔲 Todo | ✅ Working  | <https://artsandculture.google.com/asset/madame-x-madame-pierre-gautreau-john-singer-sargent/XQFBdVEh0NHo0A> | GAC native | Sargent, "Madame X" |
| Google Arts & Culture | ✅ Working | 🔲 Todo | ✅ Working  | <https://artsandculture.google.com/asset/horse-study-after-george-stubbs-anatomy-of-the-horse-clara-drummond/IQHEEIRr5uvO7A> | GAC native | Clara Drummond, Horse Study |
| Harvard Art Museums | 🔲 Todo | 🔲 Todo | 🔲 Todo | <https://harvardartmuseums.org/collections/object/299848> | Unknown | Public API available. |
| Harvard Art Museums (Library) | ❌ Fails | 🔲 Todo | 🔲 Todo | <https://curiosity.lib.harvard.edu/daguerreotypes-at-harvard/catalog/17-HUAM160264_URN-3:HUAM:LEG002372_DYNMC> | IIIF | From dezoomify-rs issues. Detected by IIIF plugin: `<https://mps.lib.harvard.edu/assets/images/drs:43154096/info.json`> |
| Leopold Museum | 🚫 Not zoomable | 🚫 Not zoomable | 🚫 Not zoomable | <https://onlinecollection.leopoldmuseum.org/objekt/539-sitzender-mannerakt-selbstdarstellung/#objektdaten> | N/A | Confirmed: not a zoomable image. |
| Met Museum | ❌ Fails | 🔲 Todo | ❌ Fails | <https://www.metmuseum.org/art/collection/search/435809> | Unknown | Has public API (`metmuseum.github.io`). Check if zoomable or just large JPEG download. |
| Met Museum | ❌ Fails | 🔲 Todo | 🔲 Todo | <https://www.metmuseum.org/art/collection/search/73809> | Unknown | |
| MKG Hamburg | 🔲 Todo | 🔲 Todo | 🔲 Todo | <https://www.mkg-hamburg.de/en/object/mkg-e00240258> | Unknown | |
| National Galleries of Scotland | 🔲 Todo | 🔲 Todo | 🔲 Todo | <https://www.nationalgalleries.org/art-and-artists/42229> | Unknown | Listed as supported by dezoomify-extension. |
| National Gallery, London | ❌ Fails | 🔲 Todo | ✅ Working | <https://www.nationalgallery.org.uk/paintings/edouard-manet-woman-with-a-cat> | IIPImage/IIIF | Manet, "Woman with a Cat". TIFF path extracted from page source. Works in Alfred but fails bare CLI. |
| National Gallery, London | 🔲 Todo | 🔲 Todo | ✅ Working  | <https://www.nationalgallery.org.uk/paintings/paolo-uccello-the-battle-of-san-romano> | IIPImage/IIIF | Uccello, Battle of San Romano. JS dezoomify has dedicated `nationalgallery.js` — check if still needed or if NG now uses standard IIIF. |
| NGV (National Gallery of Victoria) | ❌ Fails | 🔲 Todo | 🔲 Todo | <https://www.ngv.vic.gov.au/explore/collection/work/3867/> | Zoomify | Constable, "The Quarters behind Alresford Hall". Tested 2 May. Image ID `Fd104934` not derivable from page URL. Fix: scraper to extract Zoomify base URL from page source. |
| Rijksmuseum | 🔧 In progress | 🔲 Todo | 🔧 In progress | <https://www.rijksmuseum.nl/en/collection/object/Nude-Woman-Lying-on-a-Pillow--6af483682af3df3a835a526f7beb07f3> | IIIF via Micrio | Tested 2 May. Shortcode not in page URL — needs scraper. Currently picks up wrong image from related artworks. Fix: extract `iiif.micr.io/{SHORTCODE}` from page source → construct info.json URL. |
| SMK (National Gallery of Denmark) | ❌ Fails | 🔲 Todo | 🔲 Todo | <https://open.smk.dk/en/artwork/image/KMS3402?q=cat> | Unknown | |
| Tate | 🔲 Todo | 🔲 Todo | 🔲 Todo | <https://www.tate.org.uk/art/artworks/johnson-young-man-in-green-t16376> | Unknown | Claudette Johnson, "Young Man in Green" |
| ThULB (Jena University Library) | ❌ Fails | 🔲 Todo | 🔲 Todo | <https://collections.thulb.uni-jena.de/rsc/viewer/HisBest_derivate_00004529/BE_1110_0593.tif> | Unknown | From issues |
| V&A | 🔲 Todo | 🔲 Todo | 🔲 Todo | <https://collections.vam.ac.uk/item/O685128/9-the-end-of--drawing-louis-wain/> | Unknown | Louis Wain drawing |
| Van Gogh Museum | ❌ Fails | 🔲 Todo | 🔲 Todo | <https://www.vangoghmuseum.nl/en/collection/s0468N1996> | Unknown | Odilon Redon, "Roses in a Vase on a Small Table". From issues. |
| Wellcome Collection | ✅ Working | ✅ Working | ✅ Working | <https://wellcomecollection.org/works/zs6gser7/images?id=c7hxpemj> | IIIF | Wellcome uses IIIF extensively. |
| Wellcome Collection | ✅ Working | ✅ Working  | ✅ Working  | <https://wellcomecollection.org/works/an4bpesp/items> | IIIF | Wellcome uses IIIF extensively. |

---

## Known-good direct tile URLs (for debugging)

These bypass the "find the manifest" problem — useful for testing dezoomify-rs itself.

| URL | Type | Notes |
|-----|------|-------|
| <https://manifests.collections.yale.edu/ycba/obj/5005> | IIIF manifest | Yale YCBA. Used in original test script. Not a collection page. |
| <https://content.ngv.vic.gov.au/col-images/zooms/Fd104934/ImageProperties.xml> | Zoomify | NGV Constable. Untested. |

---

## Testing workflow

### For each URL, run:

```zsh
# 1. Try dezoomify-rs directly with the page URL
dezoomify-rs "{URL}" /tmp/test_output.jpg

# 2. If that fails, check what the extension would find:
#    Open the page in browser with dezoomify-extension active
#    Note what URLs it detects

# 3. View page source / network inspector for:
#    - IIIF: info.json or manifest.json URLs
#    - Zoomify: ImageProperties.xml or TileGroup paths
#    - DeepZoom: .dzi file URLs
#    - Micrio: iiif.micr.io/{ID} patterns
#    - OpenSeadragon config objects
#    - Any other tile URL patterns

# 4. If a tile URL is found, test it directly:
dezoomify-rs "{TILE_URL}" /tmp/test_output.jpg

# 5. Update this file with results
```

### Recording results

When testing, update the table and add to Notes:
- What tile technology the site uses (IIIF, Zoomify, DeepZoom, Micrio, OpenSeadragon, etc.)
- Whether the tile URL is discoverable from page source (static HTML) or only via JS execution
- The direct tile/manifest URL if found
- Any Referer or auth headers needed

## Notes

### rijksmuseum.nl (2 May 2026)

**Tile tech**: IIIF via Micrio (iiif.micr.io)
**Tile URL discoverable from HTML?**: Yes — `iiif.micr.io/{SHORTCODE}` appears in page source for related works
**Direct tile URL pattern**: `https://iiif.micr.io/{SHORTCODE}/info.json`
**Referer needed?**: Unknown
**Existing dezoomer?**: dezoomify-rs IIIF (once you have the info.json URL)
**Recommended fix approach**: Scraper — extract Micrio shortcode from page HTML, construct info.json URL
**Notes**: Shortcode is not derivable from the collection page URL. Need to parse page source.

### ngv.vic.gov.au (2 May 2026)

**Tile tech**: Zoomify
**Tile URL discoverable from HTML?**: Likely yes — found via network inspector
**Direct tile URL pattern**: `https://content.ngv.vic.gov.au/col-images/zooms/{ID}/ImageProperties.xml`
**Referer needed?**: Unknown
**Existing dezoomer?**: dezoomify-rs Zoomify (once you have the ImageProperties.xml URL)
**Recommended fix approach**: Scraper — extract Zoomify base URL from page source
**Notes**: Image ID (e.g. `Fd104934`) doesn't correlate with collection page URL (`/work/3867/`).

