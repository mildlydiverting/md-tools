# md-tools Project Summary
*Generated 2026-06-18 from 48 Cowork sessions*

---

## 1. Drawing Teaching Knowledge Base (dt-knowledge-base)

A structured Obsidian vault of drawing exercises extracted from teaching books, cross-referenced with artist data, linked to learning outcomes, and supporting a skill-based teaching assistant.

### Sub-areas

- **Book extraction pipeline** — exercises extracted chapter-by-chapter from Kaupelis (*Experimental Drawing*, *Life Drawing*), Mattesi (*FORCE*), Tyler, Emily Ball, Bargue, Spicer, Woods, and Nicolaides; each exercise written to a 9-section template in Kim's voice with a maximum of 2 copyright quotes
- **Exercise catalogue** — `catalogue.yaml` tracking 272 exercises / 10 books / 87 artists across themes and clusters; with ILOs, descriptions, and wikilinks between related exercises
- **Artist LOD verification** — `lod-lookup.yaml` matching artist files to Wikidata Q numbers and Getty ULAN IDs; ongoing verification sweep; artist pages with biography, teaching notes, and Eagle links
- **Schema and workflow documentation** — `SCHEMA.md`, `WORKFLOW.md`, `HANDOFF.md`, `LOG.md` maintained across sessions to support cold-start by any model
- **Teaching skill prompts** — `skill/prompts/situation.md`, `adapt.md`, `diagnose.md` for contextual exercise recommendations and student diagnosis; `skill/SKILL.md` governing defaults and behaviour
- **ILO and description enrichment** — all 142 exercises given intended learning outcomes and one-sentence descriptions; paragraph-break convention enforced
- **Linking pass** — wikilinks between exercise files; cross-references to artist and source files
- **Pedagogy materials** — early-stage collection of QAA descriptors, Fink's taxonomy, and Schön/Kolb to underpin the teaching skill
- **Python scripts and venv** — `convert-folder-smart.py` (v1.1), OCR pipeline, requirements.txt with annotated dependencies

### Chats

[Build drawing instruction knowledge base](local://local_9ce0abaf-21e3-4391-9d08-3968dcc591f6) · [Next steps for drawing knowledge base](local://local_faf18099-49cb-4154-9504-c2eed423cced) · [Work status check](local://local_cf0366d4-bb02-42c9-8176-22eddfc9c8db) · [Mattesi FORCE extraction Chapter 1](local://local_502a6e01-aa90-4009-acc8-8472325496d5) · [Mattesi FORCE Chapter 2 extraction](local://local_081a265d-dc89-4898-bee2-91d3678d405d) · [Mattesi Chapter 3 extraction](local://local_40f1f797-27b7-4bab-b79b-7fa55b0b761d) · [Handoff next tasks](local://local_32ef6f0b-3114-4707-b6ed-fea52259302c) · [Kaupelis extraction or bulk convert](local://local_3743cee1-05ca-461d-af0c-38e742a9c251) · [Kaupelis extraction (Ch5)](local://local_5f38307b-76e1-4c4f-8b3e-552c37202e09) · [Kaupelis extraction (Ch6)](local://local_db10e23e-0532-4fbf-8617-56a41f32b0da) · [Kaupelis chapter 7 extraction](local://local_aa8faeb6-4a7f-48a5-b4b7-f9bdc60f12be) · [Kaupelis chapter extraction](local://local_132838d8-2c2d-4977-a0b3-1a56a624940a) · [Kaupelis extraction next steps](local://local_67c759a7-fc7d-47c0-b150-275bf783357c) · [Next book extraction planning](local://local_1276ff77-a8ab-405d-bea6-c316e8320899) · [Book extraction workflow setup](local://local_29ac9304-8d48-4d98-b4cc-435ab3548510) · [Linking pass review](local://local_366296de-f592-4be3-9953-aa7f6046077b) · [Exercise descriptions draft](local://local_a54acc86-c991-4a42-99c2-e752a8d76406) · [Drawing knowledge base work](local://local_a0214c07-7f2f-4e93-90d8-be90eb00b055) · [Drawing knowledge base setup](local://local_6ddfd7fa-ed9f-4044-86cb-822c3b6bcea2) · [Artist data enrichment](local://local_ff7f16c0-418c-4f1d-ae41-d87ed6e297f4) · [Book conversion status](local://local_ae0eb8f1-825f-4d9e-aa8a-ec50626ef3b9) · [Book extraction workflow](local://local_bd58df74-6d09-4d2c-b61e-84159e360345) · [Exercise extraction next steps](local://local_63b2d784-233e-4114-92f5-178e8bc8c1e6) · [Artist pages Eagle Links](local://local_67803832-0c2b-44a4-b4e1-1be22f714e7b) · [Artist database pages](local://local_6fbdaed4-fd1b-4100-897c-609bea36b972) · [Start next book project](local://local_d22724a1-2725-4da3-9d7e-561d04355bc8) · [Virtual environment package audit](local://local_7bc3bd7e-e2b7-4841-8bf0-c55666a3069a) · [Code lint and cleanup](local://local_9f5e8be7-d032-4fa1-bf69-f5f163820381) · [Project skill design discussion](local://local_d24e0b4e-8f3c-4199-953f-dd20c73e9ad9) · [Continue teaching materials test](local://local_905681b3-0d2a-4e92-b358-da62aa36a85b)

### Todo

1. Complete the remaining Kaupelis chapters (Ch8 and, if confirmed exercise-bearing, Ch6 Marks/Media) — scope with Kim first.
2. Run a LOD verification sweep for all artists still marked `links_status: unverified` in `lod-lookup.yaml`, working through the priority list in HANDOFF.
3. Source the four pedagogy documents (QAA descriptors, Fink, Schön/Kolb, cross-discipline ILOs) and build out the teaching skill properly.

---

## 2. MD Design System (md-tools / md-design-system)

A CSS design system built from typographic and colour tokens derived from a curated set of reference websites, supporting a markdown-first publishing workflow.

### Sub-areas

- **Token inventory** — colour, type, and spacing tokens extracted from 14 reference sites
- **Theme files** — 14 named themes (default, lapolice, alvarodelara, fluxish, gardenernyc, etc.) each with their own CSS custom property overrides
- **CSS build** — `main.css` compiled from tokens; WCAG AA contrast enforced across all themes; background colour fixes applied to 6 themes
- **Style guide / demo pages** — HTML demo pages including a calendar page and a full article page (PAGE 11) exercising all prose components in Kim's voice
- **Theme tester** — interactive tool for switching between themes; ROM font fallbacks corrected

### Chats

[MD design system briefing](local://local_38d5e2c1-76fb-4265-ab5d-ad58756b92ea) · [md-design-system CSS build](local://local_a6fde83e-08e2-4dbe-9540-1dd51231922b) · [Design system theme tester](local://local_a351ea48-6722-4971-80d4-c6dbe9f09cf9) · [Markdown design system calendar](local://local_12dbe1c0-fd09-4323-b6c9-f90c7acf81e8)

### Todo

1. Build step 5 (main.css) using the token inventory and prototype as source — see the ready-to-paste prompt in `handoff.md`.
2. Review the six corrected themes (alvarodelara, fluxish, gardenernyc, criticalmedialab, handmadeweb, fragmentlv) in the browser to confirm they feel right.
3. Extend the style guide with further page types beyond the calendar and article demos.

---

## 3. Are.na Toolkit

A set of web tools for working with the Are.na platform — a slideshow generator, colour palette extractor, and a landing page — all hosted as static HTML.

### Sub-areas

- **Arena Hypernormalisation slideshow** — auto-advancing fullscreen slideshow fed by Are.na channel content; features hard-cut transitions, blocklist, alt text, music (muted by default), cache/pool refresh, and per-entry cache purge
- **Arena palette tool** — extracts and displays a colour palette from an Are.na channel; colour label patch logic (debugging in progress)
- **Are.na tools landing page** — static index listing all tools; UI improvements (borders removed, fonts enlarged, link colours fixed)
- **README and HANDOFF** — documentation written at launch

### Chats

[Build drawing instruction knowledge base](local://local_9ce0abaf-21e3-4391-9d08-3968dcc591f6) · [Arena hypernormalisation tool](local://local_bf182ddb-6cf5-401e-ab9b-b96509380157) · [Arena palette updates](local://local_79054343-00bb-4a04-bf1f-6f9c16857c2c) · [Are.na tools landing page](local://local_7a133f7f-e50b-4535-907f-c0d5047d98e0) · [Arena hypernormalisation blacklist](local://local_b89cece0-3cf1-4f22-b3c0-6b0ac34bed3d) · [Arena tools launch updates](local://local_846953cc-964e-4d5d-8845-d84b3a25d35f)

### Todo

1. Fix the Arena palette color label bug: revert `hex.slice(1)` to `hex` and reach legend nodes via `btn.dataset.hex` — the fix is documented in the session transcript.
2. Push the updated `docs/arena-hypernormalisation.html` to the live repo.
3. Test the pool refresh and per-entry cache purge controls in a real browsing session.

---

## 4. Drawing Biennial 2026 (Drawing Room)

Managing artist data and images for the Drawing Room's Drawing Biennial 2026 — ingesting artwork information into Eagle and converting markdown files to a structured Obsidian format.

### Sub-areas

- **Markdown file conversion** — 314 artist/artwork markdown files updated with YAML frontmatter (title, artist, year, medium, Eagle folder/item), image embeds, and structured sections
- **Eagle image ingest** — artwork images ingested into Eagle with metadata; `eagle_ingest_log.csv` tracking Eagle folder and item IDs
- **Drawing Room biennial downloads** — attempted automated image download from biennial.drawingroom.org.uk; blocked by Cowork network policy

### Chats

[Drawing biennial image ingest](local://local_ad9e6990-68a0-481c-8228-1b3ffcb0b6ca) · [Drawing Room biennial downloads](local://local_f090dd0a-54e5-4fa2-9f09-f1ae6dc81f1f)

### Todo

1. Add `biennial.drawingroom.org.uk` and `drawingcdn.azureedge.net` to Admin → Capabilities → Network access, then retry the automated download session.
2. Spot-check a sample of the converted markdown files in Obsidian to confirm frontmatter and image embeds rendered correctly.
3. Add Eagle links to any artist files in the knowledge base that appeared in the biennial.

---

## 5. Utility Scripts and Infrastructure

File management scripts, conversion tools, and general housekeeping across the projects.

### Sub-areas

- **File date prepend script** — shell script and Automator Quick Action to prepend file creation dates to filenames in Finder
- **Book conversion scripts** — `convert-folder-smart.py` v1.1 converting EPUBs, PDFs, and HTML to markdown via markitdown-ocr and Tesseract; logs to EXTRACTION-LOG.md
- **Handwritten notes conversion** — script using the Anthropic API to convert handwritten note images to markdown (API key issue resolved)
- **Development notes organisation** — 18 Obsidian development notes reorganised into project subfolders
- **Git infrastructure** — resolved index.lock issue in dt-knowledge-base; managed commits across sessions

### Chats

[File date prepend script](local://local_29c45a66-572d-4147-a643-5f4fc9fcb2bc) · [Book extraction workflow setup](local://local_29ac9304-8d48-4d98-b4cc-435ab3548510) · [Development notes frontmatter](local://local_f564eed6-e3ac-4c6a-be81-acfc9a288a32) · [Convert handwritten notes to markdown files](local://local_9725b3f9-708c-4cbe-9bf6-f7e668bf37e6) · [Code lint and cleanup](local://local_9f5e8be7-d032-4fa1-bf69-f5f163820381)

### Todo

1. Set up the File date prepend script as an Automator Quick Action using the delivered shell script.
2. Run the remaining 36 large PDFs through `convert-folder-smart.py` locally (not in the sandbox) to avoid the per-call time limit.
3. Rename the `#LLM Knowledge Bases` Obsidian note to remove the `#` prefix to avoid tag conflicts.

---

## 6. Teaching and Practice

One-off sessions related to Kim's life drawing teaching practice, personal writing, and cultural work — not tied to a specific codebase.

### Sub-areas

- **Life class planning** — quick ideation for session formats (long pose, continuous tone, negative space)
- **Tone of voice guide** — comprehensive document covering three registers (reflective, accessible/instructional, official/client); before/after examples; Claude-specific prompting guidance; pulled from newsletters, statements, and website
- **Cultural education document analysis** — analysed documents on place, cultural practice, and community arts; produced a five-slide presentation structure on place-making for a cultural education context
- **Teaching skill materials** — identified four pedagogy documents needed to build the teaching skill (QAA, Fink, Schön/Kolb, cross-discipline ILOs)

### Chats

[Life class ideas](local://local_5301e068-9dd6-4ef0-9f56-4f2469299148) · [Kim's tone of voice guide](local://local_c1f114d0-97a6-47ab-948a-21e66f4eb3d5) · [Analyze cultural education documents for patterns](local://local_7b974585-c24f-4ad3-b135-717ac59e66eb) · [Continue teaching materials test](local://local_905681b3-0d2a-4e92-b358-da62aa36a85b)

### Todo

1. Use the five-slide presentation structure from the cultural education session as a basis for a funding narrative or keynote.
2. Source the four pedagogy documents flagged in HANDOFF (QAA descriptors, Fink's *Creating Significant Learning Experiences*, a Schön or Kolb primary source, cross-discipline ILO examples) and drop them into the pedagogy folder.
3. Use the tone of voice guide's efficient prompt version (~180 tokens) as the default when working in long threads with Claude.

---

*Notes on ambiguity:*

- **Session URLs** — these are local Cowork sessions, not claude.ai web chat IDs. The `local://` links in this document and the CSV are identifiers within the Cowork session store, not navigable URLs. There is no direct mapping to `https://claude.ai/chat/{id}`.
- **Timestamps** — the session list API does not return creation or modification timestamps. Dates in the CSV are approximated from context clues in the transcripts and the session order (most-recent first). They should be treated as indicative rather than precise.
- **"Project" scope** — the connected folder is `md-tools`, but the work spans at least four separate git repositories (md-tools, dt-knowledge-base, are.na-toolkit, and the Drawing Biennial folder). The `project` column in the CSV uses `md-tools` throughout to reflect the Cowork project context, not the individual repo.
- **Four duplicate sessions** titled "Project chat index and summary" (running at time of writing) are excluded — they are earlier attempts at this current task.
