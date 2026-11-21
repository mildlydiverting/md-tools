---
name: three-things-checkin
description: Plan Kim's day as three things (fixed in the diary, will feel worse if it doesn't move, quick win) and keep them in her TaskPaper todo file under NEXT:, each with @date(). Spots tasks that keep slipping and offers kind options. Use when Kim says "check in", asks to plan her day, or at the end of a session.
---

<!--
Changelog
v1.1 (2026-11-20): No @slot or @today tags. The three questions are prompts
  only. A NEXT: line needs just @date(). A red ! on the page means slipping.
v1.0 (2026-11-16): First version. The todo file is the log (option C).
-->

# Three Things check-in

## Config

Edit this block to change where the log lives. Kim can also say "use X" in a
chat to override it for that session.

```
todo_file: ~/Library/Mobile Documents/com~hogbaysoftware~TaskPaper/Documents/todo.taskpaper
backup_dir: ~/Development/_to_delete
```

Never guess a path. If `todo_file` can't be read, use the paste fallback below.

## The three questions

Ask them to find the three things. They are prompts only: nothing about
which question a task answered goes in the file.

1. What's fixed in the diary today?
2. What will you feel worse about if it doesn't move today?
3. What's a quick win?

Other tags (`@high`, `@urgent`) only if Kim types them herself.

## The log is the todo file

At the very top of the file, above `_INBOX:`, sits a `NEXT:` heading. Real tabs.

```
NEXT:
	- Teaching 10am @date(2026-11-16)
	- Reply to Jo's email @date(2026-11-16)
	- Book dentist @date(2026-11-16)
```

- `@date` is the day the task first went on NEXT. Never reset it when carried over, so slips stay visible.
- `@done(date)` when finished.
- No separate log. A task is slipping when it is on NEXT, not done, and its `@date` is before today.
- Older lines may still carry `@today` or `@slot(...)`. Leave them as they are.

## Morning (when Kim says "check in" or asks to plan her day)

1. Read `todo_file`. Look at `NEXT:` and `_INBOX:`.
2. List yesterday's undone NEXT items. Ask for each: carry on, put back, or drop to `_INBOX:`. Never decide for her.
3. Suggest three things, one for each question, from the diary, `@high` / `@urgent` items and the inbox. Short reasons. Kim approves or changes.
4. Say which items have slipped, in plain words: "Reply to Jo has been on NEXT for 3 days." Calm and factual. No guilt.
5. For anything that has slipped two or more days, offer one or two gentle options (not all, not every day):
   - make it smaller (the first five minutes only)
   - ask someone for help, and offer to draft the message
   - an online pomodoro with friends (body doubling)
6. Show the exact changes to the file (see Writing). Wait for a yes.

## End of session

Short. Ask which NEXT items got done. Mark them `@done(date)`. Ask if anything should carry over to tomorrow. Offer to capture loose tasks with the `taskpaper-capture` skill. Show the changes, wait for a yes.

## Writing to the file

1. Show the changes first, as a short list of lines added, moved or tagged. This is the dry run.
2. On yes, copy the file to `backup_dir` as `{filename}.{YYYY-MM-DD-HHMM}.bak`. Then write.
3. A task already elsewhere in the file is moved to NEXT with its sub-items, and gets `@project(Heading)` naming where it came from (as the Archive already does). A new task is added fresh.
4. Earlier days' `@done` items leave NEXT and go to the top of `Archive:` with their `@project` tag.
5. Never delete a line. Never touch lines you were not asked to move. Keep every tag and sub-item.
6. Real tabs, not spaces.

## Paste fallback

If the file can't be reached (plain chat, no folder access), output the NEXT block in one fenced code block and end with one line: "Paste under `NEXT:` at the top of `todo.taskpaper`." For slips, ask Kim to paste the NEXT block, or the summary from the Three Things page.

## Tone

British English. Friendly, not effusive. Short. One action per step. A slip is information, not a failure.
