#!/usr/bin/env python3
"""
pinterest_move.py — move Obsidian notes with a Pinterest frontmatter field
into a subfolder, taking their local images with them.

Two modes:

  1. Report — find out which frontmatter keys actually exist before touching
     anything:

         python3 pinterest_move.py /path/to/vault --report

  2. Move — gated on explicit keys, dry-run unless --apply is passed:

         python3 pinterest_move.py /path/to/vault --keys pinterest-link
         python3 pinterest_move.py /path/to/vault --keys pinterest-link --apply

  Reversal:

         python3 pinterest_move.py --undo pinterest_move_log_2026-08-26_1432.tsv

Design notes
------------
- Direct file access via pathlib, not the Obsidian REST API: bulk operations
  over the API time out when Dropbox is syncing.
- Gated on explicit frontmatter keys. There is no "match anything vaguely
  Pinterest-ish" default, deliberately — run --report first.
- Attachments are only moved when the note that references them is the ONLY
  note that references them. Shared attachments stay put and are listed.
- Wikilink embeds (![[foo.jpg]]) need no rewriting: Obsidian resolves those
  by name wherever the file sits. Relative Markdown image links
  (![](attachments/foo.jpg)) DO break, so those get rewritten.
- Every applied run writes a TSV log that --undo can replay backwards.

Stdlib only. No venv needed.

Version history
---------------
v1.0  2026-08-26  First version: report, dry-run, apply, attachments, undo.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import urllib.parse
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

VERSION = "1.0"

# Folders never walked into.
SKIP_DIRS = {".obsidian", ".trash", ".git", ".stfolder", "node_modules"}

# Extensions treated as attachments rather than notes.
ATTACHMENT_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg", ".bmp", ".tiff",
    ".pdf", ".mp3", ".mp4", ".m4a", ".wav", ".mov", ".webm", ".ogg",
}

FRONTMATTER_KEY_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9 _\-\.]*)\s*:")
WIKI_EMBED_RE = re.compile(r"!\[\[([^\]\|#\^]+)(?:[#\^\|][^\]]*)?\]\]")
MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(\s*<?([^)<>\s]+)>?(?:\s+\"[^\"]*\")?\s*\)")


# --------------------------------------------------------------------------
# Vault walking
# --------------------------------------------------------------------------

def walk_vault(vault: Path):
    """Yield every file in the vault, skipping SKIP_DIRS."""
    for root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            yield Path(root) / name


def notes(vault: Path):
    return (p for p in walk_vault(vault) if p.suffix.lower() == ".md")


# --------------------------------------------------------------------------
# Frontmatter
# --------------------------------------------------------------------------

def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as err:
        print(f"  ! could not read {path}: {err}", file=sys.stderr)
        return None


def frontmatter_block(text: str) -> str | None:
    """Return the raw frontmatter body, or None if the note has none."""
    if not text.startswith("---"):
        return None
    lines = text.splitlines()
    if lines[0].strip() != "---":
        return None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() in ("---", "..."):
            return "\n".join(lines[1:i])
    return None


def top_level_keys(block: str) -> dict[str, str]:
    """
    Top-level frontmatter keys and their inline values.

    Regex rather than a YAML parse: no dependency, and tolerant of the
    slightly malformed frontmatter that scraped exports tend to carry.
    Indented lines (list items, nested maps) are ignored.
    """
    found: dict[str, str] = {}
    for line in block.splitlines():
        if not line or line[0].isspace() or line.lstrip().startswith("#"):
            continue
        match = FRONTMATTER_KEY_RE.match(line)
        if match:
            key = match.group(1).strip()
            found.setdefault(key, line[match.end():].strip())
    return found


# --------------------------------------------------------------------------
# Report mode
# --------------------------------------------------------------------------

def run_report(vault: Path, needle: str) -> None:
    counts: Counter[str] = Counter()
    samples: dict[str, str] = {}
    folders: dict[str, Counter[str]] = defaultdict(Counter)
    total = no_frontmatter = 0

    for note in notes(vault):
        total += 1
        text = read_text(note)
        if text is None:
            continue
        block = frontmatter_block(text)
        if block is None:
            no_frontmatter += 1
            continue
        for key, value in top_level_keys(block).items():
            if needle.lower() in key.lower():
                counts[key] += 1
                samples.setdefault(key, value[:90] or "(empty)")
                parent = note.parent.relative_to(vault).as_posix() or "(vault root)"
                folders[key][parent] += 1

    print(f"\nVault: {vault}")
    print(f"Notes scanned: {total}  ({no_frontmatter} with no frontmatter)")
    print(f"Frontmatter keys containing {needle!r}:\n")

    if not counts:
        print("  none found.\n")
        return

    for key, count in counts.most_common():
        print(f"  {key}   —   {count} notes")
        print(f"      sample: {samples[key]}")
        for folder, n in folders[key].most_common(6):
            print(f"      {n:>5}  {folder}/")
        print()

    keylist = " ".join(f'"{k}"' for k in counts)
    print("Next step (dry-run):")
    print(f'  python3 {Path(sys.argv[0]).name} "{vault}" --keys {keylist}\n')


# --------------------------------------------------------------------------
# Attachment resolution
# --------------------------------------------------------------------------

def build_attachment_index(vault: Path) -> dict[str, list[Path]]:
    """Map lowercase filename -> list of matching attachment paths."""
    index: dict[str, list[Path]] = defaultdict(list)
    for path in walk_vault(vault):
        if path.suffix.lower() in ATTACHMENT_EXTS:
            index[path.name.lower()].append(path)
    return index


def note_attachments(note: Path, text: str, vault: Path,
                     index: dict[str, list[Path]]) -> list[tuple[Path, str]]:
    """
    Local attachments a note references.

    Returns (resolved_path, link_style) pairs, where link_style is
    "wiki" or "markdown".
    """
    out: list[tuple[Path, str]] = []
    seen: set[Path] = set()

    for target in WIKI_EMBED_RE.findall(text):
        target = target.strip()
        if Path(target).suffix.lower() not in ATTACHMENT_EXTS:
            continue
        candidates = index.get(Path(target).name.lower(), [])
        if len(candidates) == 1 and candidates[0] not in seen:
            seen.add(candidates[0])
            out.append((candidates[0], "wiki"))
        elif len(candidates) > 1:
            print(f"  ? ambiguous embed {target!r} in {note.name} — left in place")

    for raw in MD_IMAGE_RE.findall(text):
        if raw.startswith(("http://", "https://", "data:")):
            continue
        decoded = urllib.parse.unquote(raw.split("#")[0])
        if Path(decoded).suffix.lower() not in ATTACHMENT_EXTS:
            continue
        candidate = (note.parent / decoded).resolve()
        if not candidate.exists():
            candidate = (vault / decoded.lstrip("/")).resolve()
        if candidate.exists() and candidate not in seen:
            seen.add(candidate)
            out.append((candidate, "markdown"))

    return out


def count_references(vault: Path, index: dict[str, list[Path]]) -> Counter[Path]:
    """How many notes reference each attachment, vault-wide."""
    refs: Counter[Path] = Counter()
    for note in notes(vault):
        text = read_text(note)
        if text is None:
            continue
        for path, _style in note_attachments(note, text, vault, index):
            refs[path] += 1
    return refs


# --------------------------------------------------------------------------
# Move planning
# --------------------------------------------------------------------------

def unique_destination(dest: Path, existing: set[Path]) -> Path:
    """Add ' 2', ' 3'… if something is already sitting at dest."""
    if dest not in existing and not dest.exists():
        return dest
    stem, suffix, n = dest.stem, dest.suffix, 2
    while True:
        candidate = dest.with_name(f"{stem} {n}{suffix}")
        if candidate not in existing and not candidate.exists():
            return candidate
        n += 1


def plan(vault: Path, dest_dir: Path, keys: list[str], move_attachments: bool,
         preserve_structure: bool) -> tuple[list[dict], list[Path]]:
    lowered = {k.lower() for k in keys}
    index = build_attachment_index(vault) if move_attachments else {}
    refs = count_references(vault, index) if move_attachments else Counter()

    moves: list[dict] = []
    shared: list[Path] = []
    claimed: set[Path] = set()

    for note in sorted(notes(vault)):
        if dest_dir in note.parents:
            continue
        text = read_text(note)
        if text is None:
            continue
        block = frontmatter_block(text)
        if block is None:
            continue
        if not (lowered & {k.lower() for k in top_level_keys(block)}):
            continue

        if preserve_structure:
            target_dir = dest_dir / note.parent.relative_to(vault)
        else:
            target_dir = dest_dir
        new_note = unique_destination(target_dir / note.name, claimed)
        claimed.add(new_note)

        attachments: list[tuple[Path, Path, str]] = []
        if move_attachments:
            for path, style in note_attachments(note, text, vault, index):
                if refs[path] > 1:
                    shared.append(path)
                    continue
                new_path = unique_destination(target_dir / path.name, claimed)
                claimed.add(new_path)
                attachments.append((path, new_path, style))

        moves.append({"note": note, "new_note": new_note, "attachments": attachments})

    return moves, shared


def rewrite_markdown_links(text: str, note_dir: Path,
                           mapping: dict[Path, Path]) -> str:
    """Repoint relative Markdown image links at the moved files."""
    if not mapping:
        return text

    by_name = {old.name: new for old, new in mapping.items()}

    def replace(match: re.Match) -> str:
        raw = match.group(1)
        if raw.startswith(("http://", "https://", "data:")):
            return match.group(0)
        name = Path(urllib.parse.unquote(raw.split("#")[0])).name
        new_path = by_name.get(name)
        if new_path is None:
            return match.group(0)
        rel = os.path.relpath(new_path, note_dir)
        quoted = urllib.parse.quote(rel.replace(os.sep, "/"), safe="/._-")
        return match.group(0).replace(raw, quoted)

    return MD_IMAGE_RE.sub(replace, text)


# --------------------------------------------------------------------------
# Apply / undo
# --------------------------------------------------------------------------

def apply_moves(moves: list[dict], log_path: Path) -> None:
    with log_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["kind", "from", "to"])

        for item in moves:
            note, new_note = item["note"], item["new_note"]
            attachments = item["attachments"]

            new_note.parent.mkdir(parents=True, exist_ok=True)
            for old, new, _style in attachments:
                new.parent.mkdir(parents=True, exist_ok=True)
                old.rename(new)
                writer.writerow(["attachment", str(old), str(new)])

            md_moves = {old: new for old, new, style in attachments
                        if style == "markdown"}
            if md_moves:
                text = read_text(note)
                if text is not None:
                    rewritten = rewrite_markdown_links(text, new_note.parent, md_moves)
                    if rewritten != text:
                        note.write_text(rewritten, encoding="utf-8")

            note.rename(new_note)
            writer.writerow(["note", str(note), str(new_note)])

    print(f"\nMove log: {log_path}")
    print(f"Reverse it with:  python3 {Path(sys.argv[0]).name} --undo \"{log_path}\"")


def run_undo(log_path: Path) -> None:
    with log_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle, delimiter="\t"))[1:]

    restored = missing = 0
    for kind, src, dst in reversed(rows):
        source, target = Path(dst), Path(src)
        if not source.exists():
            print(f"  ! missing, skipped: {source}")
            missing += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
        restored += 1

    print(f"\nRestored {restored} files ({missing} missing).")
    print("Note: Markdown link rewrites are not reversed — check any notes that "
          "used relative image links.\n")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Move Obsidian notes with a Pinterest frontmatter field into a subfolder.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("vault", nargs="?", type=Path, help="Path to the vault root")
    parser.add_argument("--report", action="store_true",
                        help="List matching frontmatter keys and counts, change nothing")
    parser.add_argument("--needle", default="pinterest",
                        help="Substring used by --report (default: pinterest)")
    parser.add_argument("--keys", nargs="+", metavar="KEY",
                        help="Frontmatter keys that mark a note for moving (exact, case-insensitive)")
    parser.add_argument("--dest", default="Pinterest",
                        help="Destination folder, vault-relative (default: Pinterest)")
    parser.add_argument("--preserve-structure", action="store_true",
                        help="Recreate each note's existing subfolder path under --dest")
    parser.add_argument("--no-attachments", action="store_true",
                        help="Leave local images where they are")
    parser.add_argument("--apply", action="store_true",
                        help="Actually move files (default is dry-run)")
    parser.add_argument("--undo", type=Path, metavar="LOG.tsv",
                        help="Reverse a previous --apply run")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    args = parser.parse_args()

    if args.undo:
        if not args.undo.is_file():
            parser.error(f"log not found: {args.undo}")
        run_undo(args.undo)
        return 0

    if args.vault is None:
        parser.error("a vault path is required (or use --undo)")
    vault = args.vault.expanduser().resolve()
    if not vault.is_dir():
        parser.error(f"not a directory: {vault}")

    if args.report or not args.keys:
        if not args.report:
            print("No --keys given, so running in report mode.")
        run_report(vault, args.needle)
        return 0

    dest_dir = (vault / args.dest).resolve()
    if vault not in dest_dir.parents and dest_dir != vault:
        parser.error("--dest must sit inside the vault")

    moves, shared = plan(vault, dest_dir, args.keys,
                         move_attachments=not args.no_attachments,
                         preserve_structure=args.preserve_structure)

    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"\n[{mode}]  {len(moves)} notes matched on: {', '.join(args.keys)}")
    print(f"Destination: {dest_dir}\n")

    for item in moves[:20]:
        print(f"  {item['note'].relative_to(vault)}")
        print(f"    -> {item['new_note'].relative_to(vault)}")
        for old, new, _style in item["attachments"]:
            print(f"    + {old.name}  ->  {new.relative_to(vault)}")
    if len(moves) > 20:
        print(f"  … and {len(moves) - 20} more notes")

    total_attachments = sum(len(m["attachments"]) for m in moves)
    print(f"\nAttachments to move: {total_attachments}")
    if shared:
        unique_shared = sorted({p.name for p in shared})
        print(f"Shared attachments left in place: {len(unique_shared)}")
        for name in unique_shared[:10]:
            print(f"    {name}")
        if len(unique_shared) > 10:
            print(f"    … and {len(unique_shared) - 10} more")

    if not moves:
        print("\nNothing to do.\n")
        return 0

    if not args.apply:
        print("\nNothing has been moved. Re-run with --apply to commit.\n")
        return 0

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    apply_moves(moves, Path.cwd() / f"pinterest_move_log_{stamp}.tsv")
    print("\nDone. Let Obsidian re-index, and check Dropbox has finished syncing.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
