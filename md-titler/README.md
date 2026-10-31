# Titler (Python)

Turns URLs in your text into Markdown links with the page title.

```
https://example.org/some-page
→ [The page's title](https://example.org/some-page)
```

A Python 3 rewrite of Brett Terpstra's 2015 `titler.rb` (the Ruby original
stopped working on macOS 26). Standard library only, no affiliate links.

## What's here

| File | What it is |
|---|---|
| `titler.py` | The script. Text in on stdin, text out on stdout. |
| `Titler (Python).workflow` | macOS Service: replaces selected text with titled links. |
| `Titler (Python) - Extract Links.workflow` | Service: copies a Markdown list of the selection's links to the clipboard and shows a "Titler finished" notification. Your selection is left untouched. |
| `titler_command.py` | Sublime Text plugin (runs `titler.py` directly, no Services). |
| `Default (OSX).sublime-keymap` | Suggested Sublime key bindings. |

Needs macOS with `/usr/bin/python3` (3.9 is fine) and `/usr/bin/curl`.

## What it does

- Bare URLs become `[Title](url)`.
- Existing `[text](url)` links get their text replaced with the page title.
- Reference links (`[id]: url`) get the title added: `[id]: url "Title"`.
- HTML entities in titles are decoded (`&amp;`, `&#x27;`, `&eacute;`, …).
- `<title>` tags with attributes are found (e.g. `<title data-rh="true">`).
- Site names are trimmed from the start or end of titles (`Why Cats Purr | The Verge` → `Why Cats Purr`). Root pages are left alone.
- `utm_` tracking parameters are removed from URLs.
- If a title can't be fetched, the link uses the hostname instead. Nothing fails silently: add `debug` to see why.

## Options

Put these on the command line, or on a first line of the input starting with `::`
(for example `:: 40 debug`):

| Option | Effect |
|---|---|
| `links` (or `l`) | Output only a Markdown list of links found |
| `<number>` | Truncate titles to that many characters (full title kept as the link's title attribute) |
| `clipboard` (or `c`) | Copy the result with `pbcopy` and print a count |
| `debug` (or `d`) | Print progress and errors to stderr |

```bash
cat notes.md | /usr/bin/python3 titler.py
cat notes.md | /usr/bin/python3 titler.py links 40
```

## Installing the Services

1. Copy both `.workflow` folders into `~/Library/Services/`.
2. Select text with a URL in an app that supports Services, then use **App name ▸ Services ▸ Titler (Python)** (replaces the selection) or **… ▸ Titler (Python) - Extract Links** (copies a list of links to the clipboard).
3. Optional: assign a shortcut in **System Settings ▸ Keyboard ▸ Keyboard Shortcuts ▸ Services ▸ Text**.

Each Service is a single "Run Shell Script" action that writes the embedded
script to a temporary file and runs it with `/usr/bin/python3`. It works with
either `/bin/bash` or `/bin/zsh` as the shell. The Services are built on the
same Automator 2.10 skeleton as the working `md - …` Services; the original
2015 format stopped being recognised ("There was a problem with the input to
the Service").

## Installing the Sublime Text plugin

Sublime Text's Services menu lists Titler but doesn't pass it the selection, so
the Service fails there. The plugin avoids Services altogether.

1. **Preferences ▸ Browse Packages…** and open the `User` folder.
2. Copy in `titler_command.py` and `titler.py` (they must sit side by side).
3. Add the bindings from `Default (OSX).sublime-keymap` to **Preferences ▸ Key Bindings** (user side):
   `⌘⌥T` replaces the selection with titled links; `⌘⌥⇧T` leaves the text alone and copies a Markdown list of the links to the clipboard (like the Extract Links Service). Change the keys as you like.

It replaces each selection, or the whole file if nothing is selected. It
fetches in the background (status bar shows progress). If you edit the text
while it's working, it replaces nothing. Pass options with
`"args": { "args": ["links", "40"] }` in a key binding. Add `"copy": true` to put the result on the clipboard instead of replacing the text.

## Troubleshooting

- **"There was a problem with the input to the Service."** The app isn't passing
  the selection as plain text (Sublime Text doesn't), or the Service is an
  old-format workflow. Try the Service in Notes or Obsidian to check.
- **Selected text run as code** (`SyntaxError` naming your URL): don't set the
  Run Shell Script shell to `/usr/bin/python3`. Automator feeds the input to
  Python as the program. Keep the shell as bash or zsh.
- **No title / just the hostname:** the site may block curl, need a login, or
  build its title with JavaScript. Run with `debug`.
- **Slow:** each link is fetched once (repeats are cached), with a 20 second limit.
- **Test outside Automator:**
  `echo 'https://www.bbc.co.uk/news' | /usr/bin/python3 titler.py debug`

## Limits

- Titles come from the HTML `<title>` tag only, from the first 1 MB of the page.
- Titles in other languages and character sets are decoded using the page's declared charset, falling back to UTF-8.
- Site-name trimming is a heuristic and can occasionally miss or over-trim.

## Credits

Based on `titler.rb` by Brett Terpstra (2015, MIT licence), <http://brettterpstra.com>.
