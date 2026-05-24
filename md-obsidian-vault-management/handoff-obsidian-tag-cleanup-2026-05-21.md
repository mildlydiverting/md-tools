# Handoff: Obsidian Vault — Tag Cleanup & Controlled Vocabulary

## Context
- **Vault**: `/Users/kimplowright/Library/CloudStorage/Dropbox/obsidian/obsidian vault`
- **Repos**: None — scripts live locally, not yet committed
- **Session date**: 2026-05-21

## What we did this session

### 1. Connected Obsidian MCP
- Installed the Local REST API & MCP Server plugin in Obsidian
- Configured Claude Desktop (`claude_desktop_config.json`) with `mcp-remote` bridge
- MCP connects via HTTP on port 27123 (HTTP rather than HTTPS to avoid cert issues)
- Note: vault lives on Dropbox, which caused read timeouts throughout — scripts run locally are more reliable than MCP reads for bulk operations

### 2. Fixed .md.txt files
- Renamed double-extension files using Terminal one-liner:
  ```bash
  find "/path/to/vault" -name "*.md.txt" | while read f; do mv "$f" "${f%.txt}"; done
  ```

### 3. Fixed spaced tags → kebab-case
- Script: `fix_obsidian_tags.py`
- Ran dry-run, then applied to all 1,264 files
- Handles both list-style and inline YAML tag formats

### 4. Extracted full tag list
- Script: `extract_vault_tags.py`
- Output: `vault_tags.csv` (2,290 unique tags)

### 5. Built controlled vocabulary
- Analysed full tag list and designed ~36 canonical clusters
- Key clusters: `embroidery`, `quilting`, `visible-mending`, `textile-art`,
  `japanese-textiles`, `sewing`, `knitting-crochet`, `weaving`, `cross-stitch`,
  `lace-needlework`, `soft-toys-dolls`, `collage-mixed-media`, `artists-makers`,
  `colour`, `pattern`, `drawing`, `illustration`, `painting`, `clothing-costume`,
  `interiors`, `textile-history`, `art-education`, `craft`, `book-arts`,
  `wall-art-installation`, `typography-lettering`, `printing-dyeing`,
  `nature-botanical`, `masks`, `folk-global-art`, `process-creativity`,
  `digital-art`, `product-management`, `design`, `photography`
- Fibre clusters split individually: `wool`, `linen`, `silk`, `cotton`, `fabric`
- Sub-tags preserved within clusters, e.g.:
  - embroidery: `hardanger`, `goldwork`, `blackwork`, `cross-stitch`, `needlepoint`, `vintage`, `japanese`, `korean`
  - quilting: `gees-bend`, `amish-quilt`, `improv-quilt`, `boro-sashiko`, `abstract-quilt`, `modern-quilting`, `log-cabin`, `strip-piecing`
  - japanese-textiles: `kimono`, `boro-sashiko`, `obi`
  - visible-mending: `darning`
  - artists-makers: individual artist name retained alongside cluster tag
- Files: `proposed_vocabulary.md`, `tag_mapping.csv` (1,942 mapping rules)

### 6. Applied mapping
- Script: `apply_tag_mapping.py`
- Reads `tag_mapping.csv` (old_tag → new_tags pipe-separated)
- Replaces and deduplicates tags in frontmatter
- Supports `--dry-run` and `--report` flags
- Applied successfully to vault

## Scripts produced (all in working directory)
| Script | Purpose |
|---|---|
| `fix_obsidian_tags.py` | Convert spaced tags to kebab-case |
| `extract_vault_tags.py` | Extract all unique tags with counts to CSV |
| `apply_tag_mapping.py` | Apply tag_mapping.csv to vault frontmatter |
| `tag_mapping.csv` | 1,942-rule mapping: old tag → new canonical tags |
| `proposed_vocabulary.md` | Human-readable vocabulary reference |
| `unassigned_tags_review.md` | ~675 tags not yet mapped, sorted for review |

## Known issues / deferred things
- **~675 tags not yet mapped** — see `unassigned_tags_review.md`. Roughly split:
  - ~200 should be added to existing clusters (missed in first pass)
  - ~50 could form 4 new clusters (nature-botanical, masks, folk-global-art, process-creativity) — these were added to the vocabulary but mapping rules not yet written for all of them
  - ~250 are noise/junk/place names — candidates for deletion
- **Pinterest files** — vault contains hundreds of Pinterest import notes, most named after webpage titles rather than content, with `(1)`, `(2)` etc. suffixes. Need renaming and consolidating. Deferred pending Dropbox stability.
- **Empty/stub files** — a number of 0-byte files exist (e.g. `12.md`). Some have backlinks; worth checking before deleting.
- **Dropbox instability** — MCP reads time out frequently. All bulk work should be done via local Python scripts, not MCP.
- **Tags not yet run through kebab fixer + mapping** — if new notes have been added since the session, re-run both scripts.

## What to do next session
1. Write mapping rules for the remaining ~200 legitimately useful unassigned tags
2. Decide which of the ~250 noise tags to delete outright (script needed: remove unmapped tags from all files)
3. Pinterest file audit: count boards, sample content, decide on rename/consolidate strategy
4. Consider a script to flag notes with no tags after mapping (orphan detection)
5. Commit scripts to `md-tools` repo

---
*Handoff generated: 2026-05-21*
