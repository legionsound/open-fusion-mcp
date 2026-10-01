"""Fault injection [issues #1, #2, #3]: the real server and a real (spawned) worker run against testkit's file-backed fake Resolve, while
test.* operations hang, crash the worker or fail after a partial change. Checks the journal receipts on TIMEOUT/TRANSPORT replies,
batch.recover, batch.rollback and atomic batches. Offline: no Resolve needed."""
import asyncio
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

TMP = tempfile.mkdtemp(prefix="fc_receipts_")
STATE = os.path.join(TMP, "fake_comp.json")
ENV = {"FUSION_MCP_FAKE_RESOLVE": STATE, "FUSION_MCP_TEST_FAULTS": "1", "FUSION_MCP_OUT_DIR": os.path.join(TMP, "out"),
       "FUSION_MCP_PROJECT_ALLOWLIST": "Testbed", "FUSION_MCP_READONLY": "", "FUSION_MCP_ALLOW_CATEGORIES": ""}
_saved = {}


def setUpModule():
    for k, v in ENV.items():
        _saved[k] = os.environ.get(k)
        os.environ[k] = v
    from fusion_connector import testkit  # noqa: F401  registers test.* in this (server) process; the worker reads the env


def tearDownModule():
    from fusion_connector import server
    from fusion_connector.ops import OPS
    server.BRIDGE.close()
    for n in [n for n in OPS if n.startswith("test.")]:
        del OPS[n]
    for k, v in _saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    shutil.rmtree(TMP, ignore_errors=True)


def call(operation, args, timeoutMs=None):
    from fusion_connector import server
    a = {"operation": operation, "args": args}
    if timeoutMs:
        a["timeoutMs"] = timeoutMs
    return asyncio.run(server.do(a)).structuredContent


def tools():
    from fusion_connector.testkit import state
    return sorted(state(STATE)["tools"])


def fake_state():
    from fusion_connector.testkit import state
    return state(STATE)


def drop_empty_groups():
    """Make the fake drop undo groups that recorded nothing (whether Fusion does is what receipts_live.py's probe stage measures)."""
    from fusion_connector.testkit import _save
    st = fake_state()
    st["dropEmptyGroups"] = True
    _save(STATE, st)


class Base(unittest.TestCase):
    def setUp(self):
        if os.path.exists(STATE):
            os.unlink(STATE)
        shutil.rmtree(os.path.join(TMP, "out", "journal"), ignore_errors=True)
        shutil.rmtree(os.path.join(TMP, "out", "test_hang_once"), ignore_errors=True)
        r = call("test.add", {"names": []})            # warm worker: spawn time never eats a short timeout
        self.assertTrue(r["ok"], r)

    def err(self, r):
        self.assertFalse(r["ok"], r)
        return r["error"]


class Batches(Base):
    def test_normal_batch_is_journaled(self):
        r = call("batch.run", {"ops": [{"operation": "test.add", "args": {"names": ["A"]}}, {"operation": "test.add", "args": {"names": ["B"]}}]})
        self.assertTrue(r["ok"], r)
        self.assertEqual(tools(), ["A", "B"])
        from fusion_connector import journal
        lines = journal.read(r["result"]["callId"])
        self.assertEqual([x["t"] for x in lines if x["t"] in ("start", "end")], ["start", "end", "start", "end"])
        self.assertEqual(lines[-1], dict(lines[-1], t="done", ok=True))
        rec = journal.reconcile(lines)
        self.assertEqual([s["index"] for s in rec["completed"]], [0, 1])
        self.assertEqual(rec["completed"][0]["changed"], {"added": ["A"]})
        self.assertTrue(rec["finished"])
        self.assertEqual(rec["undoGroup"], "closed")

    def test_failure_keeps_finished_steps_by_default(self):
        r = call("batch.run", {"ops": [{"operation": "test.add", "args": {"names": ["A"]}},
                                       {"operation": "test.partial", "args": {"names": ["B", "C"], "failAfter": 1}},
                                       {"operation": "test.add", "args": {"names": ["D"]}}]})
        e = self.err(r)
        self.assertIn("atomic: true", e["message"])
        self.assertEqual(tools(), ["A", "B", "D"])                     # not transactional: the half step stays too

    def test_atomic_undoes_and_verifies(self):
        r = call("batch.run", {"atomic": True, "ops": [{"operation": "test.add", "args": {"names": ["A"]}},
                                                       {"operation": "test.partial", "args": {"names": ["B", "C"], "failAfter": 1}},
                                                       {"operation": "test.add", "args": {"names": ["D"]}}]})
        e = self.err(r)
        self.assertIn("step 1 failed", e["message"])
        self.assertIn("(verified)", e["message"])
        rb = e["details"]["rollback"]
        self.assertTrue(rb["rolledBack"] and rb["verified"], rb)
        self.assertEqual(rb["evidence"]["added"], [])
        self.assertEqual(tools(), [])                                  # A and the partial B are gone; D never ran
        self.assertTrue(e["details"]["results"][2]["skipped"])

    def test_atomic_refuses_rejected_steps_up_front(self):
        r = call("batch.run", {"atomic": True, "ops": [{"operation": "test.add", "args": {"names": ["A"]}},
                                                       {"operation": "test.add", "args": {"nmes": ["B"]}}]})
        e = self.err(r)
        self.assertEqual(e["code"], "INVALID_ARGS")
        self.assertEqual(e["details"]["rejected"][0]["index"], 1)
        self.assertEqual(tools(), [])

    def test_atomic_failure_with_no_change_keeps_earlier_work(self):
        drop_empty_groups()                                            # if the app drops a group that recorded nothing,
        self.assertTrue(call("test.add", {"names": ["Pre"]})["ok"])    # an Undo(1) would revert this earlier change
        e = self.err(call("batch.run", {"atomic": True, "ops": [{"operation": "test.partial", "args": {"names": ["X"], "failAfter": 0}}]}))
        self.assertIn("nothing was undone", e["message"])
        self.assertFalse(e["details"]["rollback"]["rolledBack"])
        self.assertEqual(tools(), ["Pre"])

    def test_atomic_partial_first_step_is_undone(self):
        drop_empty_groups()
        self.assertTrue(call("test.add", {"names": ["Pre"]})["ok"])
        e = self.err(call("batch.run", {"atomic": True, "ops": [{"operation": "test.partial", "args": {"names": ["X", "Y"], "failAfter": 1}}]}))
        self.assertTrue(e["details"]["rollback"]["rolledBack"] and e["details"]["rollback"]["verified"], e)
        self.assertEqual(tools(), ["Pre"])

    def test_atomic_refuses_steps_one_undo_cannot_revert(self):
        r = call("batch.run", {"atomic": True, "ops": [{"operation": "test.add", "args": {"names": ["A"]}},
                                                       {"operation": "project.save", "args": {}}]})
        e = self.err(r)
        self.assertEqual(e["code"], "INVALID_ARGS")
        self.assertEqual(e["details"]["notUndoable"], [{"index": 1, "operation": "project.save"}])
        self.assertEqual(tools(), [])                                  # refused before the first step


class Timeouts(Base):
    BATCH = [{"operation": "test.add", "args": {"names": ["A"]}}, {"operation": "test.add", "args": {"names": ["B"]}},
             {"operation": "test.hang", "args": {"seconds": 30, "tool": "X"}},
             {"operation": "test.add", "args": {"names": ["C"]}}, {"operation": "test.add", "args": {"names": ["D"]}}]

    def stall(self, **kw):
        r = call("batch.run", dict({"ops": self.BATCH}, **kw), timeoutMs=3000)
        e = self.err(r)
        self.assertEqual(e["code"], "TIMEOUT")
        return e

    def test_receipt_says_what_finished_what_ran_what_never_started(self):
        e = self.stall()
        rec = e["details"]["receipt"]
        self.assertEqual([s["index"] for s in rec["completed"]], [0, 1])
        self.assertEqual(rec["uncertain"], [{"index": 2, "operation": "test.hang", "targets": ["X"]}])
        self.assertEqual(rec["notStarted"], [3, 4])
        self.assertEqual(rec["undoGroup"], "open")
        self.assertFalse(rec["finished"])
        self.assertIn("steps 0-1 finished; step 2 (test.hang on 'X') was running and may have partly applied; steps 3-4 never started",
                      e["message"])
        self.assertIn("batch.recover", e["hint"])
        self.assertEqual(tools(), ["A", "B"])                          # what Resolve really holds after the stall

    def test_recover_rereads_the_comp(self):
        e = self.stall(snapshot="names")
        cid = e["details"]["receipt"]["callId"]
        r = call("batch.recover", {"callId": cid})
        self.assertTrue(r["ok"], r)
        res = r["result"]
        self.assertEqual(res["live"]["toolsBefore"], 0)
        self.assertEqual(res["live"]["delta"], 2)
        self.assertEqual(res["live"]["added"], ["A", "B"])
        self.assertEqual(res["live"]["uncertain"], [{"index": 2, "operation": "test.hang", "targets": {"X": False}}])
        adv = " ".join(res["advice"])
        self.assertIn("undo group is still open", adv)
        self.assertIn("most likely did not apply", adv)
        self.assertIn("resume: '%s' (step 2 on" % cid, adv)
        self.assertEqual(call("batch.recover", {})["result"]["callId"], cid)    # default: the newest unfinished call

    def test_rollback_closes_the_open_group_and_undoes(self):
        cid = self.stall()["details"]["receipt"]["callId"]
        r = call("batch.rollback", {"callId": cid})
        self.assertTrue(r["ok"], r)
        res = r["result"]
        self.assertTrue(res["closedUndoGroup"] and res["rolledBack"] and res["verified"], res)
        self.assertEqual(tools(), [])
        st = fake_state()
        self.assertFalse([g for g in st["groups"] if g["open"]])
        self.assertEqual(st.get("endUndoWithoutGroup", 0), 0)
        self.assertEqual(self.err(call("batch.rollback", {"callId": cid}))["code"], "CONFLICT")   # a second undo would hit older work
        self.assertEqual(self.err(call("batch.recover", {}))["code"], "NOT_FOUND")               # handled: no longer the default

    def test_keep_only_closes_the_group(self):
        cid = self.stall()["details"]["receipt"]["callId"]
        r = call("batch.rollback", {"callId": cid, "keep": True})
        self.assertTrue(r["ok"], r)
        self.assertTrue(r["result"]["closedUndoGroup"])
        self.assertFalse(r["result"]["rolledBack"])
        self.assertEqual(tools(), ["A", "B"])
        self.assertFalse([g for g in fake_state()["groups"] if g["open"]])

    def test_rollback_refuses_after_later_changes(self):
        cid = self.stall()["details"]["receipt"]["callId"]
        self.assertTrue(call("test.add", {"names": ["Z"]})["ok"])
        e = self.err(call("batch.rollback", {"callId": cid}))
        self.assertEqual(e["code"], "CONFLICT")
        self.assertEqual(e["details"]["laterChanges"][0]["operation"], "test.add")

    def test_rollback_without_evidence_of_change_undoes_nothing(self):
        drop_empty_groups()
        self.assertTrue(call("test.add", {"names": ["Pre"]})["ok"])
        e = self.err(call("batch.run", {"ops": [{"operation": "test.hang", "args": {"seconds": 30, "tool": "X"}}], "snapshot": "names"},
                          timeoutMs=3000))
        cid = e["details"]["receipt"]["callId"]
        r = call("batch.rollback", {"callId": cid})
        self.assertTrue(r["ok"], r)
        self.assertTrue(r["result"]["closedUndoGroup"])
        self.assertFalse(r["result"]["rolledBack"])
        self.assertIn("nothing undone", r["result"]["note"])
        self.assertEqual(tools(), ["Pre"])

    def test_single_operation_rollback_reports_unverified(self):
        cid = self.err(call("test.hang", {"seconds": 30, "tool": "Y"}, timeoutMs=2500))["details"]["receipt"]["callId"]
        self.assertFalse(call("batch.rollback", {"callId": cid})["result"]["rolledBack"])     # no snapshot, no finished step
        r = call("batch.rollback", {"callId": cid, "force": True})
        self.assertTrue(r["result"]["rolledBack"])
        self.assertIsNone(r["result"]["verified"])                    # nothing to compare: not claimed as verified
        self.assertIn("nothing to verify against", r["result"]["note"])

    def test_undo_probe(self):
        self.assertTrue(call("test.undo_probe", {})["result"]["emptyGroupIsUndoEvent"])
        drop_empty_groups()
        self.assertFalse(call("test.undo_probe", {})["result"]["emptyGroupIsUndoEvent"])
        self.assertEqual(tools(), [])

    def test_single_operation_timeout(self):
        e = self.err(call("test.hang", {"seconds": 30, "tool": "Y"}, timeoutMs=2500))
        rec = e["details"]["receipt"]
        self.assertEqual(rec["uncertain"], [{"index": 0, "operation": "test.hang", "targets": ["Y"]}])
        self.assertEqual(rec["undoGroup"], "open")
        self.assertIn("test.hang on 'Y' started and never reported back", e["message"])

    def test_worker_crash_mid_batch(self):
        r = call("batch.run", {"ops": [{"operation": "test.add", "args": {"names": ["A"]}}, {"operation": "test.crash", "args": {}},
                                       {"operation": "test.add", "args": {"names": ["B"]}}]}, timeoutMs=10000)
        e = self.err(r)
        self.assertEqual(e["code"], "TRANSPORT")
        rec = e["details"]["receipt"]
        self.assertEqual(([s["index"] for s in rec["completed"]], [u["index"] for u in rec["uncertain"]], rec["notStarted"]), ([0], [1], [2]))
        self.assertEqual(tools(), ["A"])


class Resume(Base):
    """[issue #14] A batch applies its first steps, times out, and is finished without repeating them (the test suggested in the
    r/mcp thread): the read-back is compared with the intended tools, not just the job status."""
    OPS = [{"operation": "test.add", "args": {"names": ["A"]}}, {"operation": "test.add", "args": {"names": ["B"]}},
           {"operation": "test.hang", "args": {"seconds": 30, "tool": "X", "once": True, "add": "after"}},
           {"operation": "test.add", "args": {"names": ["C"]}}]

    def stall(self, ops=None):
        e = self.err(call("batch.run", {"ops": ops or self.OPS}, timeoutMs=3000))
        self.assertEqual(e["code"], "TIMEOUT")
        return e["details"]["receipt"]["callId"]

    def test_a_plain_retry_duplicates_finished_steps(self):
        self.stall()
        self.assertTrue(call("batch.run", {"ops": self.OPS})["ok"])      # the stall was transient: the retry runs everything
        self.assertEqual(tools(), ["A", "A_1", "B", "B_1", "C", "X"])     # what resume prevents (Fusion renames, never errors)

    def test_resume_skips_finished_steps_and_reads_back(self):
        cid = self.stall()
        r = call("batch.run", {"ops": self.OPS, "resume": cid})
        self.assertTrue(r["ok"], r)
        res = r["result"]
        self.assertEqual([x["index"] for x in res["results"] if x.get("skipped")], [0, 1])
        self.assertEqual(tools(), ["A", "B", "C", "X"])                   # every intended tool once
        rb = res["resume"]
        self.assertTrue(rb["verified"] and rb["closedUndoGroup"], rb)
        self.assertEqual((rb["evidence"]["missing"], rb["evidence"]["duplicates"], rb["evidence"]["intended"]), ([], [], 4))
        self.assertFalse([g for g in fake_state()["groups"] if g["open"]])
        self.assertEqual(self.err(call("batch.recover", {}))["code"], "NOT_FOUND")             # handled
        self.assertEqual(self.err(call("batch.run", {"ops": self.OPS, "resume": cid}))["code"], "CONFLICT")   # only once

    def test_resume_refuses_a_different_batch(self):
        cid = self.stall()
        changed = [dict(self.OPS[0], args={"names": ["Z"]})] + self.OPS[1:]
        e = self.err(call("batch.run", {"ops": changed, "resume": cid}))
        self.assertEqual((e["code"], e["details"]["changed"]), ("INVALID_ARGS", [0]))
        self.assertEqual(self.err(call("batch.run", {"ops": self.OPS[:3], "resume": cid}))["code"], "INVALID_ARGS")
        self.assertEqual(tools(), ["A", "B"])

    def test_resume_asks_when_the_running_step_left_its_tool(self):
        ops = [{"operation": "test.add", "args": {"names": ["A"]}},
               {"operation": "test.hang", "args": {"seconds": 30, "tool": "X", "once": True, "add": "before"}},
               {"operation": "test.add", "args": {"names": ["C"]}}]
        cid = self.stall(ops)
        e = self.err(call("batch.run", {"ops": ops, "resume": cid}))
        self.assertEqual(e["code"], "CONFLICT")
        self.assertEqual(e["details"]["uncertain"], [{"index": 1, "operation": "test.hang", "targetsPresent": ["X"]}])
        r = call("batch.run", {"ops": ops, "resume": cid, "uncertain": "skip"})
        self.assertTrue(r["ok"], r)
        self.assertEqual(tools(), ["A", "C", "X"])                        # X was kept, not added again as X_1

    def test_resume_needs_a_batch_and_no_atomic(self):
        cid = self.err(call("test.hang", {"seconds": 30, "tool": "Y"}, timeoutMs=2500))["details"]["receipt"]["callId"]
        e = self.err(call("batch.run", {"ops": [{"operation": "test.hang", "args": {"seconds": 1, "tool": "Y"}}], "resume": cid}))
        self.assertIn("only batches resume", e["message"])
        self.assertEqual(self.err(call("batch.run", {"ops": self.OPS, "resume": cid, "atomic": True}))["code"], "INVALID_ARGS")

    def test_receipt_and_advice_point_to_resume(self):
        e = self.err(call("batch.run", {"ops": self.OPS}, timeoutMs=3000))
        self.assertIn("resume: '%s'" % e["details"]["receipt"]["callId"], e["hint"])
        adv = " ".join(call("batch.recover", {})["result"]["advice"])
        self.assertIn("resume", adv)


class ExpectedParams(Base):
    """[issue #13] Every INVALID_ARGS reply lists the operation's parameters, including errors raised inside the operation."""

    def test_error_inside_the_operation(self):
        e = self.err(call("test.add", {"names": [""]}))
        self.assertEqual(e["code"], "INVALID_ARGS")
        self.assertEqual(e["details"]["expected"], ["names: array (required)"])
        self.assertIn("details.expected", e["hint"])

    def test_failed_batch_child(self):
        e = self.err(call("batch.run", {"ops": [{"operation": "test.add", "args": {"names": [""]}}]}))
        child = e["details"]["results"][0]["error"]
        self.assertEqual(child["details"]["expected"], ["names: array (required)"])

    def test_schema_error_lists_enums_and_defaults(self):
        e = self.err(call("test.hang", {"seconds": 1, "add": "during"}))
        self.assertIn("add: string (optional, one of before|after)", e["details"]["expected"])
        self.assertIn("seconds: number (optional, default 30)", e["details"]["expected"])


class JournalUnits(unittest.TestCase):
    def test_torn_last_line_and_ranges(self):
        from fusion_connector import journal
        cid = "unit-" + os.urandom(3).hex()
        os.environ["FUSION_MCP_OUT_DIR"] = os.path.join(TMP, "unit_out")
        try:
            with open(journal.path_of(cid), "w") as f:
                f.write(json.dumps({"t": "call", "id": cid, "op": "batch.run", "children": ["a", "b", "c", "d", "e", "f"]}) + "\n")
                for i in (0, 1, 2, 4):
                    f.write(json.dumps({"t": "start", "i": i, "op": "x", "targets": []}) + "\n")
                    f.write(json.dumps({"t": "end", "i": i, "ok": True, "changed": {}}) + "\n")
                f.write('{"t": "start", "i": 5, "op": "y", "tar')                # the worker died mid-write
            rec = journal.reconcile(journal.read(cid))
            self.assertEqual([s["index"] for s in rec["completed"]], [0, 1, 2, 4])
            self.assertEqual(rec["notStarted"], [3, 5])
            self.assertIn("steps 0-2, 4 finished", rec["summary"])
        finally:
            os.environ["FUSION_MCP_OUT_DIR"] = ENV["FUSION_MCP_OUT_DIR"]

    def test_readback_catches_renamed_copies(self):
        from fusion_connector import testkit
        from fusion_connector.worker import resume_readback
        path = os.path.join(TMP, "unit_fake.json")
        testkit._save(path, {"tools": {n: {"reg": "F"} for n in ("RL_R1", "RL_R11", "Title", "Title_1", "Other")}, "groups": [], "data": {}})
        plan = {"callId": "x", "skip": {0: "done", 1: "done"}, "earlier": ["RL_R1", "Title"], "closedUndoGroup": False}
        rb = resume_readback(testkit.FakeComp(path), {"names": ["RL_R1", "Title"]}, plan, [])
        self.assertEqual(rb["evidence"]["duplicates"], ["RL_R11", "Title_1"])     # Fusion's _1 and an appended digit
        self.assertEqual(rb["evidence"]["unreported"], ["Other"])
        self.assertFalse(rb["verified"])

    def test_targets_and_changes(self):
        from fusion_connector import journal
        self.assertEqual(journal.targets_of({"tool": "Title", "input": "Size", "from": {"tool": "A", "input": "Output"}}), ["Title", "A"])
        self.assertEqual(journal.changes_of({"added": ["A"], "ok": True, "huge": "x" * 9}), {"added": ["A"]})
        self.assertEqual(len(journal.changes_of({"created": [str(i) for i in range(50)]})["created"]), 21)

    def test_fault_ops_refuse_a_real_resolve(self):
        from fusion_connector import testkit
        from fusion_connector.ops.base import OpError

        class Ctx:
            resolve = object()
        with self.assertRaises(OpError) as cm:
            testkit.t_add(Ctx(), None, {"names": ["A"]})
        self.assertEqual(cm.exception.code, "FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
