"""Offline tests for wf_checkin.py. Run: python3 test_wf_checkin.py"""
import datetime as dt
import unittest

import wf_checkin as wf

TODAY = dt.date(2026, 11, 21)


class FakeApi(wf.Api):
    """In-memory Workflowy with just enough behaviour for the tests."""

    def __init__(self):
        super().__init__("fake")
        self.nodes = {}
        self.days = {}      # "YYYY-MM-DD" -> day node id
        self.n = 0
        self.inbox = self._node(None, "Inbox")

    def _node(self, parent, name, **kw):
        self.n += 1
        nid = f"n{self.n}"
        self.nodes[nid] = {"id": nid, "parent_id": parent, "name": name,
                           "priority": self.n, "completed": False,
                           "completedAt": None, "data": kw.get("data", {})}
        return nid

    def _resolve(self, key, create=False):
        if key == "inbox":
            return self.inbox
        if len(key) == 10 and key[4] == "-":
            if key not in self.days:
                if not create:
                    raise wf.NotFound(key)
                self.days[key] = self._node(None, key)
            return self.days[key]
        return key

    def get(self, path, query=None):
        if path == "/nodes-export":
            return {"nodes": list(self.nodes.values())}
        if path == "/nodes":
            pid = self._resolve(query["parent_id"])
            return {"nodes": [n for n in self.nodes.values()
                              if n["parent_id"] == pid]}
        if path.startswith("/nodes/"):
            return {"node": self.nodes[self._resolve(path[7:])]}
        raise AssertionError(path)

    def post(self, path, body):
        if path == "/nodes":
            pid = self._resolve(body["parent_id"], create=True)
            return {"item_id": self._node(pid, body["name"])}
        if path.endswith("/mirror"):
            origin = path.split("/")[2]
            mid = self._node(body["parent_id"], self.nodes[origin]["name"],
                             data={"mirror": {"origin_id": origin}})
            return {"item_id": mid, "origin_id": origin}
        if path.endswith("/complete"):
            nid = path.split("/")[2]
            nid = self.nodes[nid]["data"].get("mirror", {}).get("origin_id", nid)
            self.nodes[nid]["completed"] = True
            return {"status": "ok"}
        raise AssertionError(path)


class Tests(unittest.TestCase):
    def setUp(self):
        self.api = FakeApi()
        a = self.api
        # Three tasks in the inbox
        self.jo = a.post("/nodes", {"parent_id": "inbox",
                                    "name": "Reply to <b>Jo</b>"})["item_id"]
        self.dentist = a.post("/nodes", {"parent_id": "inbox",
                                         "name": "Book dentist"})["item_id"]
        self.teach = a.post("/nodes", {"parent_id": "inbox",
                                       "name": "Teaching 10am"})["item_id"]
        d19, d20 = TODAY - dt.timedelta(2), TODAY - dt.timedelta(1)
        # 19th: Jo + dentist. 20th: Jo carried, dentist dropped.
        wf.cmd_mirror(a, d19, self.jo)
        wf.cmd_mirror(a, d19, self.dentist)
        wf.cmd_mirror(a, d20, self.jo)
        # Today: Jo carried again, teaching new and done.
        wf.cmd_mirror(a, TODAY, self.jo)
        wf.cmd_mirror(a, TODAY, self.teach)
        wf.cmd_complete(a, self.teach)

    def test_today(self):
        data = wf.collect(self.api, TODAY)
        texts = [r["text"] for r in data["today_items"]]
        self.assertEqual(texts, ["Reply to Jo", "Teaching 10am"])

    def test_slips(self):
        data = wf.collect(self.api, TODAY)
        slip = {r["text"]: r for r in data["slipping"]}
        self.assertEqual(slip["Reply to Jo"]["days_on"], 2)
        self.assertEqual(slip["Reply to Jo"]["first_date"], "2026-11-19")
        self.assertTrue(slip["Reply to Jo"]["on_today"])
        self.assertFalse(slip["Book dentist"]["on_today"])
        self.assertNotIn("Teaching 10am", slip)

    def test_heading_reused(self):
        before = len(self.api.nodes)
        wf.ensure_heading(self.api, TODAY)
        self.assertEqual(len(self.api.nodes), before)

    def test_inbox_count(self):
        self.assertEqual(wf.collect(self.api, TODAY)["inbox_open"], 2)

    def test_empty_account(self):
        data = wf.collect(FakeApi(), TODAY)
        self.assertEqual(data["today_items"], [])
        self.assertEqual(data["slipping"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
