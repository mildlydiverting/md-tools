# Titler for Sublime Text (3 and 4).
# Runs titler.py (same folder) over the selection and replaces it with the result.
# No selection = the whole file. Install both files into Packages/User/.
import os
import subprocess
import threading

import sublime
import sublime_plugin

PYTHON = "/usr/bin/python3"
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "titler.py")


def run_titler(text, args):
    proc = subprocess.run([PYTHON, SCRIPT] + args, input=text.encode("utf-8"),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", "replace").strip() or
                           "titler.py exited %d" % proc.returncode)
    return proc.stdout.decode("utf-8")


class TitlerCommand(sublime_plugin.TextCommand):
    """args: ["links"], ["40"], ["debug"] ... same as titler.py's command line.
    copy=True: leave the text alone, put the result on the clipboard instead."""

    def run(self, edit, args=None, copy=False):
        view = self.view
        regions = [r for r in view.sel() if not r.empty()]
        if not regions:
            regions = [sublime.Region(0, view.size())]
        jobs = [(r.begin(), r.end(), view.substr(r)) for r in regions]
        change = view.change_count()
        view.set_status("titler", "Titler: fetching titles...")
        threading.Thread(target=self.work, args=(jobs, list(args or []), change, copy),
                         daemon=True).start()

    def work(self, jobs, args, change, copy):
        view = self.view
        try:
            results = [(a, b, run_titler(t, args)) for a, b, t in jobs]
        except Exception as e:
            sublime.set_timeout(lambda: self.done("Titler failed: %s" % e), 0)
            return
        if copy:
            text = "\n".join(t.strip("\n") for _, _, t in results)
            sublime.set_timeout(lambda: self.copied(text), 0)
        else:
            sublime.set_timeout(lambda: self.apply(results, change), 0)

    def done(self, msg):
        self.view.erase_status("titler")
        sublime.status_message(msg)

    def copied(self, text):
        self.view.erase_status("titler")
        sublime.set_clipboard(text)
        n = len([l for l in text.splitlines() if l.strip()])
        sublime.status_message("Titler finished: %d link%s copied to the clipboard"
                               % (n, "" if n == 1 else "s"))

    def apply(self, results, change):
        if self.view.change_count() != change:
            return self.done("Titler: text changed while fetching, nothing replaced")
        self.view.erase_status("titler")
        self.view.run_command("titler_apply", {"results": results})
        sublime.status_message("Titler: done")


class TitlerApplyCommand(sublime_plugin.TextCommand):
    def run(self, edit, results):
        for a, b, text in sorted(results, reverse=True):   # back to front keeps offsets valid
            self.view.replace(edit, sublime.Region(a, b), text)
