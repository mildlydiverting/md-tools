# md-taskpaper-alfred

TaskPaper-based idea and task capture: `inbox.py` plus Alfred integration,
appending items to Kim's primary TaskPaper file (synced via iCloud).

Global rules apply: see `~/.claude/CLAUDE.md`.
Path: `~/Development/md-tools-pkim/md-taskpaper-alfred/`

## Status

- Built and working; awaiting sustained real-world testing.
- Next action: use it for a while, then fix friction points as they appear.

## Design decisions — do not silently undo

- **Native TaskPaper headings** organise projects; `@project()` tags were
  deliberately retired.
- Simplified tag vocabulary only: `@date()`, `@claude()`, `@high`, `@idea`.
  Do not invent new tags without asking.
- Inbox heading is exactly `_INBOX:`.
- The primary TaskPaper file lives in iCloud — treat it as live user data.
  Any script touching it defaults to dry-run and never reorders existing items.

## Key files

- `inbox.py` — capture script.
- `SKILL.md` — defines Claude's capture behaviour; read it before modifying
  anything about how items are formatted or filed.

## Commands

```bash
source .venv/bin/activate
# TODO: confirm typical invocation and Alfred keyword
python inbox.py --dry-run "test item"
```
