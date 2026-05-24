# Handoff: Obsidian vaults — YAML cleanup + tag consolidation

## Context
- **iCloud art vault**: `/Users/kimplowright/Library/Mobile Documents/iCloud~md~obsidian/Documents/art-reference`
- **Dropbox general vault**: `/Users/kimplowright/Library/CloudStorage/Dropbox/obsidian/obsidian vault`
- **Session date**: 2026-05-21

---

## Scripts

All three earlier scripts are superseded by **`fix_frontmatter.py` v1.0** — use this going forward.

| Script | Status |
|---|---|
| `fix_yaml_frontmatter.py` v1.1 | Superseded — keep for reference |
| `fix_yarle_frontmatter.py` v1.0 | Superseded — keep for reference |
| `fix_frontmatter.py` v1.0 | **Current** — use this |

### What `fix_frontmatter.py` fixes
1. `creation_date` / `created-at` → `created`
2. `modification_date` / `modified_date` / `last-updated-at` → `modified`
3. Human-readable dates (`June 26, 2022`) → ISO 8601 (`2022-06-26`)
4. Invalid timezone suffixes stripped (`2025-08-07T11:46:13 (UTC +01:00)` → `2025-08-07T11:46:13+01:00`)
5. Trailing colons stripped from title values
6. Mid-value colons in titles quoted (`EXERCISE: FIVE-STAR` → `"EXERCISE: FIVE-STAR"`)
7. Unclosed opening quotes fixed in title values
8. Yarle-style broken tags block (`tags:\n["#zapier"]`) → valid YAML list
9. Inline JSON tag arrays (`tags: ["#foo"]`) → valid YAML list, `#` prefixes stripped

Leaves alone: `source-url`, `pinterest-link`, `pinterest-board`, `evernote-notebook`

### Usage
```bash
# Default target: Dropbox vault / obsidian-general-to-import
python3 fix_frontmatter.py                  # dry run
python3 fix_frontmatter.py --write          # apply

# Override folder with --folder
python3 fix_frontmatter.py --folder "/Users/kimplowright/Library/Mobile Documents/iCloud~md~obsidian/Documents/art-reference/yarle 2"
python3 fix_frontmatter.py --folder "/Users/kimplowright/Library/Mobile Documents/iCloud~md~obsidian/Documents/art-reference/yarle-test-1"
```

---

## YAML cleanup status by folder

| Folder | Vault | Status |
|---|---|---|
| `obsidian-art-inbox` | iCloud art | ✅ Done — 508 files fixed |
| `yarle 2` | iCloud art | ⏳ Not yet run |
| `yarle-test-1` | iCloud art | ⏳ Not yet run |
| `obsidian-general-to-import` | Dropbox | ⏳ Not yet run — 278 files need fixing |

### Remaining filename issues (iCloud art vault)
- **`Corona` → `Corita` typo**: `obsidian-art-inbox/art - teaching - planning/2022-11-13-Corona Kent Teachings from the Heart P48.md` — title is already correct (`Corita Kent`), filename needs renaming. Use Obsidian CLI to preserve wikilinks:
  ```bash
  obsidian rename file="Corona Kent Teachings from the Heart P48" name="2022-11-13-Corita Kent Teachings from the Heart P48"
  ```
- **Unclosed-quote filename**: `obsidian-art-inbox/art - teaching - planning/2023-04-28-"Exercise 1- The 'Conversation' Exercise.md` — leading quote in filename needs renaming separately from the YAML fix.

---

## Tag consolidation — NOT YET STARTED

### Source data
- `art-refernce-vault_tags.csv` — frontmatter tags from the vault (Obsidian `tags:` arrays)
- `tags.txt` — inline hashtags from `obsidian tags sort=count counts`

### Three distinct tag populations
| Source | Style | Volume |
|---|---|---|
| Pinterest/IFTTT/Zapier imports | camelCase Instagram hashtags | ~1000+ unique, mostly count=1 |
| Your own tags | hyphenated, conceptual | moderate count, higher frequency |
| Frontmatter YAML tags | mixed case, some scraped artefacts | ~250 in CSV |

### Agreed tag schema (prefix system)
- `@` — people and organisations
- `#` — topics (bare tag, no prefix in Obsidian)
- `col:` — colour
- `project:` — personal projects
- `class:` — classification
- `src:` — publications, platforms, sources *(agreed this session)*
- `series:` — sequential article/content series *(agreed this session)*

Note: frontmatter keys `source`, `source-url`, `pinterest-board`, `pinterest-link`, `evernote-notebook` are **kept as-is** — not migrated to `src:` tags.

### Consolidation priorities

**1 — Case duplicates** (straightforward, lowercase wins)
- `art`/`Art` → `art`
- `artists`/`Artists` → `artists`
- `Culture`/`culture` → `culture`
- `film`/`Film` → `film`
- `music`/`Music` → `music`
- `Science`/`science` → `science`
- `illustration`/`Illustration` → `illustration`

**2 — Source fragmentation** (needs `src:` prefix)
- `dazed`, `dazed+confused`, `dazed-&-confused`, `dazed-&-confused-magazine`, `dazed-and-confused`, `dazed-and-confused-magazine`, `dazeddigital` → `src:dazed`
- `artnet-news` → `src:artnet`
- `the-gentlewoman` → `src:the-gentlewoman`

**3 — Series tags**
- `line-by-line` (count 12) → `series:line-by-line` + `src:nyt`
- `guardian-guide-to-painting` (count 50) → `series:guardian-guide-to-painting` + `src:guardian`
- `gridsgestures` (count 5) — check if this is a series before tagging

**4 — Junk/artefact tags to delete**
- `disable-inline-signup-unit`
- `pinterest-bulk-downloader`, `pinterest-image-downloader`, `pinterest-video-downloader`, `wfdownloader-app`
- `_featured`, `Uncategorized`
- The monstrous composition tag (line 56 of CSV)
- `ifttt` (count 9872), `zapier` (count 4870), `pinterest` (count 11347) — Pinterest import noise; bulk-delete or move to `src:` namespace

**5 — People tags** (cybernetics cluster — well-formed, consider `@` prefix)
`humberto-maturana`, `francisco-varela`, `gordon-pask`, `heinz-von-foerster`, `ross-ashby`, `warren-mcculloch`, `john-von-neumann`, `norbert-wiener`, `gregory-bateson`, `margaret-mead`

### Approach for tag changes
Use Obsidian CLI — do not bulk-edit frontmatter directly.
```bash
# Check exact syntax first
obsidian help tags
# Example rename
obsidian vault="art-reference" tags:rename old="Art" new="art"
```

---

## Files to attach next session
- [ ] `fix_frontmatter.py` v1.0
- [ ] This handoff note
- [ ] Fresh `obsidian tags sort=count counts` output after any tag changes
