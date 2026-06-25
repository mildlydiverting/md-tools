"""
PATCH for eagle_import.py
--------------------------

THREE changes:

── 1. name field in import_folder() (~line 280) ─────────────────────────────

OLD:
    name = meta.get("title") or image_path.stem

NEW:
    name = meta.get("photo_id") or image_path.stem

Eagle shows photo_id as the item name. Full title is in the annotation.

── 2. Replace build_annotation() entirely ───────────────────────────────────

Fixes:
  - yaml.dump() was wrapping long strings at 80 chars, breaking URLs and
    citations mid-string. Fixed with width=float('inf').
  - title was missing from the annotation fields. Added.
  - URLs in creator_url / source_url / license_url should be plain text,
    not converted to HTML <a href> tags.

Replace the entire build_annotation() function with the version below.

── 3. Remove any linkify() / URL-to-HTML conversion ─────────────────────────

If your local eagle_import.py has a function that wraps URLs in <a href> tags,
remove it. Eagle's annotation field does not render HTML.
"""

import yaml


def build_annotation(meta):
    """
    Build the annotation block for Eagle.

    Format:
        YAML front matter (--- delimited) containing structured citation fields,
        followed by the plain-text citation as a readable block.

    Notes:
        - width=float('inf') prevents yaml from wrapping long strings at 80 chars.
          Without this, URLs and citations get broken across lines with YAML
          continuation indentation, which makes them unreadable in Eagle.
        - All URL fields are plain text — Eagle does not render HTML.
        - Title is included in full, untruncated.
    """
    fields = {}

    for dest, src in [
        ("photo_id",      "photo_id"),
        ("title",         "title"),           # full title, untruncated
        ("creator",       "creator"),
        ("creator_url",   "creator_profile_url"),
        ("date_created",  "date_created"),
        ("medium",        "medium"),
        ("license",       "license_name"),
        ("license_url",   "license_url"),
        ("source_url",    "accessed_url"),
        ("copyright_line","copyright_line"),
        ("tasl",          "tasl"),
        ("citation",      "citation_markdown"),
    ]:
        val = meta.get(src)
        if val:
            fields[dest] = str(val)

    if not fields:
        return ""

    yaml_block = yaml.dump(
        fields,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=float('inf'),      # ← prevents line-wrapping inside strings
    ).strip()

    front_matter = f"---\n{yaml_block}\n---"

    citation = fields.get("citation", "")
    machine_tags = meta.get("_machine_tags", [])

    parts = [front_matter]
    if citation:
        parts.append(citation)
    if machine_tags:
        parts.append("tags:\n" + "\n".join(f"  {t}" for t in machine_tags))

    return "\n\n".join(parts)
