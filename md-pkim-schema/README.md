# md-pkim-schema

The start of a home for the PKIM spec: one record schema, one vocabulary, shared by every tool.

**Status: proposed, not yet approved.** Written 2026-11-16.

## What is here

| File | What it does |
|---|---|
| `build_vocabulary_map.py` | Checks `pkim-vocabulary.yaml` and rebuilds the visual map |
| `vocabulary-map.template.html` | The map page without its data. Edit this to change how the map looks or behaves |

## Where the rest is

The design documents and the vocabulary file are in the dev notes vault:

`~/Development/_development-notes/md-tools-pkim-notes/pkim-schema/`

Start with `00-progress.md` there.

## Rebuild the map

```
python3 build_vocabulary_map.py
```

Needs PyYAML in the active venv. It refuses to write if the vocabulary file has a problem, and says what the problem is.
