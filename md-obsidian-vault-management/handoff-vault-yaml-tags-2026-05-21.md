# Handoff: art-reference vault — YAML cleanup + tag consolidation

## Context
- **Vault**: `/Users/kimplowright/Library/Mobile Documents/iCloud~md~obsidian/Documents/art-reference`
- **Script**: `fix_yaml_frontmatter.py` v1.1 — saved in `md-obsidian-vault-management` working dir
- **Session date**: 2026-05-21

## What we did this session

### YAML frontmatter fix — COMPLETE ✓
Fixed 508 files across `obsidian-art-inbox` (all subfolders). The `yarle` and `yarle 2` folders were untouched.

Fixes applied:
1. `creation_date` / `modification_date` → `created` / `modified`
2. Human-readable dates (`June 26, 2022`) → ISO 8601 (`2022-06-26`)
3. Trailing colons stripped from title values
4. Invalid timezone suffixes stripped (`2025-08-07T11:46:13 (UTC +01:00)` → `2025-08-07T11:46:13+01:00`)
5. Unclosed opening quotes fixed in title values
6. Mid-value colons in titles quoted (`EXERCISE: FIVE-STAR` → `"EXERCISE: FIVE-STAR"`)

Dataview bad-YAML table now returns 0 rows.

### Deferred / not yet done
- **`yarle-test-1` and `yarle 2` folders**: not audited. May have their own YAML issues — unknown.
- **`Corona` → `Corita` filename typo**: `2022-11-13-Corona Kent Teachings from the Heart P48.md` — title is correct (`Corita Kent`), filename needs renaming. Use Obsidian CLI to preserve wikilinks: `obsidian rename file="Corona Kent Teachings from the Heart P48" name="2022-11-13-Corita Kent Teachings from the Heart P48"`
- **`Exercise 1` unclosed-quote filename**: `2023-04-28-"Exercise 1- The 'Conversation' Exercise.md` — the filename itself has a leading quote. May need renaming separately from the YAML fix.

---

## Tag consolidation — NOT YET STARTED

### Source data
- `art-refernce-vault_tags.csv` — frontmatter tags from the vault (Obsidian `tags:` arrays)
- `tags.txt` — inline hashtags from `obsidian tags sort=count counts`

### Three distinct populations mixed together
| Source | Style | Volume |
|---|---|---|
| Pinterest/IFTTT/Zapier imports | camelCase Instagram hashtags | ~1000+ unique, mostly count=1 |
| Your own tags | hyphenated, conceptual | moderate count, higher frequency |
| Frontmatter YAML tags | mixed case, some scraped artefacts | ~250 in CSV |

### Agreed tag schema (prefix system)
- `@` — people and organisations
- `#` — topics (no prefix in Obsidian, just the tag)
- `col:` — colour
- `project:` — projects
- `class:` — classification
- `src:` — publications, platforms, sources *(new, agreed this session)*
- `series:` — sequential series *(new, agreed this session)*

Note: existing deliberate frontmatter keys (`source`, `source-url`, `pinterest-board`, `pinterest-link`, `evernote-notebook`) are **kept as-is** — not migrated to `src:` tags.

### Consolidation work still to do

**Priority 1 — case duplicates (straightforward)**
Lowercase wins in all cases:
- `art` + `Art` → `art`
- `artists` + `Artists` → `artists`
- `Culture` + `culture` → `culture`
- `film` + `Film` → `film`
- `music` + `Music` → `music`
- `Science` + `science` → `science`
- `illustration` + `Illustration` → `illustration`

**Priority 2 — source fragmentation (needs `src:` prefix)**
- `dazed`, `dazed+confused`, `dazed-&-confused`, `dazed-&-confused-magazine`, `dazed-and-confused`, `dazed-and-confused-magazine`, `dazeddigital` → `src:dazed`
- `artnet-news` → `src:artnet`
- `the-gentlewoman` → `src:the-gentlewoman`
- `guardian-guide-to-painting` (count 50 inline tag) → `series:guardian-guide-to-painting`

**Priority 3 — series tags**
- `line-by-line` (count 12) → keep as `series:line-by-line` + add `src:nyt`
- `guardian-guide-to-painting` (count 50) → `series:guardian-guide-to-painting` + `src:guardian`
- `gridsgestures` (count 5) — check if this is a series

**Priority 4 — junk/artefact tags to delete**
- `disable-inline-signup-unit`
- `pinterest-bulk-downloader`, `pinterest-image-downloader`, `pinterest-video-downloader`
- `wfdownloader-app`
- `_featured`
- `Uncategorized`
- The monstrous `composition-rhythm-artists-painting-portrait...` tag (line 56 of CSV)
- `#ifttt` (count 9872), `#zapier` (count 4870), `#pinterest` (count 11347) — Pinterest import noise; consider bulk-deleting or moving to `src:` namespace

**Priority 5 — cybernetics cluster (well-formed, may just need case normalisation)**
All already hyphenated and lowercase. Check whether any need `@` prefix for people:
`humberto-maturana`, `francisco-varela`, `gordon-pask`, `heinz-von-foerster`, `ross-ashby`, `warren-mcculloch`, `john-von-neumann`, `norbert-wiener`, `gregory-bateson`, `margaret-mead` → consider `@` prefix for all

### Approach for tag changes
Use Obsidian CLI to avoid manual edits:
```bash
# Example: rename a tag across vault
obsidian vault="art-reference" tags:rename old="Art" new="art"
```
Check `obsidian help` for exact tag command syntax — may need `tag:rename` or similar.
**Do not bulk-edit tag arrays in frontmatter directly** — use CLI so Obsidian tracks the changes.

---

## Files to attach next session
- [ ] `fix_yaml_frontmatter.py` v1.1 (already in working dir)
- [ ] This handoff note
- [ ] Fresh `obsidian tags sort=count counts` output after any tag changes
