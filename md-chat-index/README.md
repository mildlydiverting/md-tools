# md-chat-index

Repeatable way to produce a **chat index CSV** and a **project summary** for a Claude project. Written for an incoming model picking this up cold; Kim's conventions are in the last section.

## What's here

| File | Purpose |
|---|---|
| `parse_recent_chats.py` | Compacts saved `recent_chats` results (both output shapes) into JSON: id, date, title, excerpt. |
| `build_chat_index.py` | Builds `<slug>-chat-index.csv` and `<slug>-summary.md` from one data file. Validates as it goes. |
| `examples/md-pkim-and-tools.example.json` | Real data from the 4 Nov 2026 run (72 chats, 19 sections). Copy it as a template. |

No paths are hard-coded. Everything is an argument; standard library only (Python 3.8+).

## Workflow

1. **Look for existing outputs first.** Search the project's folders for `*chat-index*` and `*summary*.md`. Update rather than duplicate, and rename to `<slug>-chat-index.csv` / `<slug>-summary.md` if they use an older convention. Check the project name matches: a file called `md-tools-chat-index.csv` may belong to a different project (it did).
2. **Collect chats.** Call `recent_chats` with `n=20`, then repeat with `before=<updated_at of the last chat>` until a page returns fewer than 20. Large results are persisted to a file by the tool; pass those files to `parse_recent_chats.py`. Cross-check with a few `conversation_search` queries on the project's main themes, especially for the newest chats, which return a raw transcript rather than a summary.
3. **Write the data file.** One entry per chat (`summary` is one or two sentences, British English), then sections. Copy `examples/…example.json`. Use `carry_from` + `extra_body` to reuse sections from an earlier summary (`--carry-from`).
4. **Build.**
   ```
   python3 build_chat_index.py my-data.json --out-dir /path/to/_inbox --carry-from old-summary.md
   ```
   It refuses to write if a chat is in no section, or a section lacks exactly three todos.
5. **Deliver** to the folder Kim named, and list ambiguities at the end of your reply (they also go in the summary's `notes`).

## Gotchas learned

- `recent_chats` is **not filterable by project**; judge membership yourself and say so in the notes.
- A chat that spans several sub-projects goes in each relevant section's `chat_ids`.
- `last_updated` is the metadata timestamp (UTC); `parse_recent_chats.py` trims it to whole seconds.
- Exact titles matter: some contain double spaces. Copy them from the tool output.
- Dropbox-hosted folders can be slow; write the files once, at the end.
- Todos are inferred from where each chat ended; say so in the notes.

## Kim's conventions

British English; short structured answers; no effusive praise; ask at most one short question at a time, except when told "don't ask, just do it", in which case list ambiguities at the end. Cite sources where claims are made.
