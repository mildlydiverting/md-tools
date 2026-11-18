---
name: taskpaper-capture
description: Capture tasks and ideas from a conversation as a TaskPaper block, ready to paste under `_INBOX:` in one of Kim's todo files. Use when the user types /capture, asks for a TaskPaper block, says "capture that", "add that to my todo" or "what should I note down from this chat", or when a conversation is winding down and tasks or ideas have been left open.
---

# Task and Idea Capture

## Purpose
At the end of a conversation (or on demand), surface tasks and ideas worth capturing and format them as TaskPaper entries ready to paste under `_INBOX:` in the right todo file. Items land there via paste (from a Claude chat) or via Alfred + `inbox.py` (outside a chat). Triage — moving items to the right project heading — is always manual.

---

## Which file

There are two kinds of todo file. Both are TaskPaper format.

| File | Where | Use for |
|---|---|---|
| `todo.taskpaper` | TaskPaper's iCloud folder | The main inbox. The default. |
| `todo-{name}.md` | `~/Development/_development-notes/{name}-notes/` | Items that belong to one development project, e.g. `todo-claude.md` |

Rules:
- If the chat is plainly about one development project and that project has a `todo-{name}.md`, name that file.
- If you cannot check whether the file exists, or the chat is not about one project, use `todo.taskpaper`.
- Never guess a file name. If unsure, use `todo.taskpaper`.
- Do not write to either file yourself unless the user asks. The default is a block to paste.

---

## Modes

### Default (quiet)
Monitor the conversation passively. When it winds down, if there are one or more items worth capturing, offer a summary:

> "Want a TaskPaper block for those?" or "There are a few things worth capturing — want a block?"

Wait for yes/no. If yes, ask for the chat name (see Format below), then output the block.

If nothing is worth capturing, say nothing.

### `/capture` (noisy)
Activated by the user typing `/capture` (optionally with a context name, e.g. `/capture drawing-garden-session`).

In this mode:
- Flag ideas and tasks as they arise with a light in-line note, e.g. "*(worth capturing — I'll include this in the summary)*"
- Don't interrupt the flow; just mark it
- At the end, produce the full formatted block as normal
- If a name was passed inline (e.g. `/capture drawing-garden-session`), use it as the chat name and skip the question

---

## What counts as worth capturing

Capture:
- Explicit tasks or actions discussed or agreed
- Ideas floated but not acted on in this chat
- Deferred decisions
- Things the user says they want to remember or follow up

Do not capture:
- Factual information or explanations
- Things already resolved within the chat
- Conversational filler

Non-actionable references (a URL, a name, a resource mentioned) can sit as an indented plain-text note beneath a related task, but should not be standalone entries.

---

## Format

### Step 1: Ask for the chat name
> "What shall I call this chat for the source tag?"

Use whatever the user provides. If they decline, use `chat`.

### Step 2: Determine the project heading
- If the conversation is inside a named Claude Project, use that as the outer heading with the chat name nested beneath it
- If not, the chat name is the only heading

### Step 3: Output the block

Tags go on the heading line, not on individual tasks. The heading carries `@date()` and `@claude()`. Individual tasks carry only `@idea` or `@high` where applicable — nothing else.

**With a Claude Project:**
```
Claude Project Name:
	Chat Name: @date(2026-04-22) @claude(Chat Name)
		- Task stated plainly
		- Urgent task @high
		- Future idea @idea
			Reference note or URL if relevant
```

**Without a Claude Project:**
```
Chat Name: @date(2026-04-22) @claude(Chat Name)
	- Task stated plainly
	- Urgent task @high
	- Future idea @idea
		Reference note or URL if relevant
```

---

## Tags

| Tag | Usage |
|---|---|
| `@date()` | ISO date captured; on heading only |
| `@claude()` | Chat name; on heading only; only present for Claude-sourced items |
| `@high` | Something urgent or important; on individual task |
| `@idea` | Future/low priority; on individual task |

No `@status`, no `@type`, no `@source`, no `@priority`. Keep it simple. URLs sit inline in the text or as indented plain-text notes, not in tags.

Alfred-captured items land directly under `_INBOX:` with no heading, no `@claude()`, and no `@date()` unless the script adds one.

---

## Indentation
Use real tabs (`\t`), not spaces. TaskPaper is tab-sensitive.

---

## Output behaviour
- Output the block as a single fenced code block, ready to copy
- Do not explain or annotate the block — it should be clean copy-paste
- After the block, one line naming the file: "Paste under `_INBOX:` in `todo.taskpaper`." or "Paste under `_INBOX:` in `todo-claude.md`."
- If the file has no `_INBOX:` heading, it goes at the top of the file
- Always use today's actual date for `@date()` — never a hardcoded or example date

---

## References
- [TaskPaper format guide](https://guide.taskpaper.com/getting-started/) — human-readable introduction to the format
- [birch-outline](https://github.com/jessegrosjean/birch-outline) — open source JS library; the authoritative format spec for `.taskpaper` files
