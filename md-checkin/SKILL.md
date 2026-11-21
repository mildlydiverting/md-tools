---
name: three-things-checkin
description: Plan Kim's day as three things (fixed in the diary, will feel worse if it doesn't move, quick win), kept on Workflowy's daily calendar page as mirrors of real tasks. Spots tasks that keep slipping and offers kind options. Use when Kim says "check in", asks to plan her day, or at the end of a session.
---

<!--
Changelog
v2.1 (2026-11-21): The page (checkin-log.html v5) reads and ticks live, so
  no fetch step. Kim can do everything on the page; the skill is for
  talking it through.
v2.0 (2026-11-21): Workflowy replaces TaskPaper. Three things are mirrors
  on the day's calendar page, under a "Three things" heading. Slips come
  from mirror history, not @date. All reads and writes go through
  wf_checkin.py. The TaskPaper version is v1.1 in git history.
v1.1 (2026-11-20): No @slot or @today tags. Red ! on the page means slipping.
v1.0 (2026-11-16): First version. The todo file is the log.
-->

# Three Things check-in

## How it's laid out in Workflowy

```
Calendar
  2026-11-21
    Three things            (h2)
      Reply to Jo           (mirror: the original lives in Inbox or a project)
      Teaching 10am         (mirror)
      Book dentist          (mirror)
```

- The **original** task lives in the Inbox or a project. The day page only holds **mirrors**.
- **Carry over** = mirror the task onto today as well. Old mirrors stay put, so the history shows.
- **Slipping** = not done, and first mirrored before today. The days count comes from that first mirror.
- **Done** = complete it once. Mirrors share the original's state.
- **Drop** = remove today's mirror only. The task stays where it lives.

## Tool

All Workflowy changes go through the script, not by hand:

```
script: ~/Development/md-tools-pkim/md-checkin/wf_checkin.py
```

| Need | Command |
|---|---|
| See today and slips | `wf_checkin.py show` |
| New task, onto today | `wf_checkin.py add "Text" --today` |
| New task, Inbox only | `wf_checkin.py add "Text"` |
| Existing task onto today | `wf_checkin.py mirror ID` |
| Mark done | `wf_checkin.py complete ID` |
| Take off today | `wf_checkin.py unmirror MIRROR_ID` |

Add `--dry-run` to any command to see the change without making it.

Where to run it, in order:
1. A shell on Kim's Mac that can reach workflowy.com.
2. Otherwise, Workflowy MCP tools, if this session has them. Mirrors need the heading's full node id, not `today`.
3. Otherwise, use the paste fallback below.

Never guess an id. Take ids from `show` output.

## The three questions

Ask them to find the three things. They are prompts only: nothing about which question a task answered is stored.

1. What's fixed in the diary today?
2. What will you feel worse about if it doesn't move today?
3. What's a quick win?

Other tags (`#high`, `#urgent`) only if Kim types them herself.

## Morning (when Kim says "check in" or asks to plan her day)

1. Run `show`.
2. List yesterday's undone items. Ask for each: carry on, put back, or drop. Never decide for her.
   - Carry on → `mirror ID` onto today.
   - Put back or drop → nothing to do; it stays where it lives.
3. Suggest three things, one for each question, from the diary, `#high` / `#urgent` items and the Inbox. Short reasons. Kim approves or changes.
4. Say which items have slipped, in plain words: "Reply to Jo has been on your three things for 3 days." Calm and factual. No guilt.
5. For anything that has slipped two or more days, offer one or two gentle options (not all, not every day):
   - make it smaller (the first five minutes only)
   - ask someone for help, and offer to draft the message
   - an online pomodoro with friends (body doubling)
6. Show the exact commands (the dry run). Wait for a yes. Then run them. The Three Things page reads Workflowy live, so Kim just presses Refresh.

## End of session

Short. Run `show`. Ask which items got done; `complete` each one. Ask if anything should carry to tomorrow; tomorrow's check-in mirrors it then, so nothing to do now. Offer to capture loose tasks to the Inbox with `add`. Show the commands, wait for a yes, run them.

## Writing rules

1. Show the commands first. This is the dry run.
2. Never delete a node. `unmirror` removes a mirror only, and only when Kim asks to take something off today.
3. Never move or rename tasks you weren't asked about.
4. A new task always goes to the Inbox first, then gets mirrored. Triage stays manual.

## Paste fallback

If the script can't run here, give Kim the commands in one fenced block to paste into Terminal, or point her to the Three Things page, which can do the same live. For slips, ask her to paste the output of `show`.

## Tone

British English. Friendly, not effusive. Short. One action per step. A slip is information, not a failure.
