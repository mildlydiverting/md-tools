---
type: prompt
title: md-chat-index - PROMPT
description:
resource:
timestamp: 2026-11-04T15:07:23+00:00
created: 2026-11-04T15:04
aliases:
tags:
  - 
---
# md-chat-index - PROMPT

For running an index and update inside Claude projects, when your brain gets full

```
Please update the chat index and project summary for this project, and save both files in `/Users/kimplowright/Development/_development-notes/_inbox`.

Use the current claude project name as a filename slug prefix
  (e.g. `md-tools-pkim`)

Tools: `/Users/kimplowright/Development/md-tools-pkim/md-chat-index/`. Read its README.md first and use `parse_recent_chats.py` and `build_chat_index.py`. Do not rewrite them.

1. Look for existing outputs
Search this project's folders for `*chat-index*`, `*summary*.md` and `<slug>-chat-index.data.json`. Only treat a file as this project's if the project name matches; files for other projects (for example `md-tools-chat-index.csv`) are to be left alone. If this project's files exist, update them and rename to `<slug>-chat-index.csv` / `<slug>-summary.md`. Leave the originals in place and tell me where they are. If none exist, create new files.

2. Collect the chats
Page through `recent_chats` (n=20, using `before=` the last `updated_at`) until a page returns fewer than 20. If a `<slug>-chat-index.data.json` already exists, I only need chats newer than its latest `last_updated`, plus any whose title has changed. Use `conversation_search` on the project's main themes to catch anything missed, and to get detail on chats that only returned a raw transcript. `recent_chats` can't filter by project, so use your judgement on membership and note it.

3. Write the data file
Use the format in `examples/*.example.json`:
- Chats: one entry each, with the exact title, the metadata timestamp, and one or two sentences on what we were trying to do.
- Sections: one per distinct sub-project or area of work. Each has a one-line description, a Sub-areas list (strands, scripts, outputs), the chat ids, and exactly three concrete next todos. If a chat spans several sub-projects, put it in each relevant section.
- When updating, reuse unchanged sections from the earlier summary (`--carry-from`) and extend them rather than rewriting.

4. Build and save
Run `build_chat_index.py` into `_inbox`, and save the data file there too as `<slug>-chat-index.data.json` so the next run can be incremental.

Rules:
- British English.
- Don't ask clarifying questions. Do the work, save the files, then list anything ambiguous at the end, such as borderline chats, guessed todos and anything that couldn't be verified.
- Keep the final reply short: what was written, where, and the ambiguities.
```