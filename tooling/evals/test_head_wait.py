#!/usr/bin/env python3
"""Runs dv:director-mode's head_wait.py against a fake `orca`, never the real one.

The fake keeps a bot's items, their links and events, automations, sessions and sent messages in
a JSON file under a lock, and answers with Orca's JSON envelopes (shapes read from Orca 1.4.277:
`bot item show|list|link|comment|set`, `automations create|edit|show`, `orchestration
send|request-show`, `agent show`). A link is added only if the item lacks it, under the lock, and
a second caller gets `unchanged`, as Orca does; events come 50 to a page. Faults make a chosen
call fail, answer something that isn't Orca's JSON, land and then error, hide a link's event from
one read (Orca's show reads the events before the item), or pause until the test releases it.

Two ways in:
  - in-process: the script's `_exec` is replaced, so its envelope parsing runs on the fake's
    bytes, a timeout can be raised, and its clock, pauses and budget can be changed;
  - subprocess: `python3 -I head_wait.py ...` with the fake first on PATH, for argv lists, the
    inert text round trip and runs that overlap in time (a paused run can also be killed).

Checked (each name below is printed with ok or FAIL):
  marker outcomes for reserve and claim (event id, unchanged, item_closed, the cap message, each
  refused code, items_unavailable, an unknown code, empty, non-JSON, a non-zero exit with no
  envelope, ok with a non-zero exit, a timeout, orca missing); claim refused with no W<k> marker;
  arm: ARMED, TAKEN with nothing else written, k from both marker kinds, BLOCKED cases, values
  refused before any call (the deadline gap and the owner's session among them), create
  verification mismatches closing unarmed with the claim before the UNARMED line, the Waiting
  write refused or overtaken or after a change or too close, an unreadable Waiting result read
  back, UNCHECKED, SPENT and UNREADABLE; the successor gate (a closed marker alone never lets
  W<k+1> arm; a paused winner blocks it until its closing record lands); close: one claim winner
  among concurrent closes, one send, the send only inside the winning run after its Re-send line
  and a fresh read, every reason the fresh check stops a send (the snooze rule, an earlier unclear
  send under the same key here or along the carry), an unclear send recorded with request-show run
  once, the winner's time window; notice rules; retire RETIRED, GONE, UNVERIFIED; reconcile note,
  the 15-minute rule, --final unarmed, DUPLICATE and UNCHECKED; close-unarmed's second read;
  rewake's outcomes, each rewake hold with no create call, two rewakes that each read seven
  claims of which exactly one creates, and an uncertain create counting against the limit; the
  first read's tries and the spent budget; items past one page of events;
  a read missing a marker's event; FULL with the Wait blocked line, carrying to a fresh item;
  restart is read-only and lists each finding; argv lists only, every value checked before the
  first call, and free text reaching Orca byte for byte without running; a cleanup failure after
  a send.

Stdlib only, no network.

    python3 tooling/evals/test_head_wait.py [path/to/head_wait.py]
"""

from __future__ import annotations

import ast
import contextlib
import fcntl
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "plugins" / "dv" / "skills" / "director-mode" / "scripts" / "head_wait.py"
BOT_NAME, BOT_ID = "Head of Skills", "d2a3a17d-217b-4549-be5e-3d7a5d0cfdc4"
CHAT = "2269cda5-b698-4d56-bae1-44a588c295cf"
OWNER_S, WAIT_S = "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"
OWNER_ADDR = f"orca_session_id:{OWNER_S}"
KEY = f"VIL-1218/{WAIT_S}/Q3"

failures: list = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("ok   " if ok else "FAIL ") + name)
    if not ok:
        failures.append(name + (f"\n     {detail}" if detail else ""))


# ------------------------------------------------------------------------------ the fake


def iso_ms(t: float) -> int:
    return int(t * 1000)


class FakeOrca:
    """Orca's item, automation, mail and agent calls over a JSON state file."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.state_path = root / "state.json"
        self.log_path = root / "log.jsonl"
        self.lock_path = root / "state.lock"

    # -- state

    def init(self, items: dict | None = None) -> None:
        state = {"items": {}, "events": [], "next_event": 100, "automations": {},
                 "sessions": {OWNER_S: True, WAIT_S: True}, "messages": [], "faults": [],
                 "requests": {}}
        self.save(state)
        for n, spec in (items or {}).items():
            self.add_item(n, **spec)

    def load(self) -> dict:
        return json.loads(self.state_path.read_text())

    def save(self, state: dict) -> None:
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state))
        os.replace(tmp, self.state_path)

    @contextlib.contextmanager
    def locked(self):
        with open(self.lock_path, "a") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                state = self.load()
                yield state
                self.save(state)
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

    def add_item(self, n: int, status: str = "in_progress", links: int = 0, bot: str = BOT_ID,
                 name: str = BOT_NAME) -> None:
        with self.locked() as st:
            st["items"][str(n)] = {"number": n, "status": status, "wait": None,
                                   "snoozedUntil": None, "owner": {"botId": bot, "name": name},
                                   "links": [{"kind": "file", "ref": f"/tmp/dummy-{n}-{i}"}
                                             for i in range(links)], "version": 1}

    def event(self, st: dict, n: int, kind: str, data: dict, actor_bot: str = BOT_ID,
              chat: str = CHAT, at: float | None = None) -> str:
        st["next_event"] += 1
        eid = f"e{st['next_event']}"
        st["events"].append({"id": eid, "item": n, "kind": kind,
                             "actor": {"kind": "bot", "botId": actor_bot, "chatId": chat},
                             "data": data, "at": iso_ms(at if at is not None else time.time())})
        st["items"][str(n)]["version"] += 1
        return eid

    def fixture_link(self, n: int, ref: str, actor_bot: str = BOT_ID, at: float | None = None):
        with self.locked() as st:
            st["items"][str(n)]["links"].append({"kind": "file", "ref": ref})
            return self.event(st, n, "linked", {"links": ["file:" + ref]}, actor_bot, at=at)

    def fixture_comment(self, n: int, text: str, person: bool = False,
                        actor_bot: str = BOT_ID) -> str:
        with self.locked() as st:
            eid = self.event(st, n, "commented", {"text": text}, actor_bot)
            if person:  # the item's owner, a person, writing in the app
                st["events"][-1]["actor"] = {"kind": "owner"}
            return eid

    def fixture_status(self, n: int, status: str) -> None:
        with self.locked() as st:
            item = st["items"][str(n)]
            self.event(st, n, "status", {"from": item["status"], "to": status})
            item["status"] = status
            if status != "waiting":
                item["wait"] = None

    def set_fields(self, n: int, **fields) -> None:
        with self.locked() as st:
            st["items"][str(n)].update(fields)

    def fault(self, match: list, mode: str, times: int = 1, **extra) -> None:
        with self.locked() as st:
            st["faults"].append({"match": match, "mode": mode, "times": times, **extra})

    def log(self) -> list:
        if not self.log_path.exists():
            return []
        return [json.loads(l) for l in self.log_path.read_text().splitlines() if l.strip()]

    def comments(self, n: int) -> list:
        return [e for e in self.load()["events"] if e["item"] == n and e["kind"] == "commented"]

    def item(self, n: int) -> dict:
        return self.load()["items"][str(n)]

    def refs(self, n: int) -> list:
        return [l["ref"] for l in self.item(n)["links"]]

    # -- calls

    def exec(self, argv: list) -> tuple:
        """argv without the leading orca. Returns (exit code, stdout bytes)."""
        fault = self.take_fault(argv)
        if fault and fault["mode"] == "pause":
            flag = Path(fault["flag"])
            (flag.parent / (flag.name + f".waiting.{os.getpid()}.{threading.get_ident()}")) \
                .write_text("")
            deadline = time.time() + 30
            while not flag.exists() and time.time() < deadline:
                time.sleep(0.05)
            fault = None
        if fault and fault["mode"] == "timeout":
            raise subprocess.TimeoutExpired(["orca"] + argv, 60)
        with self.locked() as st:
            with open(self.log_path, "a") as fh:
                fh.write(json.dumps(argv) + "\n")
            if fault:
                mode = fault["mode"]
                if mode == "garbage":
                    return 0, b"not json at all"
                if mode == "empty":
                    return 0, b""
                if mode == "exit1":
                    return 1, b""
                if mode == "ok-exit1":
                    return 1, json.dumps({"ok": True, "result": {"eventId": "e1"}}).encode()
                if mode == "ok-noevent":
                    return 0, json.dumps({"ok": True, "result": {"item": {}}}).encode()
                if mode == "nocode":
                    return 1, json.dumps({"ok": False, "error": {"message": "x"}}).encode()
                if mode == "error":
                    return 1, self.err(fault["code"], fault.get("message", "stubbed"),
                                       fault.get("data"))
                if mode == "after-error":
                    code, out = self.dispatch(st, argv, fault)
                    return 1, self.err(fault["code"], fault.get("message", "after the write"))
            return self.dispatch(st, argv, fault)

    def take_fault(self, argv: list) -> dict | None:
        with self.locked() as st:
            for f in st["faults"]:
                if f["times"] <= 0 or argv[:len(f["match"])] != f["match"]:
                    continue
                if f.get("ref") and f["ref"] not in argv:
                    continue
                if f.get("skip", 0) > 0:
                    f["skip"] -= 1
                    continue
                if f.get("text_prefix"):
                    path = argv[argv.index("--text-file") + 1] if "--text-file" in argv else None
                    if not path or not Path(path).read_text().startswith(f["text_prefix"]):
                        continue
                f["times"] -= 1
                return dict(f)
        return None

    @staticmethod
    def ok(result: dict) -> bytes:
        return json.dumps({"id": str(uuid.uuid4()), "ok": True, "result": result,
                           "_meta": {"runtimeId": "fake"}}, indent=2).encode()

    @staticmethod
    def err(code: str, message: str, data: dict | None = None) -> bytes:
        error = {"code": code, "message": message}
        if data:
            error["data"] = data
        return json.dumps({"id": str(uuid.uuid4()), "ok": False, "error": error,
                           "_meta": {"runtimeId": "fake"}}, indent=2).encode()

    @staticmethod
    def flag(argv: list, name: str) -> str | None:
        return argv[argv.index(name) + 1] if name in argv else None

    def view(self, st: dict, n: int) -> dict:
        return dict(st["items"][str(n)])

    def dispatch(self, st: dict, argv: list, fault: dict | None) -> tuple:
        f = lambda name: self.flag(argv, name)
        head = argv[:3]
        if head == ["bot", "item", "show"]:
            n = f("--id")
            if n not in st["items"]:
                return 1, self.err("not_found", f"No item {n} on this computer.")
            after = f("--after")
            low = int(after[1:]) if after else 0
            evs = [e for e in st["events"] if e["item"] == int(n) and int(e["id"][1:]) > low]
            if fault and fault["mode"] == "hide-link":  # Orca reads events before the item
                evs = [e for e in evs if not (e["kind"] == "linked"
                                              and "file:" + fault["hide"] in e["data"]["links"])]
            if fault and fault["mode"] == "hide-comment":
                evs = [e for e in evs if not (e["kind"] == "commented"
                                              and e["data"]["text"].startswith(fault["hide"]))]
            page = [{k: v for k, v in e.items() if k != "item"} for e in evs[:50]]
            result = {"item": self.view(st, int(n)), "events": page}
            if len(evs) > 50:
                result["nextCursor"] = page[-1]["id"]
            return 0, self.ok(result)
        if head == ["bot", "item", "list"]:
            wanted = [s.replace("-", "_") for s in (f("--status") or "").split(",")]
            items = [self.view(st, int(k)) for k in st["items"]
                     if st["items"][k]["status"] in wanted]
            return 0, self.ok({"botId": BOT_ID, "botName": BOT_NAME, "items": items,
                               "counts": {}})
        if head[:3] in (["bot", "item", "link"], ["bot", "item", "comment"],
                        ["bot", "item", "set"]):
            n = f("--id")
            if n not in st["items"]:
                return 1, self.err("not_found", f"No item {n} on this computer.")
            item = st["items"][n]
            closed = item["status"] in ("done", "canceled")
            if head[2] == "link":
                if closed:
                    return 1, self.err("item_closed", f"Item {n} is {item['status']}.")
                ref = f("--ref")
                if any(l["ref"] == ref for l in item["links"]):
                    return 0, self.ok({"item": self.view(st, int(n)), "eventId": None,
                                       "unchanged": True})
                if len(item["links"]) >= 50:
                    return 1, self.err("invalid_argument", "An item takes up to 50 links.")
                item["links"].append({"kind": "file", "ref": ref})
                eid = self.event(st, int(n), "linked", {"links": ["file:" + ref]})
                return 0, self.ok({"item": self.view(st, int(n)), "eventId": eid})
            if head[2] == "comment":
                text = Path(f("--text-file")).read_text(encoding="utf-8")
                if len(text) > 8000:
                    return 1, self.err("invalid_argument", "text is too long")
                eid = self.event(st, int(n), "commented", {"text": text})
                return 0, self.ok({"item": self.view(st, int(n)), "eventId": eid})
            # set
            status = f("--status")
            if status == "waiting" and item["status"] == "needs_you":
                return 1, self.err("invalid_argument", f"Item {n} waits on your owner's answer. "
                                   "It stays Needs you; put the wait in a comment.")
            if closed:
                return 1, self.err("item_closed", f"Item {n} is {item['status']}.")
            note = Path(f("--note-file")).read_text().strip()
            comment = Path(f("--comment-file")).read_text() if f("--comment-file") else None
            eid = None
            if comment:
                eid = self.event(st, int(n), "commented", {"text": comment})
            sid = self.event(st, int(n), "status", {"from": item["status"], "to": "waiting",
                                                    "note": note})
            item["status"] = "waiting"
            item["wait"] = {"text": note, "at": iso_ms(time.time()) + int(sid[1:])}
            return 0, self.ok({"item": self.view(st, int(n)), "eventId": sid})
        if argv[:2] == ["automations", "create"]:
            bot = f("--bot")
            if bot != BOT_NAME:
                return 1, self.err("invalid_argument", f"No bot named {bot}.")
            by = f("--by")
            import datetime as _dt
            by_ms = int(_dt.datetime.fromisoformat(by).timestamp() * 1000)
            if by_ms <= iso_ms(time.time()):
                return 1, self.err("invalid_argument", "--by must be a time in the future")
            aid = str(uuid.uuid4())
            auto = {"id": aid, "name": f("--name"), "prompt": f("--prompt"), "enabled": True,
                    "once": {"by": by_ms}, "bot": {"botId": BOT_ID, "runsIn": "chat"},
                    "on": None, "nextRunAt": None}
            if fault and fault["mode"] == "mutate":
                for k, v in fault["fields"].items():
                    auto[k] = v
            st["automations"][aid] = auto
            return 0, self.ok({"automation": auto})
        if argv[:2] in (["automations", "edit"], ["automations", "show"]):
            aid = f("--id")
            if aid not in st["automations"]:
                return 1, self.err("runtime_error", "Automation not found.")
            if argv[1] == "edit" and "--disabled" in argv and not (fault and
                                                                    fault["mode"] == "noop"):
                st["automations"][aid]["enabled"] = False
            return 0, self.ok({"automation": st["automations"][aid], "owner": None})
        if argv[:2] == ["orchestration", "send"]:
            body = Path(f("--body-file")).read_text(encoding="utf-8")
            msg = "msg_" + uuid.uuid4().hex[:12]
            st["messages"].append({"id": msg, "to": f("--to"), "subject": f("--subject"),
                                   "type": f("--type"), "body": body})
            return 0, json.dumps({"ok": True, "result": {"messageId": msg}}).encode()
        if argv[:2] == ["orchestration", "request-show"]:
            return 0, self.ok({"state": "absent"})
        if argv[:2] == ["agent", "show"]:
            sid = argv[2].split(":", 1)[-1]
            if not st["sessions"].get(sid):
                return 1, self.err("agent_unknown", f"No agent {argv[2]} on this Orca.")
            return 0, self.ok({"orcaSessionId": sid, "places": [{"state": "done"}]})
        return 99, f"fake orca: unknown command {argv}".encode()


FAKE_MAIN = r'''#!/usr/bin/env python3
import os, sys
sys.path.insert(0, os.environ["FAKE_ORCA_DIR"])
from test_head_wait import FakeOrca
from pathlib import Path
code, out = FakeOrca(Path(os.environ["FAKE_ORCA_ROOT"])).exec(sys.argv[1:])
sys.stdout.write(out.decode())
sys.exit(code)
'''


# ------------------------------------------------------------------------------ harness


def load_module():
    spec = importlib.util.spec_from_file_location("head_wait_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


HW = None  # the script as a module, loaded by main() (the fake imports this file too)


class Case:
    """A temp root with the fake, a scratch dir for the Head's files and a bin/ with orca."""

    def __init__(self, items: dict | None = None) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="hw-test-"))
        self.files = self.root / "scratch"
        self.files.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        orca = self.bin / "orca"
        orca.write_text(FAKE_MAIN)
        orca.chmod(0o755)
        self.fake = FakeOrca(self.root)
        self.fake.init(items)

    def close(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def env(self) -> dict:
        env = dict(os.environ)
        env["PATH"] = f"{self.bin}{os.pathsep}{env.get('PATH', '')}"
        env["FAKE_ORCA_DIR"] = str(Path(__file__).resolve().parent)
        env["FAKE_ORCA_ROOT"] = str(self.root)
        return env

    def run(self, *args: str) -> tuple:
        p = subprocess.run([sys.executable, "-I", str(SCRIPT), *args], capture_output=True,
                           text=True, env=self.env(), timeout=120)
        return p.returncode, p.stdout.strip(), p.stderr

    def popen(self, *args: str) -> subprocess.Popen:
        return subprocess.Popen([sys.executable, "-I", str(SCRIPT), *args], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, env=self.env())

    @contextlib.contextmanager
    def inproc(self):
        """Run the script's functions here, with _exec answered by the fake."""
        saved = HW._exec
        HW._exec = lambda argv, timeout: self.fake.exec(argv[1:])
        try:
            yield HW
        finally:
            HW._exec = saved

    def write(self, n: int, k: int, part: str, text: str) -> str:
        path = self.files / f"item-{n}-W{k}-{part}.txt"
        path.write_bytes(text.encode("utf-8"))
        return str(path)

    def arm_args(self, n: int, k: int, target_s: float = 900, deadline_s: float = 1800,
                 record: str | None = None, **over) -> list:
        import datetime as _dt
        def stamp(sec):
            t = _dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(seconds=sec)
            t = t.replace(second=0, microsecond=0) + _dt.timedelta(minutes=1)
            return t.strftime("%Y-%m-%dT%H:%M:00+00:00")
        values = {"item": str(n), "wait": f"W{k}", "target": stamp(target_s),
                  "deadline": stamp(deadline_s), "owner": OWNER_ADDR, "owner-session": OWNER_S,
                  "waiting-session": WAIT_S, "ticket": "VIL-1218", "key": KEY,
                  "record-file": record or self.write(n, k, "record", "Waits on: the answer.\n")}
        values.update(over)
        out = ["arm"]
        for k_, v in values.items():
            if v is not None:
                out += [f"--{k_}", v]
        return out

    def arm(self, n: int, k: int, **over) -> tuple:
        return self.run(*self.arm_args(n, k, **over))

    def close_wait(self, n: int, k: int, case: str = "settled", trigger: str = "wake",
                   text: str | None = None, body: str | None = None, *extra: str) -> list:
        args = ["close", "--item", str(n), "--wait", f"W{k}", "--trigger", trigger, "--case",
                case, "--text-file", self.write(n, k, "disposition", text or (
                    "Evidence: the owner answered under the key; the session resumed.\n"
                    "Blocker: none\nNext check: none: settled\n"))]
        if body is not None:
            args += ["--body-file", self.write(n, k, "body", body)]
        return args + list(extra)


def calls(log: list, *prefix: str) -> list:
    return [c for c in log if c[:len(prefix)] == list(prefix)]


def paused_arm(c: Case, n: int, k: int, **over) -> tuple:
    """An arm stopped at its fresh read, after the reservation, the record and the wake."""
    flag = c.root / f"go-arm-{n}-{k}"
    c.fake.fault(["bot", "item", "show"], "pause", skip=1, flag=str(flag))
    x = c.popen(*c.arm_args(n, k, **over))
    return x, flag, wait_for_waiters(flag, 1)


def cut_arm(c: Case, n: int, k: int) -> bool:
    """An arm killed before its Waiting write: W<k>, a record and a wake, no Armed line."""
    x, flag, paused = paused_arm(c, n, k)
    x.kill()
    x.communicate(timeout=30)
    flag.write_text("")  # the fake's own process finishes its read and exits
    return paused


def in_main(hw, argv: list) -> tuple:
    """Run main() in-process; returns (exit code, stdout)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = hw.main(argv)
    return code, buf.getvalue().strip()


def record_line(n: int, k: int, target: str = "2099-01-01T00:00:00+00:00",
                deadline: str = "2099-01-01T01:00:00+00:00") -> str:
    return (f"Wait record, item {n} W{k}. Owner: {OWNER_ADDR} (session {OWNER_S}). Waiting work: "
            f"session {WAIT_S}. Ticket: VIL-1218. Key: {KEY}. Wake target: {target}. Deadline: "
            f"{deadline} (later). Item at arm: in_progress, wait none.\nWaits on: the answer.\n")


def wait_for_waiters(flag: Path, count: int, timeout: float = 20) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if len(list(flag.parent.glob(flag.name + ".waiting.*"))) >= count:
            return True
        time.sleep(0.05)
    return False


# ------------------------------------------------------------------------------ tests


def test_static() -> None:
    src = SCRIPT.read_text()
    tree = ast.parse(src)
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = ast.unparse(node.func) if hasattr(ast, "unparse") else ""
            if fn in ("os.system", "os.popen", "subprocess.Popen", "subprocess.call",
                      "subprocess.check_output", "subprocess.check_call", "eval", "exec"):
                bad.append(fn)
            if fn == "subprocess.run":
                if any(kw.arg == "shell" for kw in node.keywords):
                    bad.append("subprocess.run(shell=...)")
                if node.args and isinstance(node.args[0], (ast.Constant, ast.JoinedStr)):
                    bad.append("subprocess.run(str)")
    check("static: no shell, os.system, popen or eval; subprocess.run takes a list",
          not bad and src.count("subprocess.run(") == 1, str(bad))
    sends = [n for n in ast.walk(tree) if isinstance(n, ast.Constant) and n.value == "send"]
    check("static: one orchestration send call site, inside send_once",
          len(sends) == 1 and src.count("send_once(") == 2, str(len(sends)))
    plugin = json.loads((REPO_ROOT / "plugins/dv/.claude-plugin/plugin.json").read_text())
    check("version: the script's VERSION matches plugin.json", HW.VERSION == plugin["version"],
          f"{HW.VERSION} vs {plugin['version']}")


def test_outcomes() -> None:
    """reserve and claim map each Orca answer to the design's outcome words."""
    cases = [
        ("event id", None, "RESERVED", "CLAIMED"),
        ("unchanged", "pre-link", "TAKEN", "NOT CLAIMED"),
        ("item_closed", {"mode": "error", "code": "item_closed"}, "CLOSED", "CLOSED"),
        ("cap", {"mode": "error", "code": "invalid_argument",
                 "message": "An item takes up to 50 links."}, "FULL", "FULL"),
        ("not_found", {"mode": "error", "code": "not_found", "message": "No item."},
         "REFUSED", "REFUSED"),
        ("not_found after the write", {"mode": "error", "code": "not_found",
                                       "message": "The item is gone."}, "UNCLEAR", "UNCLEAR"),
        ("not_owner", {"mode": "error", "code": "not_owner"}, "REFUSED", "REFUSED"),
        ("items_read_only", {"mode": "error", "code": "items_read_only"}, "REFUSED", "REFUSED"),
        ("other invalid_argument", {"mode": "error", "code": "invalid_argument",
                                    "message": "An empty link."}, "REFUSED", "REFUSED"),
        ("items_unavailable", {"mode": "error", "code": "items_unavailable"},
         "UNCLEAR", "UNCLEAR"),
        ("unknown code", {"mode": "error", "code": "weird_code"}, "UNCLEAR", "UNCLEAR"),
        ("empty output", {"mode": "empty"}, "UNCLEAR", "UNCLEAR"),
        ("not JSON", {"mode": "garbage"}, "UNCLEAR", "UNCLEAR"),
        ("non-zero exit, no envelope", {"mode": "exit1"}, "UNCLEAR", "UNCLEAR"),
        ("ok with exit 1", {"mode": "ok-exit1"}, "UNCLEAR", "UNCLEAR"),
        ("ok with no event id", {"mode": "ok-noevent"}, "UNCLEAR", "UNCLEAR"),
        ("error with no code", {"mode": "nocode"}, "UNCLEAR", "UNCLEAR"),
        ("timeout", {"mode": "timeout"}, "UNCLEAR", "UNCLEAR"),
    ]
    for label, fault, want_reserve, want_claim in cases:
        for closed, want in ((False, want_reserve), (True, want_claim)):
            c = Case({7: {}})
            try:
                ref = f"head-wait/item-7/W1{'-closed' if closed else ''}"
                if closed:
                    c.fake.fixture_link(7, "head-wait/item-7/W1")
                if fault == "pre-link":
                    c.fake.fixture_link(7, ref)
                elif fault:
                    c.fake.fault(["bot", "item", "link"], fault["mode"], ref=ref,
                                 **{k: v for k, v in fault.items() if k != "mode"})
                with c.inproc() as hw:
                    word, _ = hw.link_marker(7, 1, closed)
                check(f"outcome: {'claim' if closed else 'reserve'} on {label} -> {want}",
                      word == want, word)
            finally:
                c.close()
    saved_orca = HW.ORCA
    HW.ORCA = "/nonexistent/orca-missing"
    try:
        word, _ = HW.link_marker(7, 1, True)
    finally:
        HW.ORCA = saved_orca
    check("outcome: orca missing -> REFUSED (nothing could have landed)", word == "REFUSED", word)
    c = Case({7: {}})
    try:
        code, out, _ = c.run("claim", "--item", "7", "--wait", "W1")
        check("claim: refused when the item has no W1 marker, and nothing is linked",
              out.startswith("REFUSED") and not calls(c.fake.log(), "bot", "item", "link"), out)
    finally:
        c.close()


def test_arm() -> None:
    c = Case({7: {}})
    try:
        code, out, _ = c.arm(7, 1)
        item = c.fake.item(7)
        autos = list(c.fake.load()["automations"].values())
        armed = [e for e in c.fake.comments(7) if e["data"]["text"].startswith("Armed, item 7 W1:")]
        check("arm: ARMED, Waiting with a W1 note, one enabled wake, an Armed line",
              code == 0 and out.startswith("ARMED item 7 W1") and item["status"] == "waiting"
              and item["wait"]["text"].startswith("W1 wake ") and len(autos) == 1
              and autos[0]["enabled"] and len(armed) == 1, out)
        check("arm: B1, the wake is not linked to the item (two marker links only)",
              c.fake.refs(7) == ["head-wait/item-7/W1"], str(c.fake.refs(7)))
        create = calls(c.fake.log(), "automations", "create")[0]
        check("arm: the create is an argv list with the fixed name and prompt and no --on/--item",
              create[create.index("--name") + 1] == "Item 7 W1" and "--on" not in create
              and "--item" not in create and create[create.index("--bot") + 1] == BOT_NAME
              and "Head's wake for a waiting item" in create[create.index("--prompt") + 1],
              str(create))
        code, out, _ = c.arm(7, 2)
        check("arm: a second wait is BLOCKED while W1 is open, nothing written",
              out.startswith("BLOCKED") and "W1 is open" in out
              and len(calls(c.fake.log(), "bot", "item", "link")) == 1, out)
    finally:
        c.close()

    c = Case({7: {}})
    try:
        c.fake.fixture_link(7, "head-wait/item-7/W1")
        code, out, _ = c.run(*c.arm_args(7, 1))
        check("arm: expected key already reserved -> BLOCKED (next is W1 open), nothing written",
              out.startswith("BLOCKED") and not calls(c.fake.log(), "bot", "item", "comment"), out)
    finally:
        c.close()

    # k from both marker kinds; a stray W3-closed counts past it
    c = Case({7: {}})
    try:
        c.fake.fixture_link(7, "head-wait/item-7/W1")
        c.fake.fixture_link(7, "head-wait/item-7/W1-closed")
        c.fake.fixture_comment(7, "UNARMED, item 7 W1: manual; wake none.\nOrca: x")
        c.fake.fixture_link(7, "head-wait/item-7/W3-closed")
        code, out, _ = c.run("check", "--item", "7")
        check("arm: k is one more than the highest marker of either kind (W4)",
              out == "IDLE item 7: no open wait; the next is W4", out)
        code, out, _ = c.arm(7, 2)
        check("arm: a stale expected key is BLOCKED", out.startswith("BLOCKED")
              and "next wait on this item is W4" in out, out)
        code, out, _ = c.arm(7, 4)
        check("arm: W4 arms past a stray W3-closed", out.startswith("ARMED item 7 W4"), out)
    finally:
        c.close()

    # TAKEN: reserved between the read and the reservation
    c = Case({7: {}})
    try:
        flag = c.root / "go"
        c.fake.fault(["bot", "item", "link"], "pause", ref="head-wait/item-7/W1", flag=str(flag))
        x = c.popen(*c.arm_args(7, 1))
        ok = wait_for_waiters(flag, 1)
        c.fake.fixture_link(7, "head-wait/item-7/W1")
        flag.write_text("")
        out, _ = x.communicate(timeout=60)
        log = c.fake.log()
        check("arm: TAKEN when another run reserved W1 after this run's read; no record, no "
              "automation, no W2", ok and out.startswith("TAKEN item 7 W1")
              and not calls(log, "bot", "item", "comment") and not calls(log, "automations")
              and "head-wait/item-7/W2" not in c.fake.refs(7), out)
    finally:
        c.close()

    # concurrent arms: one ARMED, one TAKEN
    c = Case({7: {}})
    try:
        flag = c.root / "go"
        c.fake.fault(["bot", "item", "link"], "pause", times=2, ref="head-wait/item-7/W1",
                     flag=str(flag))
        x, y = c.popen(*c.arm_args(7, 1)), c.popen(*c.arm_args(7, 1))
        both = wait_for_waiters(flag, 2)
        flag.write_text("")
        outs = sorted(p.communicate(timeout=90)[0].split("\n")[0] for p in (x, y))
        autos = c.fake.load()["automations"]
        check("arm: two concurrent arms of W1 give one ARMED and one TAKEN, one record, one wake",
              both and outs[0].startswith("ARMED") and outs[1].startswith("TAKEN")
              and len([e for e in c.fake.comments(7) if e["data"]["text"].startswith(
                  "Wait record")]) == 1 and len(autos) == 1, str(outs))
    finally:
        c.close()

    import datetime as _dt
    base = (_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(hours=2)).replace(
        second=0, microsecond=0)
    at = lambda minutes: (base + _dt.timedelta(minutes=minutes)).strftime(
        "%Y-%m-%dT%H:%M:00+00:00")
    for label, kwargs, want in (
            ("a target in the past", {"target_s": -600, "deadline_s": 600}, "BLOCKED"),
            ("a deadline before the target", {"target_s": 1800, "deadline_s": 600}, "REFUSED"),
            ("a deadline one minute after the target", {"target": at(0), "deadline": at(1)},
             "REFUSED"),
            ("an --owner naming another session than --owner-session",
             {"owner": "orca_session_id:" + WAIT_S}, "REFUSED")):
        c = Case({7: {}})
        try:
            code, out, _ = c.arm(7, 1, **kwargs)
            check(f"arm: {label} -> {want} before any Orca call", out.startswith(want)
                  and not c.fake.log(), out)
        finally:
            c.close()
    c = Case({7: {}})
    try:
        code, out, _ = c.arm(7, 1, target=at(0), deadline=at(2))
        check("arm: a deadline two minutes after the target arms", out.startswith("ARMED"), out)
    finally:
        c.close()

    for label, status in (("Needs you", "needs_you"), ("done", "done")):
        c = Case({7: {"status": status}})
        try:
            code, out, _ = c.arm(7, 1)
            check(f"arm: an item that reads {label} is BLOCKED, nothing written",
                  out.startswith("BLOCKED") and not calls(c.fake.log(), "bot", "item", "link"),
                  out)
        finally:
            c.close()

    c = Case({7: {"links": 49}})
    try:
        code, out, _ = c.arm(7, 1)
        check("arm: 49 links -> BLOCKED (a wait needs 2 free)", out.startswith("BLOCKED")
              and "49 links" in out, out)
    finally:
        c.close()
    c = Case({7: {"links": 48}})
    try:
        code, out, _ = c.arm(7, 1)
        check("arm: 48 links -> ARMED (49 after)", out.startswith("ARMED")
              and len(c.fake.item(7)["links"]) == 49, out)
    finally:
        c.close()

    # create verification mismatches close unarmed, with the claim before the UNARMED line
    mismatches = [("disabled", {"enabled": False}), ("once.by off", {"once": {"by": 1}}),
                  ("another bot", {"bot": {"botId": "other"}}),
                  ("an event trigger", {"on": [{"source": "github"}]})]
    for label, fields in mismatches:
        c = Case({7: {}})
        try:
            c.fake.fault(["automations", "create"], "mutate", fields=fields)
            code, out, _ = c.arm(7, 1)
            evs = c.fake.load()["events"]
            claim = [e for e in evs if e["kind"] == "linked"
                     and e["data"]["links"] == ["file:head-wait/item-7/W1-closed"]]
            unarmed = [e for e in evs if e["kind"] == "commented"
                       and e["data"]["text"].startswith("UNARMED, item 7 W1: verify;")]
            auto = list(c.fake.load()["automations"].values())[0]
            check(f"arm: a wake read back with {label} closes unarmed: claim, then UNARMED, "
                  "wake retired, status unchanged",
                  out.startswith("UNARMED item 7 W1") and claim and unarmed
                  and int(claim[0]["id"][1:]) < int(unarmed[0]["id"][1:])
                  and auto["enabled"] is False and c.fake.item(7)["status"] == "in_progress", out)
        finally:
            c.close()

    c = Case({7: {}})
    try:
        c.fake.fault(["automations", "create"], "error", code="invalid_argument",
                     message="No bot named Nobody.")
        code, out, _ = c.arm(7, 1)
        un = [e["data"]["text"] for e in c.fake.comments(7) if e["data"]["text"].startswith(
            "UNARMED")]
        check("arm: a refused create closes unarmed naming Orca's error, wake none",
              out.startswith("UNARMED item 7 W1: create") and un and "wake none." in un[0]
              and "No bot named Nobody." in un[0] and not c.fake.load()["automations"], out)
    finally:
        c.close()
    c = Case({7: {}})
    try:
        c.fake.fault(["automations", "create"], "garbage")
        code, out, _ = c.arm(7, 1)
        un = [e["data"]["text"] for e in c.fake.comments(7) if e["data"]["text"].startswith(
            "UNARMED")]
        check("arm: an unreadable create closes unarmed with wake unknown",
              out.startswith("UNARMED") and un and "wake unknown." in un[0], out)
    finally:
        c.close()

    # the Waiting step, with the arm held at its fresh read
    c = Case({7: {}})
    try:
        x, flag, paused = paused_arm(c, 7, 1)
        c.fake.fixture_link(7, "head-wait/item-7/W1-closed")
        flag.write_text("")
        out, _ = x.communicate(timeout=60)
        check("waiting: W1-closed linked before the Waiting write -> OVERTAKEN, no Waiting write, "
              "no UNARMED", paused and out.startswith("OVERTAKEN item 7 W1")
              and x.returncode == 3 and not calls(c.fake.log(), "bot", "item", "set")
              and not [e for e in c.fake.comments(7) if e["data"]["text"].startswith("UNARMED")],
              out)
    finally:
        c.close()

    for label, change, want_status, want in (
            ("set Needs you between create and Waiting", "needs_you", "needs_you",
             "UNARMED item 7 W1: item-changed"),
            ("marked done between create and Waiting", "done", "done", "CLOSED item 7 W1")):
        c = Case({7: {}})
        try:
            x, flag, paused = paused_arm(c, 7, 1)
            c.fake.fixture_status(7, change)
            flag.write_text("")
            out, _ = x.communicate(timeout=60)
            autos = list(c.fake.load()["automations"].values())
            linked = "head-wait/item-7/W1-closed" in c.fake.refs(7)
            check(f"waiting: item {label} -> {want.split()[0]}, no Waiting write, status stays, "
                  "wake retired", paused and out.startswith(want)
                  and c.fake.item(7)["status"] == want_status and len(autos) == 1
                  and autos[0]["enabled"] is False and linked == (change != "done")
                  and not calls(c.fake.log(), "bot", "item", "set"), out)
        finally:
            c.close()

    # what the read after the Waiting write finds
    c = Case({7: {}})
    try:
        c.fake.fault(["bot", "item", "show"], "error", code="items_unavailable", skip=2)
        code, out, _ = c.arm(7, 1)
        check("arm: a failed read after the Waiting write -> UNCHECKED (exit 1), not ARMED",
              code == 1 and out.startswith("UNCHECKED item 7 W1: Waiting written")
              and c.fake.item(7)["status"] == "waiting", out)
    finally:
        c.close()
    c = Case({7: {}})
    try:
        flag = c.root / "go"
        c.fake.fault(["bot", "item", "show"], "pause", skip=2, flag=str(flag))
        x = c.popen(*c.arm_args(7, 1))
        paused = wait_for_waiters(flag, 1)
        c.fake.fixture_link(7, "head-wait/item-7/W1-closed")
        flag.write_text("")
        out, _ = x.communicate(timeout=60)
        check("arm: W1-closed linked right after the Waiting write -> SPENT (exit 3), not ARMED",
              paused and x.returncode == 3 and out.startswith("SPENT item 7 W1"), out)
    finally:
        c.close()

    c = Case({7: {}})
    try:
        c.fake.fault(["bot", "item", "show"], "error", code="not_found",
                     message="No item 7 on this computer.")
        code, out, _ = c.arm(7, 1)
        check("arm: an item it can't read -> UNREADABLE (exit 1), nothing written",
              code == 1 and out.startswith("UNREADABLE item 7 W1")
              and not calls(c.fake.log(), "bot", "item", "link"), out)
    finally:
        c.close()

    c = Case({7: {}})
    try:
        c.fake.fault(["bot", "item", "set"], "error", code="invalid_argument",
                     message="Item 7 waits on your owner's answer. It stays Needs you.")
        code, out, _ = c.arm(7, 1)
        check("waiting: Orca refusing the Waiting write -> closed unarmed",
              out.startswith("UNARMED item 7 W1: waiting") and "It stays Needs you" in out, out)
    finally:
        c.close()
    c = Case({7: {}})
    try:
        c.fake.fault(["bot", "item", "set"], "after-error", code="items_unavailable")
        code, out, _ = c.arm(7, 1)
        check("waiting: a Waiting write that errors after landing reads back as ARMED",
              out.startswith("ARMED item 7 W1"), out)
    finally:
        c.close()
    c = Case({7: {}})
    try:
        c.fake.fault(["bot", "item", "set"], "error", code="items_unavailable")
        code, out, _ = c.arm(7, 1)
        check("waiting: an unclear Waiting write that did not land -> closed unarmed",
              out.startswith("UNARMED item 7 W1: waiting")
              and c.fake.item(7)["status"] == "in_progress", out)
    finally:
        c.close()
    c = Case({7: {}})
    try:
        c.fake.fault(["bot", "item", "comment"], "error", code="items_unavailable",
                     text_prefix="Wait record")
        code, out, _ = c.arm(7, 1)
        check("arm: a record that doesn't post -> closed unarmed, no automation",
              out.startswith("UNARMED item 7 W1: record") and not c.fake.load()["automations"],
              out)
    finally:
        c.close()


def armed_case(n: int = 7, **items) -> Case:
    c = Case({n: items})
    code, out, _ = c.arm(n, 1)
    assert out.startswith("ARMED"), out
    return c


def test_close() -> None:
    c = armed_case()
    try:
        code, out, _ = c.run("check", "--item", "7", "--wait", "W1")
        check("check: an armed wait reads OPEN with its record, owner and wake",
              code == 0 and out.startswith("OPEN item 7 W1") and OWNER_ADDR in out, out)
        code, out, _ = c.run(*c.close_wait(7, 1, "re-sent", body="The question, as asked.\n",
                                           text="Evidence: no answer.\nBlocker: no answer yet\n"
                                                "Next check: W2 at the next target\n"))
        msgs = c.fake.load()["messages"]
        texts = [e["data"]["text"] for e in c.fake.comments(7)]
        log = c.fake.log()
        resend_idx = next((i for i, a in enumerate(log) if a[:3] == ["bot", "item", "comment"]
                           and Path(a[a.index("--text-file") + 1]).name == "resend.txt"), 10 ** 9)
        send_idx = next((i for i, a in enumerate(log) if a[:2] == ["orchestration", "send"]), -1)
        show_idx = [i for i, a in enumerate(log) if a[:2] == ["agent", "show"]] or [10 ** 9]
        check("close: re-sent from the winning run: one send to the record's owner, fixed "
              "subject, Re-send line first, fresh checks before it",
              code == 0 and out.startswith("CLAIMED item 7 W1: re-sent") and len(msgs) == 1
              and msgs[0]["to"] == OWNER_ADDR
              and msgs[0]["subject"] == "Re-sent by the Head: item 7 W1"
              and resend_idx < send_idx and len(show_idx) == 2 and max(show_idx) < resend_idx
              and any(t.startswith("Wake disposition, item 7 W1: re-sent.") for t in texts), out)
        check("close: the re-sent body starts with the record's key and ticket",
              msgs[0]["body"].startswith(f"Re-sent by the Head: item 7 W1. Key: {KEY}. Ticket: "
                                         "VIL-1218.") if msgs else False)
        code, out, _ = c.run(*c.close_wait(7, 1, "re-sent", body="Again.\n",
                                           text="Evidence: x\nBlocker: x\nNext check: x\n"))
        check("close: a repeated close (late wake, replayed notice) gets NOT CLAIMED, sends "
              "nothing, writes nothing", out.startswith("NOT CLAIMED")
              and len(c.fake.load()["messages"]) == 1
              and len(c.fake.comments(7)) == len(texts), out)
        code, out, _ = c.run("check", "--item", "7", "--wait", "W1")
        check("check: a stale wake's first step sees CLOSED and stops", code == 3
              and out.startswith("CLOSED item 7 W1: closing record"), out)
        code, out, _ = c.arm(7, 2)
        check("arm: W2 arms after W1's verified disposition", out.startswith("ARMED item 7 W2"),
              out)
    finally:
        c.close()

    # a done item: the wake's check and its claim both stop, nothing written
    c = armed_case()
    try:
        c.fake.fixture_status(7, "done")
        n_events = len(c.fake.load()["events"])
        code, out, _ = c.run("check", "--item", "7", "--wait", "W1")
        code2, out2, _ = c.run(*c.close_wait(7, 1, "no-follow-up", "wake",
                                             "Evidence: done\nBlocker: none\nNext check: none\n"))
        check("close: on a done item the check reads CLOSED and the claim is CLOSED; no event, "
              "no send", out.startswith("CLOSED item 7 W1: the item is done")
              and out2.startswith("CLOSED item 7 W1") and not c.fake.load()["messages"]
              and len(c.fake.load()["events"]) == n_events, out + " | " + out2)
    finally:
        c.close()

    # concurrent closes: one claim winner, one send
    c = armed_case()
    try:
        flag = c.root / "go"
        c.fake.fault(["bot", "item", "link"], "pause", times=2,
                     ref="head-wait/item-7/W1-closed", flag=str(flag))
        args = c.close_wait(7, 1, "re-sent", body="Q.\n",
                            text="Evidence: e\nBlocker: b\nNext check: n\n")
        x, y = c.popen(*args), c.popen(*args)
        both = wait_for_waiters(flag, 2)
        flag.write_text("")
        outs = sorted(p.communicate(timeout=90)[0].split("\n")[0] for p in (x, y))
        disp = [e for e in c.fake.comments(7) if e["data"]["text"].startswith("Wake disposition")]
        check("close: two overlapping closes give one CLAIMED, one NOT CLAIMED, one disposition, "
              "one send", both and outs[0].startswith("CLAIMED")
              and outs[1].startswith("NOT CLAIMED") and len(disp) == 1
              and len(c.fake.load()["messages"]) == 1, str(outs))
    finally:
        c.close()

    # the fresh check stops a send
    stops = [
        ("Orca's snooze ahead", lambda c: c.fake.set_fields(7, snoozedUntil=int(
            (time.time() + 3600) * 1000)), "no follow-up"),
        ("a Snoozed until line with an ISO time ahead", lambda c: c.fake.fixture_comment(
            7, "Snoozed until 2099-01-01T00:00:00Z: holiday"), "no follow-up"),
        ("an undated Snoozed until line after the record", lambda c: c.fake.fixture_comment(
            7, "Snoozed until 23:00 PT Nov 26 / 07:00 UTC Nov 27: waiting on David"),
         "no follow-up"),
        ("Needs you", lambda c: c.fake.fixture_status(7, "needs_you"), "no follow-up"),
        ("the owner session closed", lambda c: c.fake.save(
            {**c.fake.load(), "sessions": {OWNER_S: False, WAIT_S: True}}), "not settled"),
        ("the waiting session closed", lambda c: c.fake.save(
            {**c.fake.load(), "sessions": {OWNER_S: True, WAIT_S: False}}), "not settled"),
        ("the Re-send line not posting", lambda c: c.fake.fault(
            ["bot", "item", "comment"], "error", code="invalid_argument", text_prefix="Re-send"),
         "not settled"),
    ]
    for label, setup, want in stops:
        c = armed_case()
        try:
            setup(c)
            code, out, _ = c.run(*c.close_wait(7, 1, "re-sent", body="Q.\n",
                                               text="Evidence: e\nBlocker: b\nNext check: n\n"))
            disp = [e["data"]["text"] for e in c.fake.comments(7)
                    if e["data"]["text"].startswith("Wake disposition")]
            check(f"close: {label} stops the re-send; first word NOT SENT; recorded as {want}",
                  out.startswith("NOT SENT item 7 W1") and not c.fake.load()["messages"] and disp
                  and disp[0].startswith(f"Wake disposition, item 7 W1: {want}.")
                  and "Planned: re-sent" in disp[0], out)
        finally:
            c.close()

    c = armed_case()
    try:
        c.fake.fixture_comment(7, "Snoozed until 2000-01-01T00:00:00Z: long over")
        code, out, _ = c.run(*c.close_wait(7, 1, "re-sent", body="Q.\n",
                                           text="Evidence: e\nBlocker: b\nNext check: n\n"))
        check("close: an expired dated snooze line does not stop the send",
              len(c.fake.load()["messages"]) == 1, out)
    finally:
        c.close()

    # an unclear send: request-show once, never sent again
    c = armed_case()
    try:
        req = str(uuid.uuid4())
        c.fake.fault(["orchestration", "send"], "error", code="delivery_unknown",
                     message="lost", data={"orchestrationRequestId": req})
        code, out, _ = c.run(*c.close_wait(7, 1, "re-sent", body="Q.\n",
                                           text="Evidence: e\nBlocker: b\nNext check: n\n"))
        log = c.fake.log()
        disp = [e["data"]["text"] for e in c.fake.comments(7)
                if e["data"]["text"].startswith("Wake disposition")]
        check("close: an unclear send prints SEND UNCLEAR, runs request-show once, records the "
              "request id, and the case is not settled with blocker re-send unclear",
              out.startswith("SEND UNCLEAR item 7 W1") and code == 1
              and len(calls(log, "orchestration", "send")) == 1
              and len(calls(log, "orchestration", "request-show")) == 1
              and disp and disp[0].startswith("Wake disposition, item 7 W1: not settled.")
              and req in disp[0] and "Blocker: re-send unclear." in disp[0], out)
        code, out, _ = c.run(*c.close_wait(7, 1, "re-sent", body="Q.\n",
                                           text="Evidence: e\nBlocker: b\nNext check: n\n"))
        check("close: no second send for that wait", out.startswith("NOT CLAIMED")
              and len(calls(c.fake.log(), "orchestration", "send")) == 1, out)
    finally:
        c.close()

    c = armed_case()
    try:
        c.fake.fault(["orchestration", "send"], "timeout")
        with c.inproc() as hw:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                hw.main(c.close_wait(7, 1, "re-sent", body="Q.\n",
                                     text="Evidence: e\nBlocker: b\nNext check: n\n"))
        disp = [e["data"]["text"] for e in c.fake.comments(7)
                if e["data"]["text"].startswith("Wake disposition")]
        check("close: a send that times out is not settled with no request id, not repeated",
              disp and "no request id printed. Not sent again." in disp[0]
              and not calls(c.fake.log(), "orchestration", "request-show"), buf.getvalue())
    finally:
        c.close()

    # the winner's time window
    c = armed_case()
    try:
        with c.inproc() as hw:
            real_now, real_mono = hw.now_s, hw.mono
            shift = {"s": 0.0}
            hw.now_s = lambda: real_now() + shift["s"]
            hw.mono = lambda: real_mono() + shift["s"]
            saved = hw._exec

            def exec_and_jump(argv, timeout):
                out = saved(argv, timeout)
                if argv[1:4] == ["bot", "item", "link"] and argv[-2].endswith("W1-closed"):
                    shift["s"] = 400.0
                return out
            hw._exec = exec_and_jump
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    hw.main(c.close_wait(7, 1, "re-sent", body="Q.\n",
                                         text="Evidence: e\nBlocker: b\nNext check: n\n"))
            finally:
                hw.now_s, hw.mono, hw._exec = real_now, real_mono, saved
        texts = [e["data"]["text"] for e in c.fake.comments(7)]
        check("close: a winner past its 5-minute window sends nothing and posts nothing",
              buf.getvalue().startswith("UNCLEAR item 7 W1: claimed, but out of time")
              and not c.fake.load()["messages"]
              and not any(t.startswith(("Wake disposition", "Re-send")) for t in texts),
              buf.getvalue())
    finally:
        c.close()

    # notice rules
    c = armed_case()
    try:
        n_before = len(c.fake.log())
        code, out, _ = c.run(*c.close_wait(7, 1, "re-sent", "notice", None, "Q.\n"))
        check("notice: re-sent is refused before any call", code == 2
              and "notice closes only as" in out and len(c.fake.log()) == n_before, out)
        n_before = len(c.fake.log())
        code, out, _ = c.run(*c.close_wait(7, 1, "not-settled", "notice",
                                           "Evidence: e\nBlocker: wake gone\nNext check: n\n"))
        check("notice: not settled is refused while the wake is enabled",
              out.startswith("REFUSED") and "enabled" in out
              and not calls(c.fake.log()[n_before:], "bot", "item", "link"), out)
        code, out, _ = c.run(*c.close_wait(7, 1, "settled", "notice"))
        wake = list(c.fake.load()["automations"].values())[0]
        check("notice: settled -> CLAIMED, disposition, then the wake RETIRED, no send",
              out.startswith("CLAIMED item 7 W1: settled") and "RETIRED" in out
              and wake["enabled"] is False and not c.fake.load()["messages"], out)
    finally:
        c.close()
    c = armed_case()
    try:
        auto = list(c.fake.load()["automations"])[0]
        st = c.fake.load()
        del st["automations"][auto]
        c.fake.save(st)
        code, out, _ = c.run(*c.close_wait(7, 1, "not-settled", "notice",
                                           "Evidence: e\nBlocker: wake gone\nNext check: n\n"))
        check("notice: not settled once the wake is gone", out.startswith(
            "CLAIMED item 7 W1: not settled"), out)
    finally:
        c.close()

    # sections required
    c = armed_case()
    try:
        n_before = len(c.fake.log())
        code, out, _ = c.run(*c.close_wait(7, 1, "not-settled", "wake", "Evidence: only\n"))
        check("close: a disposition other than settled needs Blocker and Next check lines",
              code == 2 and "Blocker:" in out and len(c.fake.log()) == n_before, out)
    finally:
        c.close()


def test_successor_gate() -> None:
    """Correction 1: a closed marker alone never lets the next wait arm."""
    c = armed_case()
    try:
        code, out, _ = c.run("claim", "--item", "7", "--wait", "W1")
        code2, out2, _ = c.arm(7, 2)
        check("gate: a claim with no closing record (a stopped winner) blocks W2",
              out.startswith("CLAIMED") and out2.startswith("BLOCKED")
              and "no closing record" in out2, out2)
        code, out, _ = c.run("reconcile", "--item", "7", "--wait", "W1", "--text-file",
                             c.write(7, 1, "reconcile", "Evidence: chat X stopped.\n"))
        code2, out2, _ = c.arm(7, 2)
        check("gate: a reconcile note is evidence only and W2 stays blocked",
              out.startswith("NOTED") and out2.startswith("BLOCKED"), out + " | " + out2)
        code, out, _ = c.run("reconcile", "--item", "7", "--wait", "W1", "--text-file",
                             c.write(7, 1, "final", "Evidence: e\nBlocker: b\nNext check: n\n"),
                             "--final", "not-settled")
        check("reconcile: --final refused while the winner may still post (15 minutes)",
              out.startswith("REFUSED") and "may still post" in out, out)
        st = c.fake.load()
        for e in st["events"]:
            if e["kind"] == "linked" and e["data"]["links"] == ["file:head-wait/item-7/W1-closed"]:
                e["at"] -= 16 * 60 * 1000
        c.fake.save(st)
        code, out, _ = c.run("reconcile", "--item", "7", "--wait", "W1", "--text-file",
                             c.write(7, 1, "final", "Evidence: e\nBlocker: b\nNext check: n\n"),
                             "--final", "not-settled")
        code2, out2, _ = c.arm(7, 2)
        check("reconcile: after 15 minutes the reconciled disposition lands, and W2 arms",
              out.startswith("RECONCILED") and out2.startswith("ARMED item 7 W2"),
              out + " | " + out2)
        code, out, _ = c.run("reconcile", "--item", "7", "--wait", "W1", "--text-file",
                             c.write(7, 1, "final", "Evidence: e\n"), "--final", "settled")
        check("reconcile: no second closing record", out.startswith("REFUSED")
              and "already has its closing record" in out, out)
    finally:
        c.close()

    # a paused winner blocks W2 until its closing record lands
    c = armed_case()
    try:
        flag = c.root / "go"
        c.fake.fault(["bot", "item", "comment"], "pause", text_prefix="Wake disposition",
                     flag=str(flag))
        x = c.popen(*c.close_wait(7, 1, "settled", "notice"))
        paused = wait_for_waiters(flag, 1)
        code, during, _ = c.arm(7, 2)
        flag.write_text("")
        out, _ = x.communicate(timeout=60)
        code, after, _ = c.arm(7, 2)
        check("gate: a winner paused before its disposition blocks W2; once its record lands W2 "
              "arms", paused and during.startswith("BLOCKED") and out.startswith("CLAIMED")
              and after.startswith("ARMED item 7 W2"), f"{during} | {out} | {after}")
    finally:
        c.close()

    # a stale notice suspended after its read (T6a); an intervening Needs you (T6b) stays
    for label, between in (("W2 armed", "arm"), ("Needs you set", "needs_you")):
        c = armed_case()
        try:
            code, read, _ = c.run("check", "--item", "7", "--wait", "W1")
            c.run(*c.close_wait(7, 1, "settled", "look"))
            if between == "arm":
                c.arm(7, 2)
            else:
                c.fake.fixture_status(7, "needs_you")
            before = c.fake.load()
            code, out, _ = c.run(*c.close_wait(7, 1, "settled", "notice"))
            after = c.fake.load()
            item = after["items"]["7"]
            check(f"stale notice ({label} in between): NOT CLAIMED, and the item, its links and "
                  "its sends are unchanged", read.startswith("OPEN") and out.startswith(
                      "NOT CLAIMED") and item == before["items"]["7"]
                  and after["messages"] == before["messages"]
                  and len(after["events"]) == len(before["events"]), out)
        finally:
            c.close()

    # an unverified retire after the closing record does not block W2
    c = armed_case()
    try:
        c.fake.fault(["automations", "edit"], "error", code="runtime_error",
                     message="connection reset")
        code, out, _ = c.run(*c.close_wait(7, 1, "settled", "notice"))
        code_close = code
        code2, out2, _ = c.arm(7, 2)
        code = code_close
        lines = [e["data"]["text"] for e in c.fake.comments(7)
                 if e["data"]["text"].startswith("Retire unverified, item 7 W1:")]
        check("retire: a notice's retire that fails starts the line RETIRE UNVERIFIED (exit 1), "
              "posts a Retire unverified line, and W2 still arms",
              out.startswith("RETIRE UNVERIFIED item 7 W1") and code == 1 and lines
              and out2.startswith("ARMED item 7 W2"), out + " | " + out2)
    finally:
        c.close()


def test_retire() -> None:
    c = armed_case()
    try:
        wake = list(c.fake.load()["automations"])[0]
        code, out, _ = c.run("retire", "--item", "7", "--wait", "W1", "--id", wake)
        check("retire: RETIRED on a read-back of enabled false", code == 0
              and out.startswith("RETIRED item 7 W1"), out)
        st = c.fake.load()
        del st["automations"][wake]
        c.fake.save(st)
        code, out, _ = c.run("retire", "--item", "7", "--wait", "W1", "--id", wake)
        check("retire: GONE only on exactly Automation not found.", out.startswith("GONE"), out)
    finally:
        c.close()
    for label, fault in (("another show/edit error", {"mode": "error", "code": "runtime_error",
                                                      "message": "Automation not found. Retry"}),
                         ("an unreadable result", {"mode": "garbage"}),
                         ("a result with no automation", {"mode": "ok-noevent"}),
                         ("a read-back still enabled", {"mode": "noop"})):
        c = armed_case()
        try:
            wake = list(c.fake.load()["automations"])[0]
            c.fake.fault(["automations", "edit"], fault["mode"],
                         **{k: v for k, v in fault.items() if k != "mode"})
            code, out, _ = c.run("retire", "--item", "7", "--wait", "W1", "--id", wake)
            lines = [e for e in c.fake.comments(7)
                     if e["data"]["text"].startswith("Retire unverified, item 7 W1:")]
            check(f"retire: {label} -> UNVERIFIED with a visible line", code == 1
                  and out.startswith("UNVERIFIED") and len(lines) == 1, out)
        finally:
            c.close()


def test_full() -> None:
    """Correction 3: FULL is a visible blocker that carries work to a fresh item."""
    c = Case({7: {"links": 47}, 8: {}})
    try:
        code, out, _ = c.arm(7, 1)
        c.fake.fixture_link(7, "/tmp/late-1")
        c.fake.fixture_link(7, "/tmp/late-2")
        code, out, _ = c.run(*c.close_wait(7, 1, "re-sent", body="Q.\n",
                                           text="Evidence: e\nBlocker: b\nNext check: n\n"))
        st = c.fake.load()
        blocked = [e for e in c.fake.comments(7) if e["data"]["text"].startswith(
            "Wait blocked, item 7 W1:")]
        wake = list(st["automations"].values())[0]
        check("full: capacity used between reserve and claim -> FULL, a Wait blocked line, the "
              "wake retired, nothing sent, no disposition, status untouched",
              out.startswith("FULL item 7 W1") and len(blocked) == 1 and not st["messages"]
              and wake["enabled"] is False and st["items"]["7"]["status"] == "waiting"
              and not [e for e in c.fake.comments(7)
                       if e["data"]["text"].startswith("Wake disposition")], out)
        code, out, _ = c.run("check", "--item", "7", "--wait", "W1")
        check("full: check reports the blocked wait as BLOCKED, not carried", out.startswith(
            "BLOCKED item 7 W1") and "not carried" in out, out)
        code, out, _ = c.run("restart", "--bot", BOT_NAME)
        check("full: restart lists the uncovered wait", "ITEM 7 W1: blocked at the link cap" in out
              and "not carried" in out, out)
        code, out, _ = c.arm(8, 1, **{"carried-from": "7/W1"})
        rec = [e["data"]["text"] for e in c.fake.comments(8) if e["data"]["text"].startswith(
            "Wait record")]
        carried = [e["data"]["text"] for e in c.fake.comments(7) if e["data"]["text"].startswith(
            "Carried, item 7 W1: to item 8 W1")]
        check("full: carrying to a fresh item arms it, its record names item 7 W1, and item 7 "
              "gets a Carried line after the arm is verified",
              out.startswith("ARMED item 8 W1") and rec and "Carried from: item 7 W1." in rec[0]
              and f"Key: {KEY}." in rec[0] and len(carried) == 1, out)
        code, out, _ = c.run("restart", "--bot", BOT_NAME)
        check("full: restart then shows it carried", "ITEM 7 W1: blocked at the link cap" in out
              and "carried (" in out, out)
        check("full: no item was completed or canceled",
              {i["status"] for i in c.fake.load()["items"].values()} <= {"waiting",
                                                                         "in_progress"})
    finally:
        c.close()


def test_restart() -> None:
    c = Case({7: {}, 8: {}, 9: {}})
    try:
        c.arm(7, 1)  # 7: open, then its wake disabled by hand
        st = c.fake.load()
        for a in st["automations"].values():
            a["enabled"] = False
        c.fake.save(st)
        c.fake.fixture_link(8, "head-wait/item-8/W1")  # reserved with no record
        c.arm(9, 1)
        c.run("claim", "--item", "9", "--wait", "W1")  # closed with no line, Waiting on it
        before = c.fake.load()
        n_log = len(c.fake.log())
        code, out, _ = c.run("restart", "--bot", BOT_NAME)
        new = c.fake.log()[n_log:]
        writes = [a for a in new if a[:3] in (["bot", "item", "link"], ["bot", "item", "comment"],
                                               ["bot", "item", "set"])
                  or a[:2] in (["automations", "edit"], ["automations", "create"],
                               ["orchestration", "send"])]
        after = c.fake.load()
        check("restart: read-only (no write call, every item's version unchanged)",
              not writes and all(after["items"][k]["version"] == before["items"][k]["version"]
                                 for k in after["items"]), str(writes))
        for want in ("ITEM 7 W1: open, and its wake is disabled", "ITEM 8 W1: reserved with no "
                     "record", "ITEM 9 W1: closed with no closing record",
                     "ITEM 9: Waiting names W1, which is closed (a spent wake)"):
            check(f"restart: lists {want!r}", want in out, out)
    finally:
        c.close()
    c = Case({7: {}})
    try:
        c.arm(7, 1)
        c.run(*c.close_wait(7, 1, "settled", "look"))
        c.arm(7, 2)
        st = c.fake.load()
        st["items"]["7"]["wait"]["text"] = "W1 wake 0000abcd by later; record e1"
        c.fake.save(st)
        code, out, _ = c.run("restart", "--bot", BOT_NAME)
        check("restart: flags a Waiting note naming a spent and superseded wait",
              "ITEM 7: Waiting names W1, which is closed (a spent wake), superseded by W2" in out,
              out)
    finally:
        c.close()


def test_text_and_values() -> None:
    c = Case({7: {}})
    try:
        pwned = c.root / "pwned"
        nasty = (f"Waits on: $(touch {pwned}) and `touch {pwned}`; 'single' \"double\" "
                 "back\\slash\nsecond line\n" + "caf" + chr(0xE9) + " " + chr(0x1F600) + "\n")
        record = c.write(7, 1, "record", nasty)
        code, out, _ = c.arm(7, 1, record=record)
        rec = [e["data"]["text"] for e in c.fake.comments(7) if e["data"]["text"].startswith(
            "Wait record")][0]
        header = rec.split("\n", 1)[0]
        check("text: the record is the script's header, a newline, then the file byte for byte",
              out.startswith("ARMED") and rec == header + "\n" + nasty, repr(rec[-80:]))
        code, out, _ = c.run(*c.close_wait(7, 1, "re-sent", body=nasty,
                                           text="Evidence: " + nasty + "Blocker: b\n"
                                                "Next check: n\n"))
        msg = c.fake.load()["messages"][0]["body"]
        disp = [e["data"]["text"] for e in c.fake.comments(7)
                if e["data"]["text"].startswith("Wake disposition")][0]
        check("text: the re-sent body and the disposition carry the file bytes unchanged",
              msg.endswith("\n\n" + nasty) and disp.endswith(
                  "\nEvidence: " + nasty + "Blocker: b\nNext check: n\n"), repr(msg[-60:]))
        argv_text = json.dumps(c.fake.log())
        check("text: nothing ran, and no free text reached an argument list",
              not pwned.exists() and "touch" not in argv_text and "single" not in argv_text,
              argv_text[:200])
    finally:
        c.close()

    refusals = [
        ("--item 6;id", {"item": "6;id"}),
        ("a target with $(...)", {"target": "$(id)"}),
        ("an owner with a backtick", {"owner": "orca_session_id:`id`"}),
        ("an owner starting with -", {"owner": "-x"}),
        ("a key that isn't a key", {"key": "VIL-1/x/Q1;rm"}),
        ("a session that isn't a uuid", {"owner-session": "abc"}),
        ("a relative record path", {"record-file": "item-7-W1-record.txt"}),
        ("a record file named for another wait", {"record-file": "WRONG"}),
        ("a time with seconds", {"target": "2099-01-01T00:00:30+00:00"}),
    ]
    for label, over in refusals:
        c = Case({7: {}})
        try:
            if over.get("record-file") == "WRONG":
                over = {"record-file": c.write(7, 2, "record", "x\n")}
            code, out, err = c.arm(7, 1, **over)
            check(f"values: {label} is refused before any Orca call", code == 2
                  and (out.startswith("REFUSED") or "expected one argument" in err)
                  and not c.fake.log(), out or err)
        finally:
            c.close()
    c = Case({7: {}})
    try:
        link = c.files / "item-7-W1-link.txt"
        os.symlink("/etc/hosts", link)
        code, out, _ = c.arm(7, 1, **{"record-file": str(link)})
        bad = c.files / "item-7-W1-bad.txt"
        bad.write_bytes(b"\xff\xfe not utf-8")
        code2, out2, _ = c.arm(7, 1, **{"record-file": str(bad)})
        check("values: a symlinked or non-UTF-8 record file is refused before any call",
              code == 2 and code2 == 2 and not c.fake.log(), out + " | " + out2)
    finally:
        c.close()
    code = subprocess.run([sys.executable, "-I", str(SCRIPT), "--version"], capture_output=True,
                          text=True)
    check("version: --version prints the dv version", code.stdout.strip() ==
          f"head_wait.py dv {HW.VERSION}", code.stdout)


def test_more() -> None:
    """Paths the first review found untested."""
    # more reasons the fresh check stops a send
    for label, setup in (
            ("the item closed and reopened after the record",
             lambda c: (c.fake.fixture_status(7, "done"), c.fake.fixture_status(7, "in_progress"))),
            ("a Re-send line already there", lambda c: c.fake.fixture_comment(
                7, "Re-send, item 7 W1: to x at 2026-01-01T00:00:00Z.")),
            ("the fresh read failing", lambda c: c.fake.fault(
                ["bot", "item", "show"], "error", code="items_unavailable", skip=1, times=5))):
        c = armed_case()
        try:
            setup(c)
            code, out, _ = c.run(*c.close_wait(7, 1, "re-sent", body="Q.\n",
                                               text="Evidence: e\nBlocker: b\nNext check: n\n"))
            check(f"close: {label} stops the re-send (NOT SENT, no message)",
                  out.startswith("NOT SENT item 7 W1") and not c.fake.load()["messages"], out)
        finally:
            c.close()

    # STOPPED: a closing record lands between the claim and the fresh read
    c = armed_case()
    try:
        flag = c.root / "go"
        c.fake.fault(["bot", "item", "show"], "pause", skip=1, flag=str(flag))
        x = c.popen(*c.close_wait(7, 1, "settled", "wake"))
        paused = wait_for_waiters(flag, 1)
        c.fake.fixture_comment(7, "Wake disposition, item 7 W1: settled (reconciled). x")
        flag.write_text("")
        out, _ = x.communicate(timeout=60)
        disp = [e for e in c.fake.comments(7) if e["data"]["text"].startswith("Wake disposition")]
        check("close: a closing record already there after the claim -> STOPPED, nothing posted",
              paused and out.startswith("STOPPED item 7 W1") and len(disp) == 1, out)
    finally:
        c.close()

    # target too close at the Waiting write: the clock moves on after the create
    c = Case({7: {}})
    try:
        with c.inproc() as hw:
            real, saved = hw.now_s, hw._exec
            shift = {"s": 0.0}
            hw.now_s = lambda: real() + shift["s"]

            def exec_and_jump(argv, timeout):
                out = saved(argv, timeout)
                if argv[1:3] == ["automations", "create"]:
                    shift["s"] = 150.0
                return out
            hw._exec = exec_and_jump
            try:
                code, out = in_main(hw, c.arm_args(7, 1, target_s=120, deadline_s=600))
            finally:
                hw.now_s, hw._exec = real, saved
        check("waiting: a target under a minute away closes unarmed (target-too-close), no "
              "Waiting write", out.startswith("UNARMED item 7 W1: target-too-close")
              and not calls(c.fake.log(), "bot", "item", "set"), out)
    finally:
        c.close()

    # close-unarmed and reconcile --final unarmed
    c = Case({7: {}})
    try:
        c.run("reserve", "--item", "7", "--wait", "W1")
        code, out, _ = c.run("close-unarmed", "--item", "7", "--wait", "W1", "--step",
                             "reservation-without-record")
        texts = [e["data"]["text"] for e in c.fake.comments(7)]
        log = c.fake.log()
        link_at = next(i for i, a in enumerate(log) if a[:3] == ["bot", "item", "link"]
                       and a[a.index("--ref") + 1].endswith("W1-closed"))
        code2, out2, _ = c.run("check", "--item", "7")
        check("close-unarmed: a reservation with no record, read twice -> UNARMED line; the item "
              "is idle again", out.startswith("UNARMED item 7 W1: reservation-without-record")
              and len(calls(log[:link_at], "bot", "item", "show")) == 2
              and any(t.startswith("UNARMED, item 7 W1: reservation-without-record; wake none.")
                      for t in texts) and out2.startswith("IDLE item 7: no open wait; the next is "
                                                          "W2"), out + " | " + out2)
    finally:
        c.close()
    c = Case({7: {}})
    try:  # an arm's record lands between close-unarmed's two reads
        c.run("reserve", "--item", "7", "--wait", "W1")
        flag = c.root / "go"
        c.fake.fault(["bot", "item", "show"], "pause", skip=1, flag=str(flag))
        x = c.popen("close-unarmed", "--item", "7", "--wait", "W1", "--step",
                    "reservation-without-record")
        paused = wait_for_waiters(flag, 1)
        c.fake.fixture_comment(7, record_line(7, 1))
        flag.write_text("")
        out, _ = x.communicate(timeout=60)
        check("close-unarmed: a record that lands before its second read -> REFUSED, nothing "
              "linked", paused and out.startswith("REFUSED item 7 W1: it has a record")
              and "head-wait/item-7/W1-closed" not in c.fake.refs(7), out)
    finally:
        c.close()
    c = armed_case()
    try:
        code, out, _ = c.run("close-unarmed", "--item", "7", "--wait", "W1", "--step", "manual")
        check("close-unarmed: refused on an armed wait (it has an Armed line)",
              out.startswith("REFUSED") and "Armed line" in out
              and "head-wait/item-7/W1-closed" not in c.fake.refs(7), out)
    finally:
        c.close()
    c = Case({7: {}})
    try:
        c.run("reserve", "--item", "7", "--wait", "W1")
        c.run("claim", "--item", "7", "--wait", "W1")
        st = c.fake.load()
        for e in st["events"]:
            if e["kind"] == "linked" and e["data"]["links"] == ["file:head-wait/item-7/W1-closed"]:
                e["at"] -= 16 * 60 * 1000
        c.fake.save(st)
        f = c.write(7, 1, "final", "Evidence: the reserving chat ended with no record.\n")
        code, out, _ = c.run("reconcile", "--item", "7", "--wait", "W1", "--text-file", f,
                             "--final", "settled")
        code2, out2, _ = c.run("reconcile", "--item", "7", "--wait", "W1", "--text-file", f,
                               "--final", "unarmed")
        code3, out3, _ = c.run(*c.arm_args(7, 2))
        check("reconcile: no disposition without a record; --final unarmed closes it; W2 arms",
              out.startswith("REFUSED") and out2.startswith("RECONCILED item 7 W1: unarmed")
              and out3.startswith("ARMED item 7 W2"), f"{out} | {out2} | {out3}")
    finally:
        c.close()

    # notice rules: no Armed line, or a wake whose enabled can't be read
    c = Case({7: {}})
    try:
        paused = cut_arm(c, 7, 1)
        code, out, _ = c.run(*c.close_wait(7, 1, "not-settled", "notice",
                                           "Evidence: e\nBlocker: wake gone\nNext check: n\n"))
        check("notice: not settled refused when the wait has no Armed line",
              paused and out.startswith("REFUSED") and "no Armed or Rewake line" in out, out)
    finally:
        c.close()
    c = armed_case()
    try:
        st = c.fake.load()
        for a in st["automations"].values():
            a["enabled"] = "yes"
        c.fake.save(st)
        code, out, _ = c.run(*c.close_wait(7, 1, "not-settled", "notice",
                                           "Evidence: e\nBlocker: wake gone\nNext check: n\n"))
        check("notice: not settled refused when the wake's enabled can't be read",
              out.startswith("REFUSED") and "unreadable" in out, out)
    finally:
        c.close()

    # retire past a winner's window isn't tried
    c = armed_case()
    try:
        with c.inproc() as hw:
            clock = hw.Clock()
            clock.wall -= 400
            sc = hw.Scratch()
            try:
                line = hw.retire(7, 1, list(c.fake.load()["automations"])[0], sc, clock)
            finally:
                sc.close()
        check("retire: inside a run past its window it isn't tried, and says so",
              line.startswith("UNVERIFIED") and "not tried" in line
              and not calls(c.fake.log(), "automations", "edit"), line)
    finally:
        c.close()

    # FULL twice posts one Wait blocked line
    c = Case({7: {"links": 47}})
    try:
        c.arm(7, 1)
        c.fake.fixture_link(7, "/tmp/late-1")
        c.fake.fixture_link(7, "/tmp/late-2")
        args = c.close_wait(7, 1, "settled", "notice")
        c.run(*args)
        code, out, _ = c.run(*args)
        blocked = [e for e in c.fake.comments(7) if e["data"]["text"].startswith("Wait blocked")]
        check("full: a second FULL run posts no second Wait blocked line", len(blocked) == 1
              and "already there" in out, out)
    finally:
        c.close()

    # carried-from is checked against the old wait
    for label, over, setup, want in (
            ("an old wait that isn't blocked", {}, "open", "has no Wait blocked line"),
            ("another key than the old record", {"key": f"VIL-1218/{WAIT_S}/Q9"}, "full",
             "key differs"),
            ("another owner than the old record", {"owner": "skills-manager"}, "full",
             "owner differs")):
        c = Case({7: {"links": 47}, 8: {}})
        try:
            c.arm(7, 1)
            if setup == "full":
                c.fake.fixture_link(7, "/tmp/late-1")
                c.fake.fixture_link(7, "/tmp/late-2")
                c.run(*c.close_wait(7, 1, "settled", "notice"))
            over = dict(over, **{"carried-from": "7/W1"})
            code, out, _ = c.arm(8, 1, **over)
            check(f"carry: refused from {label}", out.startswith("BLOCKED item 8 W1")
                  and want in out and not c.fake.refs(8), out)
        finally:
            c.close()
    c = Case({7: {"links": 49}, 8: {}})
    try:
        code, out, _ = c.arm(7, 1)
        code2, out2, _ = c.arm(8, 1, **{"carried-from": "7/W1"})
        carried = [e for e in c.fake.comments(7) if e["data"]["text"].startswith("Carried")]
        check("carry: allowed from the next wait of an item at the cap (arm there BLOCKED)",
              out.startswith("BLOCKED") and out2.startswith("ARMED item 8 W1") and carried,
              out + " | " + out2)
    finally:
        c.close()

    # restart: more findings
    c = Case({7: {"links": 46}})
    try:
        c.arm(7, 1)
        st = c.fake.load()
        for e in st["events"]:
            if e["kind"] == "commented" and e["data"]["text"].startswith("Wait record"):
                head, rest = e["data"]["text"].split("\n", 1)
                import re as _re
                head = _re.sub(r"Deadline: \S+ ", "Deadline: 2020-01-01T00:00:00+00:00 ", head)
                e["data"]["text"] = head + "\n" + rest
        c.fake.save(st)
        c.fake.fixture_link(7, "/tmp/another-link")
        c.fake.fixture_link(7, "head-wait/item-7/W5-closed")
        code, out, _ = c.run("restart", "--bot", BOT_NAME)
        for want in ("ITEM 7 W1: open past its deadline 2020-01-01T00:00:00+00:00",
                     "ITEM 7 W5: W5-closed is linked with no W5 (a stray marker)",
                     "ITEM 7: 1 free link slot(s) of Orca's 50"):
            check(f"restart: lists {want!r}", want in out, out)
    finally:
        c.close()
    c = armed_case()
    try:
        st = c.fake.load()
        st["items"]["7"]["wait"]["text"] = "W1 wake 0000abcd by later; record e1"
        c.fake.save(st)
        code, out, _ = c.run("restart", "--bot", BOT_NAME)
        check("restart: a Waiting note naming another wake than W1's Armed wake is flagged",
              "ITEM 7: Waiting names wake 0000abcd, not W1's armed wake" in out, out)
    finally:
        c.close()

    # outcome lines instead of crashes
    c = Case({7: {}})
    try:
        d = c.files / "item-7-W1-dir.txt"
        d.mkdir()
        code, out, _ = c.arm(7, 1, **{"record-file": str(d)})
        check("values: a record path that is a directory is REFUSED, not a crash", code == 2
              and out.startswith("REFUSED") and not c.fake.log(), out)
    finally:
        c.close()


def test_recheck() -> None:
    """Paths the second review found untested."""
    c = Case({7: {}})
    try:
        paused = cut_arm(c, 7, 1)
        code, out, _ = c.run("close-unarmed", "--item", "7", "--wait", "W1", "--step", "manual")
        texts = [e["data"]["text"] for e in c.fake.comments(7)]
        check("close-unarmed: a recorded wait with no Armed line (an arm cut off before Waiting) "
              "closes with --step manual", paused and out.startswith("UNARMED item 7 W1: manual")
              and any(t.startswith("UNARMED, item 7 W1: manual; wake none.") for t in texts)
              and "head-wait/item-7/W1-closed" in c.fake.refs(7), out)
    finally:
        c.close()

    c = Case({7: {"links": 49}, 8: {}})
    try:
        c.fake.set_fields(7, owner={"botId": "another-bot", "name": BOT_NAME})
        code, out, _ = c.arm(8, 1, **{"carried-from": "7/W1"})
        check("carry: refused from another bot's item", out.startswith("BLOCKED item 8 W1")
              and "belongs to another bot" in out and not c.fake.refs(8), out)
    finally:
        c.close()

    c = armed_case()
    try:
        st = c.fake.load()
        for e in st["events"]:
            if e["kind"] == "commented" and e["data"]["text"].startswith("Wait record"):
                e["data"]["text"] = e["data"]["text"].replace("Deadline: 20", "Deadline: 29", 1)
                head = e["data"]["text"].split("\n", 1)[0]
                import re as _re
                e["data"]["text"] = _re.sub(r"Deadline: \d{4}-\d{2}", "Deadline: 2026-13", head) + \
                    "\n" + e["data"]["text"].split("\n", 1)[1]
        c.fake.save(st)
        code, out, _ = c.run("check", "--item", "7", "--wait", "W1")
        code2, out2, _ = c.run(*c.close_wait(7, 1, "settled", "look"))
        check("record: a record line whose time isn't a real date counts as no record",
              out.startswith("OPEN item 7 W1: reserved with no record")
              and out2.startswith("REFUSED"), out + " | " + out2)
    finally:
        c.close()

    c = Case({7: {}})
    try:
        with c.inproc() as hw:
            saved = hw.read_item
            hw.read_item = lambda n, tries=1: (_ for _ in ()).throw(ValueError("bad stamp"))
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    rc = hw.main(["check", "--item", "7"])
            except Exception as e:  # the catch-all missing: a crash, not an outcome line
                rc = f"crashed: {type(e).__name__}"
            finally:
                hw.read_item = saved
        check("main: an unexpected error prints an UNCLEAR outcome line, exit 1",
              rc == 1 and buf.getvalue().startswith("UNCLEAR: check stopped on ValueError"),
              buf.getvalue())
    finally:
        c.close()

    c = Case({7: {}, 8: {}})
    try:
        c.fake.fault(["bot", "item", "show"], "error", code="items_unavailable", ref="8",
                     times=10)
        code, out, _ = c.run("restart", "--bot", BOT_NAME)
        check("restart: an unreadable item makes the first line INCOMPLETE RESTART, exit 1",
              code == 1 and out.startswith("INCOMPLETE RESTART") and "ITEM 8: unreadable" in out,
              out)
    finally:
        c.close()


RESENT = dict(body="Q.\n", text="Evidence: e\nBlocker: b\nNext check: n\n")


def claims(c: Case, count: int, n: int = 7, k: int = 1) -> None:
    for _ in range(count):
        c.fake.fixture_comment(n, f"Rewake claim, item {n} W{k}: {uuid.uuid4()}.")


def spent_case() -> Case:
    """W1 armed on item 7, its wake gone (Orca deleted it after its run); the log starts empty."""
    c = armed_case()
    st = c.fake.load()
    st["automations"] = {}
    c.fake.save(st)
    c.fake.log_path.unlink()
    return c


def resent(c: Case, n: int, k: int) -> list:
    return c.close_wait(n, k, "re-sent", **RESENT)


def test_fix_round1() -> None:
    """Paths fix round 1 found: snooze, per-key sends, paging, reads, rewake, budget."""
    # M2: the latest Snoozed until line decides, whenever it was posted
    for label, lines, sends in (
            ("an undated line posted before the arm stops the send",
             ["Snoozed until 23:00 PT Nov 26 / 07:00 UTC Nov 27: waiting on David"], 0),
            ("an Unsnoozed line after it lets the send go",
             ["Snoozed until 23:00 PT Nov 26: waiting on David", "Unsnoozed: David answered"], 1),
            ("a later expired dated line ends it",
             ["Snoozed until tonight", "Snoozed until 2000-01-01T00:00:00Z: over"], 1),
            ("a line with a past date and no time zone still holds",
             ["Snoozed until 2020-01-01T00:00: no zone"], 0),
            ("a person's line counts", ["person:Snoozed until Monday: away"], 0),
            ("a person's Unsnoozed line ends the Head's line",
             ["Snoozed until Monday: away", "person:Unsnoozed: back"], 1),
            ("another bot's Unsnoozed line doesn't end it",
             ["Snoozed until Monday: away", "otherbot:Unsnoozed: back"], 0)):
        c = Case({7: {}})
        try:
            for line in lines:
                who, _, text = line.partition(":") if line.startswith(("person:", "otherbot:")) \
                    else ("", "", line)
                c.fake.fixture_comment(7, text, who == "person",
                                       "another-bot" if who == "otherbot" else BOT_ID)
            c.arm(7, 1)
            code, out, _ = c.run(*resent(c, 7, 1))
            msgs = len(c.fake.load()["messages"])
            check(f"snooze: {label}", msgs == sends and out.startswith(
                "CLAIMED item 7 W1: re-sent" if sends else "NOT SENT item 7 W1"), out)
        finally:
            c.close()

    # M3: no send under a key while an earlier wait under it may have sent
    c = armed_case()
    try:
        c.fake.fault(["orchestration", "send"], "after-error", code="delivery_unknown")
        code, out, _ = c.run(*resent(c, 7, 1))
        c.arm(7, 2)
        code2, out2, _ = c.run(*resent(c, 7, 2))
        disp = [e["data"]["text"] for e in c.fake.comments(7)
                if e["data"]["text"].startswith("Wake disposition, item 7 W2")]
        check("per key: W1's unclear send stops W2's re-send under the same key",
              out.startswith("SEND UNCLEAR") and out2.startswith("NOT SENT item 7 W2")
              and len(c.fake.load()["messages"]) == 1 and disp
              and disp[0].startswith("Wake disposition, item 7 W2: not settled.")
              and "no Sent receipt" in disp[0], out2)
    finally:
        c.close()
    for label, key, sends in (("W1 sent with a receipt", KEY, 2),
                              ("W1's unclear send was under another key",
                               f"VIL-1218/{WAIT_S}/Q4", 2)):
        c = armed_case()
        try:
            if key == KEY:
                c.run(*resent(c, 7, 1))
            else:
                c.fake.fault(["orchestration", "send"], "after-error", code="delivery_unknown")
                c.run(*resent(c, 7, 1))
            c.arm(7, 2, key=key)
            code, out, _ = c.run(*resent(c, 7, 2))
            check(f"per key: W2 re-sends when {label}", out.startswith("CLAIMED item 7 W2")
                  and len(c.fake.load()["messages"]) == sends, out)
        finally:
            c.close()
    c = Case({7: {"links": 47}, 8: {}})
    try:
        c.arm(7, 1)
        c.fake.fault(["orchestration", "send"], "after-error", code="delivery_unknown")
        c.run(*resent(c, 7, 1))
        code, out, _ = c.arm(7, 2)
        code2, out2, _ = c.arm(8, 1, **{"carried-from": "7/W2"})
        code3, out3, _ = c.run(*resent(c, 8, 1))
        check("per key: a wait carried from an item whose earlier wait sent unclear doesn't send",
              out.startswith("BLOCKED") and out2.startswith("ARMED item 8 W1")
              and out3.startswith("NOT SENT item 8 W1") and "item 7 W1" in out3
              and len(c.fake.load()["messages"]) == 1, f"{out} | {out2} | {out3}")
    finally:
        c.close()

    # M1: two reconciliations at once: the later prints DUPLICATE
    c = armed_case()
    try:
        c.run("claim", "--item", "7", "--wait", "W1")
        st = c.fake.load()
        for e in st["events"]:
            if e["kind"] == "linked" and e["data"]["links"] == ["file:head-wait/item-7/W1-closed"]:
                e["at"] -= 16 * 60 * 1000
        c.fake.save(st)
        flag = c.root / "go"
        c.fake.fault(["bot", "item", "comment"], "pause", times=2, text_prefix="Wake disposition",
                     flag=str(flag))
        args = ("reconcile", "--item", "7", "--wait", "W1", "--text-file",
                c.write(7, 1, "final", "Evidence: e\nBlocker: b\nNext check: n\n"), "--final",
                "not-settled")
        x, y = c.popen(*args), c.popen(*args)
        both = wait_for_waiters(flag, 2)
        flag.write_text("")
        outs = sorted(p.communicate(timeout=60)[0].split("\n")[0] for p in (x, y))
        code, out, _ = c.run("check", "--item", "7", "--wait", "W1")
        first = min((e for e in c.fake.comments(7) if e["data"]["text"].startswith(
            "Wake disposition")), key=lambda e: int(e["id"][1:]))
        check("reconcile: two --final runs at once give one RECONCILED and one DUPLICATE; the "
              "first record counts", both and outs[0].startswith("DUPLICATE item 7 W1")
              and outs[1].startswith("RECONCILED item 7 W1")
              and out == f"CLOSED item 7 W1: closing record {first['id']}", f"{outs} | {out}")
        code, out, _ = c.arm(7, 2)
        check("reconcile: the next wait arms after a duplicate", out.startswith("ARMED item 7 W2"),
              out)
    finally:
        c.close()
    c = armed_case()
    try:
        c.run("claim", "--item", "7", "--wait", "W1")
        st = c.fake.load()
        for e in st["events"]:
            if e["kind"] == "linked" and e["data"]["links"] == ["file:head-wait/item-7/W1-closed"]:
                e["at"] -= 16 * 60 * 1000
        c.fake.save(st)
        c.fake.fault(["bot", "item", "show"], "error", code="items_unavailable", skip=1)
        code, out, _ = c.run("reconcile", "--item", "7", "--wait", "W1", "--text-file",
                             c.write(7, 1, "final", "Evidence: e\nBlocker: b\nNext check: n\n"),
                             "--final", "not-settled")
        check("reconcile: a failed read after the post -> UNCHECKED (exit 1)", code == 1
              and out.startswith("UNCHECKED item 7 W1"), out)
    finally:
        c.close()

    # M4: events past the first page
    for fillers, label in ((49, "the record on page 2, its marker on page 1"),
                           (60, "every W1 line on page 2")):
        c = Case({7: {}})
        try:
            for i in range(fillers):
                c.fake.fixture_comment(7, f"Note {i}.")
            code, out, _ = c.arm(7, 1)
            code2, out2, _ = c.run("check", "--item", "7", "--wait", "W1")
            code3, out3, _ = c.run(*c.close_wait(7, 1, "settled", "look"))
            code4, out4, _ = c.arm(7, 2)
            pages = [a for a in calls(c.fake.log(), "bot", "item", "show") if "--after" in a]
            check(f"paging: {label}: arm, check, close and the next arm read every page",
                  out.startswith("ARMED") and out2.startswith("OPEN item 7 W1: record")
                  and out3.startswith("CLAIMED item 7 W1: settled")
                  and out4.startswith("ARMED item 7 W2") and pages, f"{out2} | {out4}")
        finally:
            c.close()

    # Low 6: a show whose events miss a marker's link event is read again
    c = armed_case()
    try:
        c.fake.fault(["bot", "item", "show"], "hide-link", hide="head-wait/item-7/W1")
        n_log = len(c.fake.log())
        code, out, _ = c.run("check", "--item", "7", "--wait", "W1")
        shows = calls(c.fake.log()[n_log:], "bot", "item", "show")
        check("read: a marker link seen before its event is read again, so W1 reads OPEN with its "
              "record", out.startswith("OPEN item 7 W1: record") and len(shows) == 2, out)
    finally:
        c.close()

    # H1(a): a command's first read tries 3 times on an error that can pass
    for label, times, code_, want, sleeps in (
            ("two failures, then the read", 2, "items_unavailable", "OPEN item 7 W1", [15, 45]),
            ("three failures", 3, "items_unavailable", "UNREADABLE item 7: ", [15, 45]),
            ("an error that can't pass", 3, "not_found", "UNREADABLE item 7: ", [])):
        c = armed_case()
        try:
            c.fake.fault(["bot", "item", "show"], "error", code=code_, times=times,
                         message="No item 7 on this computer." if code_ == "not_found" else "x")
            slept = []
            with c.inproc() as hw:
                saved = hw.pause
                hw.pause = slept.append
                try:
                    code, out = in_main(hw, ["check", "--item", "7", "--wait", "W1"])
                finally:
                    hw.pause = saved
            check(f"retry: check on {label} -> {want.split()[0]}, pauses {sleeps}",
                  out.startswith(want) and slept == sleeps
                  and (code == 0) == want.startswith("OPEN"), out)
        finally:
            c.close()

    # H1: the budget: no Orca call starts once it is spent
    c = armed_case()
    try:
        with c.inproc() as hw:
            saved = hw.RUN_BUDGET_S
            hw.RUN_BUDGET_S = 59  # less than one call's 60 s
            n_log = len(c.fake.log())
            try:
                code, out = in_main(hw, ["check", "--item", "7", "--wait", "W1"])
            finally:
                hw.RUN_BUDGET_S = saved
        check("budget: a spent budget starts no Orca call and says so", code == 1
              and out.startswith("UNREADABLE item 7") and "are spent" in out
              and len(c.fake.log()) == n_log, out)
    finally:
        c.close()

    # H1(b): rewake
    c = armed_case()
    try:
        refs = c.fake.refs(7)
        code, out, _ = c.run("rewake", "--item", "7", "--wait", "W1")
        check("rewake: a wait whose wake is still due -> COVERED, nothing made", code == 0
              and out.startswith("COVERED item 7 W1") and len(c.fake.load()["automations"]) == 1,
              out)
        old = list(c.fake.load()["automations"])[0]
        st = c.fake.load()
        del st["automations"][old]  # the one-time wake ran and Orca deleted it
        c.fake.save(st)
        start = time.time()
        code, out, _ = c.run("rewake", "--item", "7", "--wait", "W1")
        autos = c.fake.load()["automations"]
        new = list(autos.values())[0] if autos else {}
        lines = [e["data"]["text"] for e in c.fake.comments(7)
                 if e["data"]["text"].startswith("Rewake, item 7 W1: wake ")]
        by = new.get("once", {}).get("by", 0) / 1000
        check("rewake: a wait whose wake is gone -> REWOKEN: one enabled one-time wake about 16 "
              "minutes out, a Rewake line, no link", code == 0
              and out.startswith("REWOKEN item 7 W1")
              and new.get("enabled") is True and start + 960 <= by <= start + 960 + 61
              and new.get("on") is None and len(lines) == 1 and new["id"] in lines[0]
              and c.fake.refs(7) == refs, out)
        code, out, _ = c.run("check", "--item", "7", "--wait", "W1")
        check("rewake: check names the new wake", f"wake {new.get('id')} at " in out, out)
        code, out, _ = c.run("restart", "--bot", BOT_NAME)
        check("rewake: restart sees the wait covered and the note not superseded",
              "ITEM 7" not in out, out)
        code, out, _ = c.run(*c.close_wait(7, 1, "settled", "notice"))
        check("rewake: a notice that settles the wait retires the rewake's wake",
              out.startswith("CLAIMED item 7 W1: settled") and f"RETIRED item 7 W1: wake "
              f"{new.get('id')}" in out and c.fake.load()["automations"][new["id"]]["enabled"]
              is False, out)
        code, out, _ = c.run("rewake", "--item", "7", "--wait", "W1")
        check("rewake: a wait with its closing record -> CLOSED, nothing made", code == 3
              and out.startswith("CLOSED item 7 W1: closing record"), out)
    finally:
        c.close()
    c = armed_case()
    try:  # the wake's own run: its target has passed and the wake still exists
        with c.inproc() as hw:
            real = hw.now_s
            hw.now_s = lambda: real() + 3600
            try:
                code, out = in_main(hw, ["rewake", "--item", "7", "--wait", "W1"])
            finally:
                hw.now_s = real
        check("rewake: inside the wake's own run (its target passed) -> REWOKEN", code == 0
              and out.startswith("REWOKEN item 7 W1"), out)
    finally:
        c.close()
    c = armed_case()
    try:  # a winner that stopped after its claim, its wake spent: the rewake reconciles later
        c.run("claim", "--item", "7", "--wait", "W1")
        st = c.fake.load()
        st["automations"] = {}
        c.fake.save(st)
        code, out, _ = c.run("rewake", "--item", "7", "--wait", "W1")
        check("rewake: a closed wait with no closing record and no wake -> REWOKEN",
              out.startswith("REWOKEN item 7 W1"), out)
    finally:
        c.close()
    for label, setup, want, code_ in (
            ("a create Orca refuses", lambda c: c.fake.fault(
                ["automations", "create"], "error", code="invalid_argument", message="no"),
             "UNCOVERED item 7 W1: no fresh wake", 1),
            ("a create read back disabled", lambda c: c.fake.fault(
                ["automations", "create"], "mutate", fields={"enabled": False}),
             "UNCOVERED item 7 W1: no fresh wake (verify", 1),
            ("a Rewake line that doesn't post", lambda c: c.fake.fault(
                ["bot", "item", "comment"], "error", code="invalid_argument",
                text_prefix="Rewake, item"),
             "UNRECORDED item 7 W1", 1),
            ("an item it can't read", lambda c: c.fake.fault(
                ["bot", "item", "show"], "error", code="not_found", message="No item 7."),
             "UNCOVERED item 7 W1: the item can't be read", 1),
            ("the most rewakes already", lambda c: claims(c, 8),
             "UNCOVERED item 7 W1: it has 8 rewake claims", 1)):
        c = armed_case()
        try:
            st = c.fake.load()
            st["automations"] = {}
            c.fake.save(st)
            setup(c)
            code, out, _ = c.run("rewake", "--item", "7", "--wait", "W1")
            autos = c.fake.load()["automations"]
            check(f"rewake: {label} -> {want.split(':')[0]}", code == code_
                  and out.startswith(want) and all(not a["enabled"] for a in autos.values())
                  == (not want.startswith("UNRECORDED")), out)
        finally:
            c.close()
    c = Case({7: {}})
    try:
        code, out, _ = c.run("rewake", "--item", "7", "--wait", "W1")
        check("rewake: no W1 marker -> NO WAIT, nothing made", code == 3
              and out.startswith("NO WAIT item 7 W1") and not c.fake.load()["automations"], out)
        c.run("reserve", "--item", "7", "--wait", "W1")
        code, out, _ = c.run("rewake", "--item", "7", "--wait", "W1")
        check("rewake: a wait reserved with no record -> REFUSED to close-unarmed, nothing made",
              code == 3 and out.startswith("REFUSED item 7 W1: reserved with no record")
              and "close-unarmed" in out and not c.fake.load()["automations"], out)
    finally:
        c.close()
    c = armed_case()
    try:
        c.fake.fixture_status(7, "done")
        code, out, _ = c.run("rewake", "--item", "7", "--wait", "W1")
        check("rewake: a done item -> CLOSED, nothing made", code == 3
              and out.startswith("CLOSED item 7 W1: the item is done")
              and len(c.fake.load()["automations"]) == 1, out)
    finally:
        c.close()
    c = Case({7: {"links": 47}})
    try:
        c.arm(7, 1)
        c.fake.fixture_link(7, "/tmp/late-1")
        c.fake.fixture_link(7, "/tmp/late-2")
        c.run(*c.close_wait(7, 1, "settled", "notice"))
        code, out, _ = c.run("rewake", "--item", "7", "--wait", "W1")
        check("rewake: a wait blocked at the cap -> BLOCKED, nothing made", code == 3
              and out.startswith("BLOCKED item 7 W1") and len(c.fake.load()["automations"]) == 1,
              out)
    finally:
        c.close()
    c = armed_case()
    try:
        code, out, _ = c.run("check", "--item", "7")
        check("check: an item with an open wait, no --wait -> OPEN, exit 0", code == 0
              and out.startswith("OPEN item 7 W1: record"), out)
    finally:
        c.close()

    test_fix_round2()

    # Low 9: a cleanup error after a send doesn't replace the outcome line
    c = armed_case()
    try:
        with c.inproc() as hw:
            saved = hw._exec

            def exec_and_litter(argv, timeout):
                out = saved(argv, timeout)
                if argv[1:3] == ["orchestration", "send"]:
                    sub = Path(argv[argv.index("--body-file") + 1]).parent / "sub"
                    sub.mkdir()
                    (sub / "x").write_text("x")
                return out
            hw._exec = exec_and_litter
            try:
                code, out = in_main(hw, resent(c, 7, 1))
            finally:
                hw._exec = saved
        check("cleanup: a scratch directory that won't unlink after the send leaves the CLAIMED "
              "line", code == 0 and out.startswith("CLAIMED item 7 W1: re-sent"), out)
    finally:
        c.close()

    # Low 1 and Low 8
    c = Case({7: {}})
    try:
        bad = [c.run(name, "--item", "7", "--wait", "W1")[0] for name in ("record", "create",
                                                                           "waiting")]
        code, out, _ = c.run(*c.close_wait(7, 1, "settled", "look"))
        check("commands: record, create and waiting are gone (usage error, no Orca call)",
              bad == [2, 2, 2] and len(c.fake.log()) == 1, str(bad))
        check("exit: a REFUSED after a read exits 3, not 2", code == 3
              and out.startswith("REFUSED item 7 W1: no W1 marker"), out)
    finally:
        c.close()


def test_fix_round2() -> None:
    """Fix round 2: rewake holds like a re-send, and its limit holds when runs overlap."""
    for label, setup, why in (
            ("Needs you", lambda c: c.fake.fixture_status(7, "needs_you"),
             "the item reads Needs you"),
            ("Orca's snooze ahead", lambda c: c.fake.set_fields(
                7, snoozedUntil=int((time.time() + 3600) * 1000)), "Orca's snooze is ahead"),
            ("a Snoozed until line", lambda c: c.fake.fixture_comment(
                7, "Snoozed until 23:00 PT Nov 28 / 07:00 UTC Nov 29: away"),
             "a Snoozed until line e")):
        c = spent_case()
        try:
            setup(c)
            n_log = len(c.fake.log())
            code, out, _ = c.run("rewake", "--item", "7", "--wait", "W1")
            new = c.fake.log()[n_log:]
            check(f"rewake held: {label} -> HELD saying why, no automations create call",
                  code == 3 and out.startswith(f"HELD item 7 W1: {why}") and "no wake made" in out
                  and not calls(new, "automations", "create")
                  and not calls(new, "bot", "item", "comment"), out)
        finally:
            c.close()

    c = spent_case()
    try:  # two callers each read seven claims; exactly one creates
        claims(c, 7)
        flag = c.root / "go"
        c.fake.fault(["bot", "item", "comment"], "pause", times=2, text_prefix="Rewake claim",
                     flag=str(flag))
        x = c.popen("rewake", "--item", "7", "--wait", "W1")
        y = c.popen("rewake", "--item", "7", "--wait", "W1")
        both = wait_for_waiters(flag, 2)
        flag.write_text("")
        outs = sorted(p.communicate(timeout=60)[0].split("\n")[0] for p in (x, y))
        made = calls(c.fake.log(), "automations", "create")
        lines = [e for e in c.fake.comments(7)
                 if e["data"]["text"].startswith("Rewake claim, item 7 W1:")]
        check("rewake limit: two callers that each read seven claims -> exactly one creates "
              "(REWOKEN), the other NOT CLAIMED", both and len(made) == 1 and len(lines) == 9
              and outs[0].startswith("NOT CLAIMED item 7 W1") and outs[1].startswith(
                  "REWOKEN item 7 W1"), str(outs))
        st = c.fake.load()
        st["automations"] = {}  # that wake ran too
        c.fake.save(st)
        code, out, _ = c.run("rewake", "--item", "7", "--wait", "W1")
        check("rewake limit: after that, a later caller makes nothing", code == 1
              and out.startswith("UNCOVERED item 7 W1: it has 9 rewake claims and gets at most 8")
              and len(calls(c.fake.log(), "automations", "create")) == 1, out)
    finally:
        c.close()

    c = spent_case()
    try:  # an uncertain create still counts against the limit
        claims(c, 7)
        c.fake.fault(["automations", "create"], "timeout")
        code, out, _ = c.run("rewake", "--item", "7", "--wait", "W1")
        n_log = len(c.fake.log())
        code2, out2, _ = c.run("rewake", "--item", "7", "--wait", "W1")
        check("rewake limit: a create with no answer counts (its claim), so the next caller "
              "makes nothing", out.startswith("UNCOVERED item 7 W1: no fresh wake")
              and "counts" in out and out2.startswith("UNCOVERED item 7 W1: it has 8 rewake")
              and not calls(c.fake.log()[n_log:], "automations", "create"), out + " | " + out2)
    finally:
        c.close()

    for label, fault, want, creates in (
            ("a claim that lands and then errors is found by its nonce",
             dict(mode="after-error", code="items_unavailable"), "REWOKEN item 7 W1", 1),
            ("an unclear claim the read after doesn't show",
             dict(mode="error", code="items_unavailable"), "UNCOVERED item 7 W1: the rewake "
             "claim's answer was unclear (items_unavailable: stubbed) and the read after it "
             "doesn't show it; no wake made, and the claim counts if it landed", 0),
            ("a claim Orca refuses", dict(mode="error", code="invalid_argument",
                                          message="no"), "UNCOVERED item 7 W1: the rewake "
             "claim did not post", 0)):
        c = spent_case()
        try:
            c.fake.fault(["bot", "item", "comment"], fault.pop("mode"), text_prefix="Rewake claim",
                         **fault)
            code, out, _ = c.run("rewake", "--item", "7", "--wait", "W1")
            check(f"rewake claim: {label} -> {want.split(' item')[0]}", out.startswith(want)
                  and len(calls(c.fake.log(), "automations", "create")) == creates, out)
        finally:
            c.close()
    c = spent_case()
    try:  # a read after the claim that doesn't show it: its place is unknown
        c.fake.fault(["bot", "item", "show"], "hide-comment", hide="Rewake claim", skip=1)
        code, out, _ = c.run("rewake", "--item", "7", "--wait", "W1")
        check("rewake claim: a read after the claim that doesn't show it -> UNCOVERED, nothing "
              "created", code == 1 and out.startswith("UNCOVERED item 7 W1: claim e")
              and "doesn't show it" in out
              and not calls(c.fake.log(), "automations", "create"), out)
    finally:
        c.close()
    c = spent_case()
    try:  # an item closed and reopened after the record doesn't hold: a wake closes the wait
        c.fake.fixture_status(7, "done")
        c.fake.fixture_status(7, "in_progress")
        code, out, _ = c.run("rewake", "--item", "7", "--wait", "W1")
        check("rewake: an item closed and reopened after the record isn't held (REWOKEN)",
              out.startswith("REWOKEN item 7 W1"), out)
    finally:
        c.close()
    c = spent_case()
    try:  # a wait at the limit says so now, even under a hold
        claims(c, 8)
        c.fake.fixture_comment(7, "Snoozed until 23:00 PT Nov 28: away")
        code, out, _ = c.run("rewake", "--item", "7", "--wait", "W1")
        check("rewake: a wait at the limit under a hold -> UNCOVERED now, not HELD", code == 1
              and out.startswith("UNCOVERED item 7 W1: it has 8 rewake claims"), out)
    finally:
        c.close()
    c = armed_case()
    try:  # a hold with a wake still due reads COVERED
        c.fake.fixture_comment(7, "Snoozed until 23:00 PT Nov 28: away")
        code, out, _ = c.run("rewake", "--item", "7", "--wait", "W1")
        check("rewake: a hold with the wake still due -> COVERED, not HELD", code == 0
              and out.startswith("COVERED item 7 W1"), out)
    finally:
        c.close()
    c = spent_case()
    try:
        c.fake.fault(["bot", "item", "show"], "error", code="items_unavailable", skip=1)
        code, out, _ = c.run("rewake", "--item", "7", "--wait", "W1")
        check("rewake claim: a failed read after the claim -> UNCOVERED, nothing created",
              code == 1 and out.startswith("UNCOVERED item 7 W1: claim e")
              and not calls(c.fake.log(), "automations", "create"), out)
    finally:
        c.close()


def main() -> int:
    global SCRIPT, HW
    if len(sys.argv) > 1:
        SCRIPT = Path(sys.argv[1]).resolve()
    HW = load_module()
    for test in (test_static, test_outcomes, test_arm, test_close, test_successor_gate,
                 test_retire, test_full, test_restart, test_text_and_values, test_more,
                 test_recheck, test_fix_round1):
        test()
    print()
    if failures:
        print(f"{len(failures)} failure(s):")
        for f in failures:
            print(" - " + f)
        return 1
    print("all head_wait checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
