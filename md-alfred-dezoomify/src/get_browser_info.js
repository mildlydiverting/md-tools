// get_browser_info.js — v1.0
// Alfred workflow JXA script
//
// Detects the frontmost browser (Safari or Chrome), grabs the current tab's
// URL and title, and reads the clipboard (which Alfred's hotkey trigger has
// already populated with any selected text). Returns everything as JSON for
// Alfred's "JSON to Variables" step.
//
// Run via a bash "Run Script" step in Alfred:
//   osascript -l JavaScript ./get_browser_info.js
//
// Output JSON shape:
//   { "url": "...", "title": "...", "selected_text": "..." }

function run(argv) {

    // ── 1. Read clipboard ──────────────────────────────────────────────────
    // Alfred's hotkey trigger (set to "Copy to Clipboard on Activation")
    // sends Cmd+C before invoking, so the clipboard holds selected text.
    const selfApp = Application.currentApplication()
    selfApp.includeStandardAdditions = true

    let selectedText = ''
    try {
        const cb = selfApp.theClipboard()
        if (typeof cb === 'string') {
            selectedText = cb
        }
    } catch (e) {
        // Clipboard empty or non-text — fine, we just leave it blank
    }

    // ── 2. Detect frontmost application ───────────────────────────────────
    const SystemEvents = Application('System Events')
    let frontmostApp = ''
    try {
        frontmostApp = SystemEvents.processes.whose({ frontmost: true })[0].name()
    } catch (e) {
        // Will fall through to the running-browser check below
    }

    // ── 3. Browser accessor functions ─────────────────────────────────────
    function getSafariInfo() {
        const safari = Application('Safari')
        const tab = safari.windows[0].currentTab
        return {
            url:   tab.url(),
            title: tab.name()
        }
    }

    function getChromeInfo() {
        const chrome = Application('Google Chrome')
        const tab = chrome.windows[0].activeTab
        return {
            url:   tab.url(),
            title: tab.title()   // Chrome uses .title(), Safari uses .name()
        }
    }

    // ── 4. Get tab info ────────────────────────────────────────────────────
    // When Alfred is invoked via hotkey it briefly becomes frontmost, so we
    // can't assume the browser will still be reported as frontmost. We try
    // the detected frontmost app first, then fall back to whichever browser
    // is running.
    let info

    if (frontmostApp === 'Safari') {
        info = getSafariInfo()

    } else if (frontmostApp === 'Google Chrome') {
        info = getChromeInfo()

    } else {
        // Alfred (or something else) was frontmost — find a running browser
        const safariRunning = Application('Safari').running()
        const chromeRunning = Application('Google Chrome').running()

        if (safariRunning && chromeRunning) {
            // Both running: pick whichever was most recently active.
            // We check Safari first as a tie-break; adjust to taste.
            try {
                info = getSafariInfo()
            } catch (e) {
                info = getChromeInfo()
            }
        } else if (safariRunning) {
            info = getSafariInfo()
        } else if (chromeRunning) {
            info = getChromeInfo()
        } else {
            throw new Error('No supported browser is running (tried Safari and Google Chrome)')
        }
    }

    // ── 5. Return JSON ─────────────────────────────────────────────────────
    return JSON.stringify({
    alfredworkflow: {
        arg: info.url,
        variables: {
            url:           info.url,
            title:         info.title,
            selected_text: selectedText
            }
        }
    })
}
