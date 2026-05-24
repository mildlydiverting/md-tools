# Canonical Metadata Mapping
## Image reference tools — Kim Plowright, 2026

The canonical record is the JSON sidecar file written alongside each downloaded image.
All sources map *into* this schema; all destinations map *out of* it.
Fields marked ⚠️ are consistently missing or unreliable in practice.

---

## Canonical fields

| Field | Type | Notes |
|---|---|---|
| `photo_id` | string | Source-native ID |
| `title` | string | |
| `creator` | string | Person or org name |
| `creator_url` | string | Profile or authority page |
| `creator_wikidata_qid` | string | e.g. Q5599 — enrichment via Wikidata |
| `creator_ulan_id` | string | Getty ULAN — enrichment ⚠️ |
| `date_created` | string | ISO 8601 or partial (1952, 1952-06) |
| `date_created_granularity` | int | Flickr-style: 0=exact, 4=month, 6=year, 8=circa |
| `date_posted` | string | When uploaded to source platform |
| `date_accessed` | string | ISO 8601 datetime |
| `medium` | string | e.g. "Oil on canvas", "Photograph" ⚠️ |
| `dimensions` | string | e.g. "24 × 36 cm" ⚠️ |
| `description` | string | May contain HTML |
| `description_format` | string | "html" or "plain" |
| `tags` | array[string] | Source tags, unnormalised |
| `tags_normalised` | array[string] | Your ontology-aligned tags (added by you) |
| `institution` | string | Holding institution ⚠️ |
| `institution_location` | string | City, Country ⚠️ |
| `accession_number` | string | Museum object number ⚠️ |
| `website` | string | Platform name e.g. "Flickr", "Wikimedia Commons" |
| `website_url` | string | Platform root URL |
| `source_url` | string | Canonical URL of the source page |
| `image_url` | string | Direct URL to downloaded image file |
| `image_size_label` | string | e.g. "Large 2048" |
| `license_id` | string | Source-native ID (Flickr integer, SPDX, etc.) |
| `license_name` | string | Human-readable e.g. "CC BY 2.0" |
| `license_url` | string | ⚠️ absent from most institution sites |
| `copyright_line` | string | Free-text rights statement if no structured licence |
| `tasl` | string | Title / Author / Source / Licence — formatted string |
| `citation_markdown` | string | Full citation in Markdown |
| `gallery` | object | Source gallery/collection context (see below) |
| `location` | object | Geographic location of subject (see below) |
| `wikidata_qid` | string | Wikidata Q-number for the *artwork* ⚠️ |
| `iiif_manifest_url` | string | IIIF manifest if available ⚠️ |
| `obsidian_note_path` | string | Vault-relative path of linked Obsidian note |
| `eagle_item_id` | string | Eagle item ID once imported |
| `arena_block_id` | string | Are.na block ID once posted |

### gallery sub-object
```json
{
  "gallery_id": "72157723831831179",
  "title": "Drawing References",
  "gallery_url": "https://www.flickr.com/photos/.../galleries/..."
}
```

### location sub-object
```json
{
  "latitude": 51.5,
  "longitude": -0.1,
  "locality": "London",
  "region": "England",
  "country": "United Kingdom"
}
```

---

## Source mappings (what each source provides)

### Flickr (API)
| Canonical field | Flickr API field | Notes |
|---|---|---|
| `photo_id` | `photo.id` | |
| `title` | `photo.title._content` | |
| `creator` | `photo.owner.realname` or `username` | |
| `creator_url` | `https://flickr.com/photos/{nsid}/` | |
| `date_created` | `photo.dates.taken` | |
| `date_created_granularity` | `photo.dates.takengranularity` | |
| `date_posted` | `photo.dates.posted` | Unix timestamp |
| `description` | `photo.description._content` | May be HTML |
| `tags` | `photo.tags.tag[].raw` | |
| `source_url` | `https://flickr.com/photos/{nsid}/{id}` | |
| `license_id` | `photo.license` | Integer 0–10 |
| `license_name` | lookup table | See FLICKR_LICENSES in script |
| `license_url` | lookup table | |
| `location` | `photo.location` | If geo-tagged |
| `medium` | — | ⚠️ not available |
| `dimensions` | — | ⚠️ not available |
| `institution` | — | ⚠️ not available |

### Wikimedia Commons (best in class)
| Canonical field | Source | Notes |
|---|---|---|
| `title` | SDC file info table / JSON-LD `name` | |
| `creator` | SDC file info table `creator` | |
| `creator_wikidata_qid` | SDC Wikidata link | e.g. Q5599 |
| `date_created` | SDC file info table `date` | |
| `medium` | SDC file info table `medium` | ✅ |
| `dimensions` | SDC file info table `dimensions` | ✅ |
| `institution` | SDC file info table `institution` | ✅ |
| `license_name` | `<link rel="license">` | ✅ |
| `license_url` | `<link rel="license" href>` | ✅ |
| `wikidata_qid` | SDC `P6243` (digital representation of) | |
| `iiif_manifest_url` | `<link rel="alternate">` | ✅ |
| `image_url` | JSON-LD `contentUrl` | |

### Art Institute of Chicago (HTML Microdata + API)
| Canonical field | Source | Notes |
|---|---|---|
| `title` | `itemprop="name"` | |
| `creator` | `itemprop="creator"` | |
| `date_created` | `itemprop="dateCreated"` | |
| `medium` | `itemprop="material"` | ✅ via Microdata |
| `dimensions` | `itemprop="size"` | ✅ via Microdata |
| `accession_number` | `itemprop="identifier"` | |
| `institution` | `itemprop="provider"` | |
| `license_name` | — | ⚠️ absent from markup; check AIC API |
| `iiif_manifest_url` | AIC API / page source | ✅ |

### British Museum / Harvard (dt/dd lists)
| Canonical field | Source | Notes |
|---|---|---|
| `title` | `<dd>` matching `<dt>Title` | |
| `creator` | `<dd>` matching `<dt>Producer/People` | |
| `date_created` | `<dd>` matching `<dt>Production date/Date` | |
| `medium` | `<dd>` matching `<dt>Materials/Medium` | ✅ |
| `dimensions` | `<dd>` matching `<dt>Dimensions` | ✅ |
| `accession_number` | `<dd>` matching `<dt>Museum number/Object number` | |
| `license_name` | — | ⚠️ absent |

### Are.na (API)
| Canonical field | Are.na API field | Notes |
|---|---|---|
| `photo_id` | `block.id` | |
| `title` | `block.title` | Often empty |
| `description` | `block.description.plain` | |
| `source_url` | `block.source.url` | |
| `creator` | `block.user.username` | Person who added it, not the artwork creator |
| `date_posted` | `block.created_at` | |
| `image_url` | `block.image.original.src` | |
| `tags` | — | ⚠️ Are.na has no tags on blocks |
| `license_name` | — | ⚠️ not available |

### Museum APIs (Met, AIC, Harvard — for API fallback enrichment)
| Canonical field | Met API field | AIC API field | Harvard API field |
|---|---|---|---|
| `title` | `title` | `title` | `title` |
| `creator` | `artistDisplayName` | `artist_display` | `people[].name` |
| `date_created` | `objectDate` | `date_display` | `dated` |
| `medium` | `medium` | `medium_display` | `technique` |
| `dimensions` | `dimensions` | `dimensions` | `dimensions` |
| `accession_number` | `accessionNumber` | `main_reference_number` | `accessionNumber` |
| `license_name` | `rightsAndReproduction` | `license_text` | `copyright` |
| `wikidata_qid` | — | — | via `sameAs` |
| `iiif_manifest_url` | `isHighlight` (linked) | `/api/v1/artworks/{id}` | `iiif_manifest` |

---

## Destination mappings (what each destination can receive)

### Eagle (Web API v2 / Plugin API)
| Canonical field | Eagle field | Method | Notes |
|---|---|---|---|
| `title` | `name` | API / Plugin | |
| `source_url` | `website` | API / Plugin | Shown as source link |
| `tags` + `tags_normalised` | `tags` | API / Plugin | Merge both arrays |
| `citation_markdown` | `annotation` | API / Plugin | Primary use of annotation |
| `tasl` | `annotation` (appended) | API / Plugin | |
| `gallery.title` | `folders` | API | Map to Eagle folder by name |
| `creator`, `date_created`, `license_name`, `medium`, `dimensions`, `institution` | `annotation` (as YAML block) | Plugin | Full structured block |
| `eagle_item_id` | — | write back to JSON | Record after import |

**Annotation structure** (stored as a YAML block in the annotation field):
```yaml
creator: Josef Sudek
date_created: 1952
medium: Photograph
institution: ~
license: CC BY 2.0
license_url: https://creativecommons.org/licenses/by/2.0/
source: https://www.flickr.com/photos/.../
tasl: "[Title](url) — [Creator](url) — [CC BY 2.0](url)"
citation: "Sudek, J. (1952). _Window_. Available at https://... (Accessed 24 May 2026)."
obsidian_note: Reference/Drawing/Sudek-window.md
```

### Are.na (API v3)
| Canonical field | Are.na field | Notes |
|---|---|---|
| `title` | `title` | |
| `description` + TASL | `description` | Combine: description + formatted attribution |
| `source_url` | `source_url` | |
| `image_url` | Upload as attachment | |

### Obsidian (frontmatter YAML)
| Canonical field | Frontmatter key | Notes |
|---|---|---|
| `title` | `title` | |
| `creator` | `artist` | |
| `date_created` | `date_created` | |
| `medium` | `medium` | |
| `institution` | `institution` | |
| `license_name` | `license` | |
| `source_url` | `source` | |
| `eagle_item_id` | `eagle_id` | Link back to Eagle |
| `arena_block_id` | `arena_block` | Link back to Are.na |
| `tags_normalised` | `tags` | Use your tag ontology |
| `citation_markdown` | `citation` | |

### Pinboard
| Canonical field | Pinboard field | Notes |
|---|---|---|
| `source_url` | `url` | |
| `title` | `description` | |
| `creator` + `institution` | `extended` | Free text notes |
| `tags_normalised` | `tags` | Space-separated, max 100 |

---

## Schema.org alignment

Where our canonical fields map to `schema.org/VisualArtwork` (used by nobody in practice, but worth knowing):

| Canonical field | schema.org property |
|---|---|
| `title` | `name` |
| `creator` | `creator` / `author` |
| `date_created` | `dateCreated` |
| `medium` | `artMedium` |
| `dimensions` | `width`, `height`, `depth` |
| `institution` | `locationCreated` / `contentLocation` |
| `accession_number` | `identifier` |
| `license_url` | `license` |
| `description` | `description` |
| `image_url` | `image` / `contentUrl` |

Also relevant: `schema.org/ImageObject` for the digital surrogate (distinct from the artwork itself — the Wikimedia Commons distinction noted in the structured data audit).

---

## Wikidata enrichment paths

If a `wikidata_qid` is known (from Wikimedia Commons SDC or a `sameAs` link), you can enrich:
- `creator_wikidata_qid` → ULAN, VIAF, ISNI, LCCN via `owl:sameAs`
- `creator_ulan_id` → Getty ULAN SPARQL endpoint for biography, nationality, life dates
- `institution` → Q-number → institution name, location, website
- Artwork type → `schema.org` subtype (Painting, Drawing, Sculpture, Photograph)

SPARQL endpoint: `https://query.wikidata.org/sparql`
Getty LOD: `https://vocab.getty.edu/sparql`

---

## Open questions / deferred decisions

- `tags_normalised`: applying your tag ontology (`@` people, `#` topics, `col:`, `project:`, `class:`) is a manual or semi-manual step — needs a normalisation pass, not an automatic one
- `medium` and `dimensions` are absent from Flickr entirely — consider a manual enrichment field in the JSON
- Obsidian ↔ Eagle link: best maintained via `eagle_item_id` in Obsidian frontmatter + `obsidian_note_path` in Eagle annotation YAML — needs a sync script
- Are.na post-back: write a separate `arena_upload.py` that reads the canonical JSON and constructs the block
- LIDO and Europeana EDM are comprehensive museum standards but probably overkill for personal use — worth knowing for cross-referencing institution APIs
