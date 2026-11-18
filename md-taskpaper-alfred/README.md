# md-taskpaper-alfred

A lightweight capture workflow for appending tasks and ideas to a TaskPaper file, from Alfred or the terminal.

---

## What it does

`inbox.py` inserts one or more entries under the `_INBOX:` heading in your TaskPaper file. If the heading doesn't exist, it creates it at the top of the file.

It works in two modes:

- **Alfred**: invoke a keyword, type your task, script runs directly
- **Terminal**: pass text as an argument, or pipe via stdin

Formatted blocks from Claude can be pasted via Alfred or directly into the file.

---

## Setup

### Requirements

- Python 3.10+
- A TaskPaper file with an `_INBOX:` heading (or let the script create one)

### File path

The target file is hardcoded near the top of `inbox.py`:

```python
DEFAULT_FILE = Path(os.environ.get("targetfile", str(Path.home() / "Library/Mobile Documents/com~hogbaysoftware~TaskPaper/Documents/todo.taskpaper")))
```

To override it, either:
- Edit the hardcoded path directly
- Set a `targetfile` environment variable (Alfred workflow variable or shell profile)

### Inbox heading

Defaults to `_INBOX:`. Override by setting an `inbox` environment variable — in Alfred this is a workflow variable, in the terminal set it in your shell profile.

---

## Usage

### Terminal

```zsh
# Simple task
python3 inbox.py "Pick up more charcoal"

# Pre-formatted line (e.g. pasted from a Claude chat)
python3 inbox.py "	- My task @date(2026-04-22) @claude(my-chat)"

# Via stdin
echo "Pick up more charcoal" | python3 inbox.py

# Different file
python3 inbox.py "Some task" --file ~/path/to/other.taskpaper
```

### Alfred

Set up a workflow with:
- **Trigger**: Keyword (e.g. `todo`), with argument
- **Action**: Run Script, language set to Python 3, script set to the path of `inbox.py`
- **Notification**: Post notification using `{output}` as the message

Optional workflow variables:
- `targetfile` — path to your TaskPaper file
- `inbox` — heading name to insert under (default: `_INBOX:`)

---

## Input handling

| Input | Result |
|---|---|
| Raw text | Wrapped as `- text @date(today)` |
| Line starting with `\t-` | Inserted as-is |
| Line starting with `\t\t` | Inserted as-is (nested note) |
| Blank line | Skipped |
| Multi-line input | Each line handled independently |

---

## Claude capture workflow

This script is part of a wider idea capture workflow using Claude.

At the end of a Claude chat, Claude offers a formatted TaskPaper block covering tasks and ideas from the conversation. The block uses this structure:

```
Chat Name: @date(2026-04-22) @claude(Chat Name)
	- A task discussed in the chat
	- An urgent task @high
	- A future idea @idea
		https://a-reference-url.com
```

Copy the block, invoke Alfred, paste — done.

See `SKILL.md` for the full Claude behaviour spec.

---

## Tags

| Tag | Usage |
|---|---|
| `@date()` | Capture date, ISO format; on heading only |
| `@claude()` | Source chat name; on heading only |
| `@high` | Urgent or important |
| `@idea` | Future/low priority |

---

## References

- [TaskPaper format guide](https://guide.taskpaper.com/getting-started/)
- [birch-outline](https://github.com/jessegrosjean/birch-outline) — authoritative format spec
- [Alfred workflows](https://www.alfredapp.com/help/workflows/)
