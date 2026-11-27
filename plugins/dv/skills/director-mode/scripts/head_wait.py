#!/usr/bin/env python3
"""dv:director-mode, "Head's wake for a waiting item": the only place `orca` is called to arm,
check, close, retire, reconcile or rewake a wait on one of the Head's Orca items.

    python3 -I head_wait.py <command> [options]

Each wait W<k> on item n has two marker links on the item, both plain file links:
`head-wait/item-<n>/W<k>` (linked first by the run that arms the wait: the reservation) and
`head-wait/item-<n>/W<k>-closed` (linked first by the run that closes it: the claim). Orca adds a
link only when the item lacks it, checked and inserted in one transaction, and answers
`unchanged` to every later caller, so exactly one call ever gets an event id for each marker.

Commands (the first printed line starts with the outcome word):

  arm        --item --wait --target --deadline --owner --owner-session --waiting-session
             --ticket --key --record-file [--carried-from <m>/W<j>]
             ARMED | UNCHECKED | SPENT | OVERTAKEN | TAKEN | BLOCKED | UNARMED | NOT CLAIMED |
             CLOSED | FULL | REFUSED | UNREADABLE | UNCLEAR
  check      --item [--wait]                read-only: OPEN | IDLE | CLOSED | NO WAIT | BLOCKED |
                                            UNREADABLE
  close      --item --wait --trigger wake|notice|look --case no-follow-up|settled|re-sent|
             not-settled --text-file [--body-file]
             CLAIMED (closing record posted) | NOT SENT (a planned re-send the fresh check
             stopped; closing record posted) | SEND UNCLEAR (the send answered with an error or
             unreadably, so it may have gone; closing record posted) | RETIRE UNVERIFIED (closing
             record posted, the wake not confirmed disabled) | NOT CLAIMED | STOPPED | CLOSED |
             FULL | REFUSED | UNREADABLE | UNCLEAR
  retire     --item --wait --id                RETIRED | GONE | UNVERIFIED
  reconcile  --item --wait --text-file [--final <case>]
             NOTED | RECONCILED | DUPLICATE | UNCHECKED | REFUSED | UNREADABLE | UNCLEAR
  rewake     --item --wait                     REWOKEN | COVERED | UNCOVERED | UNRECORDED |
                                               CLOSED | BLOCKED | NO WAIT | REFUSED
  restart    --bot                             read-only: RESTART <count> (INCOMPLETE RESTART when
                                               an item can't be read), then one line each;
                                               UNREADABLE when the item list can't be read
  --version

Step commands, the same code `arm` and `close` run, for the live tests and reconciliation:
  reserve    --item --wait                     RESERVED | TAKEN | CLOSED | FULL | REFUSED | UNCLEAR
  claim      --item --wait                     CLAIMED | NOT CLAIMED | CLOSED | FULL | REFUSED |
                                               UNREADABLE | UNCLEAR
  close-unarmed --item --wait --step [--wake-id]
             UNARMED | NOT CLAIMED | CLOSED | FULL | REFUSED | UNREADABLE | UNCLEAR
A `claim` run alone is a winner that stopped: it never sends, and only `reconcile` gives that
wait its closing record.

Rules the code keeps:
  - `orca` runs from an argument list, never through a shell. Every value on its command line
    passes a pattern first; free text reaches Orca only from files, by `--text-file`,
    `--note-file`, `--comment-file` or `--body-file`. The Head's files must be named
    item-<n>-W<k>-<part>.txt; the script writes its own header and the file's bytes to a new
    file and passes that.
  - Only the run whose claim returned an event id sends for a wait, posts its closing record
    or retires its wake as part of closing it. Other lines close nothing (`Reconcile note`,
    `Retire unverified`, `Carried`, `Rewake`, `Wait blocked`). The exceptions never send:
    FULL (the item is at Orca's 50-link cap, so the claim can't be linked) posts a `Wait blocked`
    line unless one is there and retires the wake; `reconcile --final` posts the closing record
    of a wait whose winner stopped (two at once can each post; the first counts, and the later
    one prints DUPLICATE); an arm whose item turned out closed retires the wake it made;
    `rewake` makes a one-time wake and posts a `Rewake` line, and links nothing.
  - A send happens only inside the `close` run whose claim returned an event id, after a fresh
    read of the item and of both sessions, and after a `Re-send` line posted. One send attempt
    per wait, never repeated, never from another command. No send under a key while an earlier
    wait under that key (on the item or along its Carried from chain, up to 5 items) has a
    `Re-send` line and no `Sent: msg_` receipt.
  - A run that won a claim starts no write or send once 5 minutes have passed since it claimed,
    so `reconcile --final` (the only other closing record) is refused until 15 minutes after the
    claim.
  - A successor wait arms only after every earlier wait has its closed marker and a closing
    record (a `Wake disposition` or `UNARMED` line) after it.
  - No command writes an item's status except `arm`'s Waiting write, and none closes an item.
  - Each orca call stops after 60 s and starts only when those 60 s fit inside the command's
    first 540 s, so a command ends within 10 minutes. A command's first read of the item is tried up to 3 times
    (15 s, then 45 s apart) on an error that can pass; a read that shows a marker link without
    its event is read again at once.

Exit codes: 0 the command's normal outcome (ARMED, OPEN, IDLE, CLAIMED, RETIRED, GONE, NOTED,
RECONCILED, REWOKEN, COVERED, RESTART; RESERVED for reserve); 1 UNCLEAR, UNREADABLE, UNCHECKED,
UNVERIFIED, SEND UNCLEAR, RETIRE UNVERIFIED, UNCOVERED, UNRECORDED or INCOMPLETE RESTART; 2 a
value or file refused before any Orca call; 3 any other outcome, a REFUSED after a read included.

Stdlib only, Python 3.9 or later. Offline tests: tooling/evals/test_head_wait.py.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

VERSION = "0.49.0"
ORCA = "orca"
CALL_TIMEOUT_S = 60       # one orca call
RUN_BUDGET_S = 540        # every orca call starts and ends inside this, so 10 minutes covers a run
READ_TRIES = 3            # a command's first read of the item, on an error that can pass
READ_PAUSES_S = (15, 45)  # the waits before the second and third tries
RE_READ_PAUSE_S = 2       # close-unarmed's wait before its second read
WINNER_WINDOW_S = 300
RECONCILE_AFTER_S = 900
ARM_MIN_LEAD_S = 120
DEADLINE_MIN_GAP_S = 120
WAITING_LEAD_S = 60
REWAKE_AFTER_S = 960      # past RECONCILE_AFTER_S, so a rewake after a claim can reconcile
REWAKE_MAX = 8
LINK_CAP = 50
LINKS_PER_WAIT = 2
TEXT_MAX = 8000
NOTE_MAX = 200
SHOW_PAGES_MAX = 400

EXIT_OK, EXIT_UNCLEAR, EXIT_USAGE, EXIT_OTHER = 0, 1, 2, 3

UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
TIME = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:00[+-]\d{2}:\d{2}"
RE_ITEM = re.compile(r"[1-9][0-9]{0,5}")
RE_WAIT = re.compile(r"W([1-9][0-9]{0,3})")
RE_TIME = re.compile(TIME)
RE_UUID = re.compile(UUID)
RE_SESSION = re.compile(r"(?:orca_session_id:)?(" + UUID + r")")
RE_TICKET = re.compile(r"VIL-[1-9][0-9]{0,5}")
RE_KEY = re.compile(
    r"VIL-[1-9][0-9]{0,5}/[A-Za-z0-9._-]{1,64}/Q[1-9][0-9]{0,3}"
    r"|[A-Za-z0-9._-]{1,100}/[A-Za-z0-9._-]{1,100}#[1-9][0-9]{0,6}@[0-9a-f]{40}"
    r"|msg_[0-9a-f]{12}")
RE_ADDRESS = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9:_.@/ -]{0,198}[A-Za-z0-9:_.@/-])?")
RE_BOT = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9 ._-]{0,62}[A-Za-z0-9._-])?")
RE_PATH = re.compile(r"/[A-Za-z0-9/._-]{1,1023}")
RE_EVENT = re.compile(r"e([1-9][0-9]{0,15})")


def real_times(*stamps: str) -> bool:
    try:
        for stamp in stamps:
            dt.datetime.fromisoformat(stamp)
    except ValueError:
        return False
    return True
RE_MSG = re.compile(r"msg_[0-9a-f]{12}")
RE_CARRIED = re.compile(r"([1-9][0-9]{0,5})/W([1-9][0-9]{0,3})")
RE_MARKER = re.compile(r"head-wait/item-([1-9][0-9]{0,5})/W([1-9][0-9]{0,3})(-closed)?")
RE_OWNER_SESSION = re.compile(r"orca_session_id:(" + UUID + r")")

OPEN_STATUSES = ("planned", "in_progress", "waiting")
CASES = {"no-follow-up": "no follow-up", "settled": "settled", "re-sent": "re-sent",
         "not-settled": "not settled"}
TRIGGER_CASES = {"wake": ("no-follow-up", "settled", "re-sent", "not-settled"),
                 "notice": ("settled", "not-settled"),
                 "look": ("settled", "not-settled")}
UNARMED_STEPS = ("record", "create", "verify", "fresh-read", "item-changed", "target-too-close",
                 "waiting", "manual", "reservation-without-record")


class Refused(Exception):
    """A value or file failed its check; nothing was sent to Orca."""


# ------------------------------------------------------------------------------ output


def say(line: str, *more: str) -> None:
    print(line)
    for m in more:
        if m:
            print(m)
    sys.stdout.flush()


def now_s() -> float:
    return time.time()


def mono() -> float:
    return time.monotonic()


def pause(seconds: float) -> None:
    time.sleep(seconds)


BUDGET = {"start": None}  # set by main(); functions called on their own have no budget


def budget_left() -> float:
    if BUDGET["start"] is None:
        return float("inf")
    return RUN_BUDGET_S - (mono() - BUDGET["start"])


def iso_utc(t: float) -> str:
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def in_pt(stamp: str) -> str:
    when = parse_time(stamp)
    try:
        from zoneinfo import ZoneInfo
        local = when.astimezone(ZoneInfo("America/Los_Angeles"))
        return local.strftime("%Y-%m-%d %H:%M PT")
    except Exception:  # no tz database: keep the stamp as given
        return stamp


def parse_time(stamp: str) -> dt.datetime:
    return dt.datetime.fromisoformat(stamp)


def ms(stamp: str) -> int:
    return int(parse_time(stamp).timestamp() * 1000)


# ------------------------------------------------------------------------------ checks


def need(pattern: re.Pattern, value: str, what: str) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise Refused(f"{what} fails its pattern")
    return value


def wait_number(value: str) -> int:
    m = RE_WAIT.fullmatch(value or "")
    if not m:
        raise Refused("--wait fails its pattern (W1 to W9999)")
    return int(m.group(1))


def need_time(value: str, what: str) -> str:
    need(RE_TIME, value, what)
    try:
        parse_time(value)
    except ValueError:
        raise Refused(f"{what} is not a real time")
    return value


def session_id(value: str, what: str) -> str:
    m = RE_SESSION.fullmatch(value or "")
    if not m:
        raise Refused(f"{what} fails its pattern (an Orca session id)")
    return m.group(1)


def utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def read_head_file(path: str, n: int, k: int, what: str) -> str:
    """A free-text file the Head wrote: an absolute plain path named item-<n>-W<k>-<part>.txt."""
    if not isinstance(path, str) or not RE_PATH.fullmatch(path):
        raise Refused(f"{what} fails its pattern (an absolute path of A-Z a-z 0-9 / . _ -)")
    if any(part in ("", ".", "..") for part in path.split("/")[1:]):
        raise Refused(f"{what} has an empty, . or .. part")
    name = path.rsplit("/", 1)[-1]
    if not re.fullmatch(rf"item-{n}-W{k}-[a-z0-9]+(?:-[a-z0-9]+)*\.txt", name):
        raise Refused(f"{what} must be named item-{n}-W{k}-<part>.txt")
    p = Path(path)
    if p.is_symlink() or not p.is_file():
        raise Refused(f"{what} is not a regular file")
    try:
        data = p.read_bytes()
    except OSError as e:
        raise Refused(f"{what} can't be read ({e.strerror})")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise Refused(f"{what} is not valid UTF-8")
    if "\x00" in text:
        raise Refused(f"{what} holds a NUL character")
    if not text.strip():
        raise Refused(f"{what} is empty")
    return text


# ------------------------------------------------------------------------------ orca


class Result:
    """One orca call: state is ok, error (Orca's error envelope), unclear or notrun."""

    def __init__(self, state: str, env: dict | None = None, detail: str = "") -> None:
        self.state = state
        self.env = env or {}
        self.detail = detail

    @property
    def result(self) -> dict:
        r = self.env.get("result")
        return r if isinstance(r, dict) else {}

    @property
    def code(self) -> str:
        err = self.env.get("error")
        return err.get("code", "") if isinstance(err, dict) else ""

    @property
    def message(self) -> str:
        err = self.env.get("error")
        m = err.get("message", "") if isinstance(err, dict) else ""
        return m if isinstance(m, str) else ""

    @property
    def error_data(self) -> dict:
        err = self.env.get("error")
        d = err.get("data") if isinstance(err, dict) else None
        return d if isinstance(d, dict) else {}

    def describe(self) -> str:
        if self.state == "ok":
            return "ok"
        if self.state == "error":
            return f"{self.code}: {self.message}"
        return self.detail


def _exec(argv: list, timeout: int) -> tuple:
    """Run orca from an argument list, never a shell. Returns (exit code, stdout bytes)."""
    p = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=timeout, check=False)
    return p.returncode, p.stdout


def run_orca(args: list, timeout: int = CALL_TIMEOUT_S) -> Result:
    argv = [ORCA] + list(args)
    if not all(isinstance(a, str) for a in argv):
        raise TypeError("orca arguments must be strings")
    if budget_left() < timeout:  # a call starts only when its whole timeout fits
        return Result("notrun", detail=f"not run: the command's {RUN_BUDGET_S} s are spent")
    try:
        code, stdout = _exec(argv, timeout)
    except FileNotFoundError:
        return Result("notrun", detail="orca is not on PATH")
    except subprocess.TimeoutExpired:
        return Result("unclear", detail=f"orca gave no answer in {timeout} s")
    except OSError as e:
        return Result("notrun", detail=f"orca could not start: {e}")
    return parse_envelope(code, stdout)


def parse_envelope(code: int, stdout: bytes) -> Result:
    out = stdout.decode("utf-8", "replace").strip()
    try:
        env = json.loads(out)
    except ValueError:
        return Result("unclear", detail=f"exit {code}; the output is not Orca's JSON")
    if not isinstance(env, dict) or not isinstance(env.get("ok"), bool):
        return Result("unclear", detail=f"exit {code}; the output is not Orca's envelope")
    if env["ok"]:
        if code != 0 or not isinstance(env.get("result"), dict):
            return Result("unclear", env, f"exit {code} with ok: true")
        return Result("ok", env)
    err = env.get("error")
    if not isinstance(err, dict) or not isinstance(err.get("code"), str):
        return Result("unclear", env, f"exit {code}; an error with no code")
    return Result("error", env)


class Scratch:
    """Files the script writes for -file flags: its header plus the Head's bytes."""

    def __init__(self) -> None:
        self.dir = tempfile.mkdtemp(prefix="head-wait-")

    def file(self, name: str, text: str) -> str:
        path = os.path.join(self.dir, name)
        with open(path, "x", encoding="utf-8", newline="") as fh:
            fh.write(text)
        return path

    def close(self) -> None:
        """Best effort: a cleanup error never replaces the command's outcome line."""
        shutil.rmtree(self.dir, ignore_errors=True)


# ------------------------------------------------------------------------------ the item


class Item:
    def __init__(self, item: dict, events: list) -> None:
        self.raw = item
        self.number = item.get("number")
        self.status = item.get("status")
        wait = item.get("wait") if isinstance(item.get("wait"), dict) else None
        self.wait_text = wait.get("text") if wait else None
        self.wait_at = wait.get("at") if wait else None
        self.snoozed_until = item.get("snoozedUntil")
        owner = item.get("owner") if isinstance(item.get("owner"), dict) else {}
        self.owner_bot = owner.get("botId")
        self.owner_name = owner.get("name")
        self.links = [(l.get("kind"), l.get("ref")) for l in item.get("links") or []
                      if isinstance(l, dict)]
        self.events = [e for e in events if isinstance(e, dict) and RE_EVENT.fullmatch(
            str(e.get("id", "")))]

    def own_comments(self) -> list:
        out = []
        for e in self.events:
            actor = e.get("actor") if isinstance(e.get("actor"), dict) else {}
            data = e.get("data") if isinstance(e.get("data"), dict) else {}
            if (e.get("kind") == "commented" and actor.get("kind") == "bot"
                    and actor.get("botId") == self.owner_bot and isinstance(data.get("text"), str)):
                out.append(e)
        return out

    def link_event(self, ref: str) -> dict | None:
        want = "file:" + ref
        for e in self.events:
            data = e.get("data") if isinstance(e.get("data"), dict) else {}
            if e.get("kind") == "linked" and want in (data.get("links") or []):
                return e
        return None


def eid(event: dict | None) -> int:
    m = RE_EVENT.fullmatch(str((event or {}).get("id", "")))
    return int(m.group(1)) if m else -1


def read_pages(n: int) -> tuple:
    """One read of the item and every event, paged with --after.
    Returns (Item, None, False) or (None, reason, whether the error can pass)."""
    events: list = []
    after = None
    item = None
    for _ in range(SHOW_PAGES_MAX):
        args = ["bot", "item", "show", "--id", str(n)] + (["--after", after] if after else [])
        res = run_orca(args + ["--json"])
        if res.state != "ok" or not isinstance(res.result.get("item"), dict):
            passing = res.state == "unclear" or (res.state == "error"
                                                 and res.code not in DEFINITE_ERRORS)
            return None, f"bot item show: {res.describe()}", passing
        item = res.result["item"]
        page = res.result.get("events") or []
        if not isinstance(page, list):
            return None, "bot item show: events is not a list", True
        events.extend(page)
        cursor = res.result.get("nextCursor")
        if not cursor:
            break
        if not isinstance(cursor, str) or not RE_EVENT.fullmatch(cursor) or cursor == after:
            return None, "bot item show: a cursor it did not print", False
        after = cursor
    else:
        return None, "bot item show: too many pages", False
    if item.get("number") != n:
        return None, "bot item show: another item came back", False
    return Item(item, events), None, False


def unsettled_markers(item: Item) -> bool:
    """A marker link whose `linked` event the read missed. Orca's show reads the events first and
    the item second, so a link added between the two shows up without its event."""
    return any(kind == "file" and isinstance(ref, str) and ref.startswith("head-wait/")
               and item.link_event(ref) is None for kind, ref in item.links)


def read_item(n: int, tries: int = 1) -> tuple:
    """Returns (Item, None) or (None, reason). Up to `tries` reads while the error is one that
    can pass, with READ_PAUSES_S between them; a read that shows a marker link without its event
    is read again at once, up to twice."""
    why, done = "", 0
    for attempt in range(tries):
        if attempt:
            wait_s = READ_PAUSES_S[min(attempt, len(READ_PAUSES_S)) - 1]
            if budget_left() < wait_s + CALL_TIMEOUT_S:
                break
            pause(wait_s)
        done += 1
        for _ in range(3):
            item, why, passing = read_pages(n)
            if item is None or not unsettled_markers(item):
                break
        if item is not None:
            return item, None
        if not passing:
            return None, why
    return None, why + (f" ({done} tries)" if done > 1 else "")


def marker(n: int, k: int, closed: bool = False) -> str:
    return f"head-wait/item-{n}/W{k}" + ("-closed" if closed else "")


RECORD_LINE = re.compile(
    r"Wait record, item (\d+) W(\d+)\. Owner: (.+?) \(session (" + UUID + r")\)\. "
    r"Waiting work: session (" + UUID + r")\. Ticket: (VIL-\d+)\. Key: (\S+)\. "
    r"Wake target: (" + TIME + r")\. Deadline: (" + TIME + r") \([^()\n]*\)\. "
    r"Item at arm: ([a-z_]+), wait (\d+|none)\.(?: Carried from: item (\d+) W(\d+)\.)?")
ARMED_LINE = re.compile(r"Armed, item (\d+) W(\d+): wake (" + UUID + r"), target (" + TIME
                        + r"), deadline (" + TIME + r")\.")
REWAKE_LINE = re.compile(r"Rewake, item (\d+) W(\d+): wake (" + UUID + r"), target (" + TIME
                         + r")\.")
SNOOZE_LINE = re.compile(r"Snoozed until (\S+)")
UNSNOOZE_LINE = re.compile(r"Unsnoozed\b")
SENT_RECEIPT = re.compile(r"\bSent: msg_[0-9a-f]{12} to ")


class Wait:
    """What the item shows for one wait W<k>, from its links and the owner bot's own lines."""

    def __init__(self, item: Item, k: int) -> None:
        n = item.number
        self.k = k
        self.reserved = (("file", marker(n, k)) in item.links)
        self.closed = (("file", marker(n, k, True)) in item.links)
        self.reserved_ev = item.link_event(marker(n, k)) if self.reserved else None
        self.closed_ev = item.link_event(marker(n, k, True)) if self.closed else None
        self.record = self.record_fields = self.armed = self.closing = None
        self.resend = self.blocked = self.carried = None
        self.notes: list = []
        self.rewakes: list = []
        start = eid(self.reserved_ev)
        tag = f", item {n} W{k}"
        for e in item.own_comments():
            text = e["data"]["text"]
            first = text.split("\n", 1)[0]
            if self.record is None and eid(e) > start >= 0 and first.startswith(
                    f"Wait record{tag}. "):
                m = RECORD_LINE.fullmatch(first)
                if m and int(m.group(1)) == n and int(m.group(2)) == k and real_times(
                        m.group(8), m.group(9)):
                    self.record, self.record_fields = e, m
            elif self.armed is None and self.record is not None and first.startswith(
                    f"Armed{tag}: "):
                m = ARMED_LINE.fullmatch(first)
                if m and int(m.group(1)) == n and int(m.group(2)) == k:
                    self.armed = (e, m.group(3), m.group(4), m.group(5))
            elif (self.closing is None and self.closed_ev is not None and eid(e) > eid(
                    self.closed_ev) and (first.startswith(f"Wake disposition{tag}: ")
                                         or first.startswith(f"UNARMED{tag}: "))):
                self.closing = e
            elif self.resend is None and first.startswith(f"Re-send{tag}: "):
                self.resend = e
            elif self.blocked is None and first.startswith(f"Wait blocked{tag}: "):
                self.blocked = e
            elif self.carried is None and first.startswith(f"Carried{tag}: "):
                self.carried = e
            elif first.startswith(f"Reconcile note{tag}: "):
                self.notes.append(e)
            elif eid(e) > start >= 0 and first.startswith(f"Rewake{tag}: "):
                m = REWAKE_LINE.fullmatch(first)
                if m and int(m.group(1)) == n and int(m.group(2)) == k and real_times(m.group(4)):
                    self.rewakes.append((e, m.group(3), m.group(4)))

    def field(self, name: str) -> str:
        names = ("item", "k", "owner", "owner_session", "waiting_session", "ticket", "key",
                 "target", "deadline", "status_at_arm", "wait_at_arm", "carried_item",
                 "carried_wait")
        return self.record_fields.group(names.index(name) + 1)

    def current_wake(self) -> tuple | None:
        """(line event, wake id, target) of the latest Armed or Rewake line, or None."""
        wakes = ([self.armed[:3]] if self.armed else []) + self.rewakes
        return max(wakes, key=lambda w: eid(w[0])) if wakes else None

    def wake_id(self) -> str | None:
        cur = self.current_wake()
        return cur[1] if cur else None


def markers_on(item: Item) -> dict:
    """{k: (has W<k>, has W<k>-closed)} for this item's own markers. Any marker found counts."""
    seen: dict = {}
    for kind, ref in item.links:
        m = RE_MARKER.fullmatch(ref) if kind == "file" and isinstance(ref, str) else None
        if not m or int(m.group(1)) != item.number:
            continue
        k = int(m.group(2))
        has_open, has_closed = seen.get(k, (False, False))
        seen[k] = (has_open or not m.group(3), has_closed or bool(m.group(3)))
    return seen


def gate(item: Item) -> tuple:
    """Arm step 0 on a read item: (next k, None) or (None, the reason it is blocked)."""
    if item.status not in OPEN_STATUSES:
        return None, f"the item is {item.status}; a wait arms only on a planned, in-progress " \
                     "or waiting item"
    seen = markers_on(item)
    for k in sorted(seen):
        w = Wait(item, k)
        if w.blocked is not None:
            return None, f"W{k} is blocked at Orca's link cap; carry the work to a fresh item"
        if not w.reserved:
            continue  # a stray W<k>-closed: nothing can act on it, and k counts past it
        if not w.closed:
            return None, f"W{k} is open"
        if w.closing is None:
            return None, f"W{k} is closed with no closing record; reconcile it first"
    if len(item.links) > LINK_CAP - LINKS_PER_WAIT:
        return None, f"the item has {len(item.links)} links; a wait needs {LINKS_PER_WAIT} free " \
                     f"of Orca's {LINK_CAP}"
    return (max(seen) + 1 if seen else 1), None


# ------------------------------------------------------------------------------ markers


def link_outcome(res: Result, won: str, lost: str) -> str:
    if res.state == "notrun":
        return "REFUSED"
    if res.state == "ok":
        event = res.result.get("eventId")
        if isinstance(event, str) and RE_EVENT.fullmatch(event):
            return won
        if res.result.get("unchanged") is True and event is None:
            return lost
        return "UNCLEAR"
    if res.state == "error":
        code, message = res.code, res.message.strip()
        if code == "item_closed":
            return "CLOSED"
        if code == "invalid_argument" and message == f"An item takes up to {LINK_CAP} links.":
            return "FULL"
        if code == "not_found" and message != "The item is gone.":
            return "REFUSED"
        if code in ("not_owner", "items_read_only", "invalid_argument"):
            return "REFUSED"
    return "UNCLEAR"


def link_marker(n: int, k: int, closed: bool) -> tuple:
    res = run_orca(["bot", "item", "link", "--id", str(n), "--ref", marker(n, k, closed),
                    "--json"])
    word = link_outcome(res, "CLAIMED" if closed else "RESERVED",
                        "NOT CLAIMED" if closed else "TAKEN")
    return word, res


def post(n: int, text: str, scratch: Scratch, name: str) -> Result:
    if utf16_len(text) > TEXT_MAX:
        return Result("notrun", detail=f"the line is over Orca's {TEXT_MAX} characters")
    path = scratch.file(name, text)
    return run_orca(["bot", "item", "comment", "--id", str(n), "--text-file", path, "--json"])


def posted(res: Result) -> str | None:
    event = res.result.get("eventId") if res.state == "ok" else None
    return event if isinstance(event, str) and RE_EVENT.fullmatch(event) else None


DEFINITE_ERRORS = ("item_closed", "invalid_argument", "not_found", "not_owner",
                   "items_read_only")


def may_have_landed(res: Result) -> bool:
    """A write whose result doesn't rule out that it landed (O13: items_unavailable says so)."""
    if res.state in ("unclear",):
        return True
    if res.state == "ok":
        return posted(res) is None
    return res.state == "error" and res.code not in DEFINITE_ERRORS


def clip(text: str, limit: int = 2000) -> str:
    return text if len(text) <= limit else text[:limit] + " [cut]"


class Clock:
    """A claim winner's write window: no write or send starts after WINNER_WINDOW_S."""

    def __init__(self) -> None:
        self.wall, self.mono = now_s(), mono()

    def ok(self) -> bool:
        return now_s() - self.wall < WINNER_WINDOW_S and mono() - self.mono < WINNER_WINDOW_S


# ------------------------------------------------------------------------------ retire


def retire(n: int, k: int, wake: str, scratch: Scratch, clock: Clock | None = None) -> str:
    """Disable a wake. RETIRED only on a read-back of enabled: false; GONE only on exactly
    "Automation not found."; anything else is UNVERIFIED and gets a visible line."""
    if clock is not None and not clock.ok():
        return f"UNVERIFIED item {n} W{k}: wake {wake}: not tried, the run is past its " \
               f"{WINNER_WINDOW_S // 60}-minute window; retire it by hand"
    res = run_orca(["automations", "edit", "--id", wake, "--disabled", "--json"])
    auto = res.result.get("automation") if res.state == "ok" else None
    if isinstance(auto, dict) and auto.get("id") == wake and auto.get("enabled") is False:
        return f"RETIRED item {n} W{k}: wake {wake}"
    if res.state == "error" and res.message.strip() == "Automation not found.":
        return f"GONE item {n} W{k}: wake {wake}"
    why = res.describe() if not isinstance(auto, dict) else \
        f"the result shows enabled: {auto.get('enabled')!r} for {auto.get('id')!r}"
    if clock is not None and not clock.ok():
        return f"UNVERIFIED item {n} W{k}: wake {wake}: {why}; out of time, no Retire " \
               "unverified line"
    line = f"Retire unverified, item {n} W{k}: wake {wake}.\nOrca: {clip(why)}"
    note = posted(post(n, line, scratch, "retire.txt"))
    return f"UNVERIFIED item {n} W{k}: wake {wake}: {why}; " + (
        f"Retire unverified line {note}" if note else "the Retire unverified line did not post")


# ------------------------------------------------------------------------------ arm steps


def post_blocked(n: int, k: int, scratch: Scratch) -> str:
    """FULL: post the Wait blocked line unless the item already has one for W<k>."""
    item, _ = read_item(n)
    if item is not None and Wait(item, k).blocked is not None:
        return f"Wait blocked line {Wait(item, k).blocked['id']} already there"
    note = posted(post(n, blocked_line(n, k), scratch, "blocked.txt"))
    return f"Wait blocked line {note}" if note else "the Wait blocked line did not post"


def blocked_line(n: int, k: int) -> str:
    return (f"Wait blocked, item {n} W{k}: the item is at Orca's {LINK_CAP}-link cap, so "
            f"W{k}-closed can't be linked. Nothing was sent or closed for W{k}. Its work and any "
            "open owner decision stay open; they carry to a fresh item.")


def close_unarmed(n: int, k: int, step: str, error: str, wake: str | None, scratch: Scratch,
                  clock: Clock | None = None, wake_unknown: bool = False) -> tuple:
    """Claim W<k>-closed; on CLAIMED post the UNARMED line and retire a known wake."""
    clock = clock or Clock()
    word, res = link_marker(n, k, True)
    wake_word = wake if wake else ("unknown" if wake_unknown else "none")
    if word == "NOT CLAIMED":
        return EXIT_OTHER, f"NOT CLAIMED item {n} W{k}: its wake or another run holds W{k}; " \
                           "nothing more written"
    if word == "FULL":
        line = post_blocked(n, k, scratch)
        tail = retire(n, k, wake, scratch, clock) if wake else "no wake to retire"
        return EXIT_OTHER, f"FULL item {n} W{k}: the {step} step failed ({error}) and " \
                           f"W{k}-closed can't be linked; {line}; {tail}. Carry the work to a " \
                           "fresh item."
    if word == "CLOSED":
        tail = retire(n, k, wake, scratch, clock) if wake else "no wake to retire"
        return EXIT_OTHER, f"CLOSED item {n} W{k}: the {step} step failed ({error}); the item " \
                           f"is closed, so W{k}-closed can't be linked and nothing can act on " \
                           f"W{k}; {tail}; nothing else written"
    if word != "CLAIMED":
        return (EXIT_UNCLEAR if word == "UNCLEAR" else EXIT_OTHER), \
            f"{word} item {n} W{k}: the {step} step failed ({error}) and the close-unarmed claim " \
            f"gave {res.describe()}; reconcile"
    if not clock.ok():
        return EXIT_UNCLEAR, f"UNCLEAR item {n} W{k}: claimed W{k}-closed but out of time " \
                             "before the UNARMED line; reconcile"
    line = f"UNARMED, item {n} W{k}: {step}; wake {wake_word}.\nOrca: {clip(error)}"
    note = posted(post(n, line, scratch, "unarmed.txt"))
    tail = retire(n, k, wake, scratch, clock) if wake else "no wake to retire"
    if not note:
        return EXIT_UNCLEAR, f"UNCLEAR item {n} W{k}: claimed W{k}-closed after the {step} " \
                             f"step failed, but the UNARMED line did not post; {tail}; reconcile"
    return EXIT_OTHER, f"UNARMED item {n} W{k}: {step}: {error}; wake {wake_word}; line {note}; " \
                       f"{tail}"


def record_text(n: int, k: int, a: argparse.Namespace, item: Item, body: str) -> str:
    wait_at = item.wait_at if isinstance(item.wait_at, int) else "none"
    line = (f"Wait record, item {n} W{k}. Owner: {a.owner} (session {a.owner_session}). "
            f"Waiting work: session {a.waiting_session}. Ticket: {a.ticket}. Key: {a.key}. "
            f"Wake target: {a.target}. Deadline: {a.deadline} ({in_pt(a.deadline)}). "
            f"Item at arm: {item.status}, wait {wait_at}.")
    if a.carried_from:
        m, j = a.carried_from
        line += f" Carried from: item {m} W{j}."
    return line + "\n" + body


def wake_prompt(n: int, k: int, target: str) -> str:
    return (f"Wake for item {n} W{k}, target {target}. Follow \"Head's wake for a waiting item\" "
            f"in dv director-mode without turning Director Mode on; run its check for item {n} "
            f"W{k} first. The W{k} record on the item is the source, not this prompt.")


def step_record(n: int, k: int, a: argparse.Namespace, item: Item, body: str,
                scratch: Scratch) -> tuple:
    res = post(n, record_text(n, k, a, item, body), scratch, "record.txt")
    return posted(res), res


def step_create(n: int, k: int, item: Item, target: str, name: str | None = None) -> tuple:
    """(automation id or None, error or None, whether a wake may exist with an unknown id)."""
    bot = item.owner_name
    if not isinstance(bot, str) or not RE_BOT.fullmatch(bot):
        return None, "the item's bot name fails its pattern", False
    res = run_orca(["automations", "create", "--bot", bot, "--name", name or f"Item {n} W{k}",
                    "--once", "--by", target, "--prompt", wake_prompt(n, k, target), "--json"])
    auto = res.result.get("automation") if res.state == "ok" else None
    if not isinstance(auto, dict):
        return None, f"automations create: {res.describe()}", res.state in ("ok", "unclear")
    wake = auto.get("id") if isinstance(auto.get("id"), str) and RE_UUID.fullmatch(
        auto.get("id")) else None
    once = auto.get("once") if isinstance(auto.get("once"), dict) else {}
    bot_view = auto.get("bot") if isinstance(auto.get("bot"), dict) else {}
    problems = []
    if wake is None:
        problems.append("no automation id")
    if auto.get("enabled") is not True:
        problems.append(f"enabled is {auto.get('enabled')!r}")
    if once.get("by") != ms(target):
        problems.append(f"once.by is {once.get('by')!r}, not {ms(target)}")
    if bot_view.get("botId") != item.owner_bot:
        problems.append("bot.botId is not the item's bot")
    if auto.get("on") not in (None, []):
        problems.append("it has an event trigger")
    if problems:
        return wake, "verify: " + "; ".join(problems), wake is None
    return wake, None, False


def step_waiting(n: int, k: int, wake: str, scratch: Scratch) -> tuple:
    """Arm steps 4 to 6 on the item as it is now. Returns (exit, first line, Waiting written)."""
    item, why = read_item(n)
    if item is None:
        return close_unarmed(n, k, "fresh-read", why, wake, scratch) + (False,)
    w = Wait(item, k)
    if w.closed:
        return EXIT_OTHER, f"OVERTAKEN item {n} W{k}: W{k}-closed is already linked; no Waiting " \
                           "write and no UNARMED line (whoever closed it writes its line)", False
    if w.record is None:
        return close_unarmed(n, k, "fresh-read", "no W%d record on the item" % k, wake,
                             scratch) + (False,)
    target, deadline = w.field("target"), w.field("deadline")
    at_arm = (w.field("status_at_arm"), w.field("wait_at_arm"))
    now_view = (item.status, str(item.wait_at) if isinstance(item.wait_at, int) else "none")
    if now_view != at_arm:
        return close_unarmed(n, k, "item-changed", "the item's status or wait changed while "
                             f"arming: {at_arm[0]}, wait {at_arm[1]} at the reservation; "
                             f"{now_view[0]}, wait {now_view[1]} now", wake, scratch) + (False,)
    if now_s() > ms(target) / 1000 - WAITING_LEAD_S:
        return close_unarmed(n, k, "target-too-close", f"the wake target {target} is less than "
                             f"{WAITING_LEAD_S} s away, so its wake may run before Waiting",
                             wake, scratch) + (False,)
    note = f"W{k} wake {wake[:8]} by {in_pt(deadline)}; record {w.record['id']}"
    if len(note) > NOTE_MAX:
        note = f"W{k} wake {wake[:8]}; record {w.record['id']}"
    armed = f"Armed, item {n} W{k}: wake {wake}, target {target}, deadline {deadline}."
    res = run_orca(["bot", "item", "set", "--id", str(n), "--status", "waiting", "--note-file",
                    scratch.file("note.txt", note), "--comment-file",
                    scratch.file("armed.txt", armed), "--json"])
    landed = posted(res) is not None
    if not landed and may_have_landed(res):
        again, _ = read_item(n)
        landed = bool(again and again.status == "waiting" and isinstance(again.wait_text, str)
                      and again.wait_text.startswith(f"W{k} "))
    if not landed:
        return close_unarmed(n, k, "waiting", f"bot item set: {res.describe()}", wake,
                             scratch) + (False,)
    after, why = read_item(n)
    if after is None:
        return EXIT_UNCLEAR, f"UNCHECKED item {n} W{k}: Waiting written with wake {wake}, target " \
                             f"{target}, deadline {deadline}, but the read after it failed " \
                             f"({why}); run check", True
    if Wait(after, k).closed:
        return EXIT_OTHER, f"SPENT item {n} W{k}: Waiting written with wake {wake}, but " \
                           f"W{k}-closed was linked right after, so the item reads Waiting on a " \
                           "closed wait", True
    return EXIT_OK, f"ARMED item {n} W{k}: wake {wake}, target {target}, deadline {deadline}", True


# ------------------------------------------------------------------------------ commands


def arm_inputs(a: argparse.Namespace) -> tuple:
    n = int(need(RE_ITEM, a.item, "--item"))
    k = wait_number(a.wait)
    need_time(a.target, "--target")
    need_time(a.deadline, "--deadline")
    if ms(a.deadline) < ms(a.target) + DEADLINE_MIN_GAP_S * 1000:
        raise Refused(f"--deadline must be at least {DEADLINE_MIN_GAP_S // 60} minutes after "
                      "--target")
    need(RE_ADDRESS, a.owner, "--owner")
    a.owner_session = session_id(a.owner_session, "--owner-session")
    a.waiting_session = session_id(a.waiting_session, "--waiting-session")
    named = RE_OWNER_SESSION.fullmatch(a.owner)
    if named and named.group(1) != a.owner_session:
        raise Refused("--owner names one session and --owner-session another")
    need(RE_TICKET, a.ticket, "--ticket")
    need(RE_KEY, a.key, "--key")
    a.carried_from = None
    if getattr(a, "carried", None):
        m = RE_CARRIED.fullmatch(a.carried)
        if not m or int(m.group(1)) == n:
            raise Refused("--carried-from fails its pattern (<item>/W<k>, another item)")
        a.carried_from = (int(m.group(1)), int(m.group(2)))
    body = read_head_file(a.record_file, n, k, "--record-file")
    return n, k, body


def carry_problem(a: argparse.Namespace, new: Item) -> str | None:
    """--carried-from <m>/W<j> only from a wait the cap blocked, with the same owner and key."""
    m, j = a.carried_from
    old, why = read_item(m)
    if old is None:
        return f"item {m} can't be read ({why})"
    if old.owner_bot != new.owner_bot:
        return f"item {m} belongs to another bot"
    w = Wait(old, j)
    if w.blocked is None:
        seen = markers_on(old)
        at_cap = len(old.links) > LINK_CAP - LINKS_PER_WAIT
        if not (at_cap and not w.reserved and j == (max(seen) + 1 if seen else 1)):
            return f"item {m} W{j} has no Wait blocked line, and isn't the next wait of an " \
                   "item at the link cap"
    if w.record is not None:
        mine = {"owner": a.owner, "owner_session": a.owner_session,
                "waiting_session": a.waiting_session, "ticket": a.ticket, "key": a.key}
        for field, value in mine.items():
            if w.field(field) != value:
                return f"its {field.replace('_', ' ')} differs from item {m} W{j}'s record"
    return None


def cmd_arm(a: argparse.Namespace) -> tuple:
    n, k, body = arm_inputs(a)
    if ms(a.target) / 1000 < now_s() + ARM_MIN_LEAD_S:
        return EXIT_OTHER, f"BLOCKED item {n} W{k}: the target must be at least " \
                           f"{ARM_MIN_LEAD_S} s ahead; nothing written"
    item, why = read_item(n, READ_TRIES)
    if item is None:
        return EXIT_UNCLEAR, f"UNREADABLE item {n} W{k}: {why}; nothing written"
    if utf16_len(record_text(n, k, a, item, body)) > TEXT_MAX:
        return EXIT_OTHER, f"REFUSED item {n} W{k}: the record is over Orca's {TEXT_MAX} " \
                           "characters; nothing written"
    nxt, why = gate(item)
    if nxt is None:
        return EXIT_OTHER, f"BLOCKED item {n} W{k}: {why}; nothing written"
    if nxt != k:
        return EXIT_OTHER, f"BLOCKED item {n} W{k}: the next wait on this item is W{nxt}; " \
                           "nothing written"
    if a.carried_from:
        why = carry_problem(a, item)
        if why:
            return EXIT_OTHER, f"BLOCKED item {n} W{k}: --carried-from: {why}; nothing written"
    scratch = Scratch()
    try:
        word, res = link_marker(n, k, False)
        if word == "TAKEN":
            return EXIT_OTHER, f"TAKEN item {n} W{k}: another run reserved W{k}; nothing " \
                               "written, and no other key tried"
        if word != "RESERVED":
            code = EXIT_UNCLEAR if word == "UNCLEAR" else EXIT_OTHER
            return code, f"{word} item {n} W{k}: the reservation gave {res.describe()}; " \
                         "nothing else written"
        record, res = step_record(n, k, a, item, body, scratch)
        if record is None:
            return close_unarmed(n, k, "record", res.describe(), None, scratch)
        wake, err, unknown = step_create(n, k, item, a.target)
        if err:
            return close_unarmed(n, k, "verify" if wake or err.startswith("verify") else "create",
                                 err, wake, scratch, wake_unknown=unknown)
        code, line, written = step_waiting(n, k, wake, scratch)
        if written and a.carried_from:
            m, j = a.carried_from
            res = post(m, f"Carried, item {m} W{j}: to item {n} W{k}, wake {wake}.", scratch,
                       "carried.txt")
            note = posted(res)
            line += f"; Carried line on item {m}: " + (note or f"not posted ({res.describe()})")
        return code, line
    finally:
        scratch.close()


def cmd_reserve(a: argparse.Namespace) -> tuple:
    n, k = int(need(RE_ITEM, a.item, "--item")), wait_number(a.wait)
    word, res = link_marker(n, k, False)
    code = EXIT_OK if word == "RESERVED" else (EXIT_UNCLEAR if word == "UNCLEAR" else EXIT_OTHER)
    return code, f"{word} item {n} W{k}: {res.describe() if word != 'RESERVED' else 'linked'}"


def cmd_claim(a: argparse.Namespace) -> tuple:
    n, k = int(need(RE_ITEM, a.item, "--item")), wait_number(a.wait)
    item, why = read_item(n, READ_TRIES)
    if item is None:
        return EXIT_UNCLEAR, f"UNREADABLE item {n} W{k}: {why}; nothing written"
    if not Wait(item, k).reserved:
        return EXIT_OTHER, f"REFUSED item {n} W{k}: no W{k} marker, so it can't be closed"
    word, res = link_marker(n, k, True)
    code = EXIT_OK if word == "CLAIMED" else (EXIT_UNCLEAR if word == "UNCLEAR" else EXIT_OTHER)
    tail = "a winner that stops here; only reconcile gives W%d its closing record" % k
    return code, f"{word} item {n} W{k}: " + (tail if word == "CLAIMED" else res.describe())


def cmd_close_unarmed(a: argparse.Namespace) -> tuple:
    n, k = int(need(RE_ITEM, a.item, "--item")), wait_number(a.wait)
    if a.step not in UNARMED_STEPS:
        raise Refused("--step is not one of " + ", ".join(UNARMED_STEPS))
    wake = need(RE_UUID, a.wake_id, "--wake-id") if a.wake_id else None
    item, why = read_item(n, READ_TRIES)
    if item is not None:  # an arm in flight posts its record and Armed line within seconds
        pause(RE_READ_PAUSE_S)
        item, why = read_item(n, READ_TRIES)
    if item is None:
        return EXIT_UNCLEAR, f"UNREADABLE item {n} W{k}: {why}; nothing written"
    w = Wait(item, k)
    if not w.reserved:
        return EXIT_OTHER, f"REFUSED item {n} W{k}: no W{k} marker, so it can't be closed"
    if w.armed is not None:
        return EXIT_OTHER, f"REFUSED item {n} W{k}: it has an Armed line {w.armed[0]['id']}; " \
                           "an armed wait is closed by close, not unarmed"
    if a.step == "reservation-without-record" and w.record is not None:
        return EXIT_OTHER, f"REFUSED item {n} W{k}: it has a record {w.record['id']}"
    detail = {"manual": "closed unarmed by hand",
              "reservation-without-record": "reservation without a record"}.get(
        a.step, "closed unarmed by hand at this step")
    scratch = Scratch()
    try:
        return close_unarmed(n, k, a.step, detail, wake, scratch)
    finally:
        scratch.close()


def describe_wait(item: Item, w: Wait) -> str:
    n, k = item.number, w.k
    if w.reserved and not w.closed:
        if w.record is None:
            return f"OPEN item {n} W{k}: reserved with no record"
        cur = w.current_wake()
        return (f"OPEN item {n} W{k}: record {w.record['id']}; owner {w.field('owner')} "
                f"(session {w.field('owner_session')}); waiting session "
                f"{w.field('waiting_session')}; ticket {w.field('ticket')}; key {w.field('key')}; "
                f"target {w.field('target')}; deadline {w.field('deadline')}; wake "
                + (f"{cur[1]} at {cur[2]}" if cur else "none recorded"))
    if w.closed:
        if w.closing is not None:
            return f"CLOSED item {n} W{k}: closing record {w.closing['id']}"
        return f"CLOSED item {n} W{k}: no closing record yet; reconcile"
    return f"NO WAIT item {n} W{k}: no W{k} marker"


def cmd_check(a: argparse.Namespace) -> tuple:
    n = int(need(RE_ITEM, a.item, "--item"))
    k = wait_number(a.wait) if a.wait else None
    item, why = read_item(n, READ_TRIES)
    if item is None:
        return EXIT_UNCLEAR, f"UNREADABLE item {n}: {why}"
    if k is not None:
        w = Wait(item, k)
        if item.status in ("done", "canceled") and w.reserved:
            return EXIT_OTHER, f"CLOSED item {n} W{k}: the item is {item.status}; nothing to do"
        if w.blocked is not None:
            return EXIT_OTHER, f"BLOCKED item {n} W{k}: at Orca's link cap ({w.blocked['id']}); " + (
                f"carried ({w.carried['id']})" if w.carried else "not carried to a fresh item yet")
        line = describe_wait(item, w)
        return (EXIT_OK if line.startswith("OPEN") else EXIT_OTHER), line
    nxt, why = gate(item)
    if nxt is not None:
        return EXIT_OK, f"IDLE item {n}: no open wait; the next is W{nxt}"
    seen = markers_on(item)
    opened = [j for j, (o, c) in seen.items() if o and not c]
    if opened:
        line = describe_wait(item, Wait(item, opened[0]))
        return (EXIT_OK if line.startswith("OPEN") else EXIT_OTHER), line
    return EXIT_OTHER, f"BLOCKED item {n}: {why}"


def close_header(n: int, k: int, case: str, trigger: str, w: Wait, reconciled: bool) -> str:
    deadline = w.field("deadline")
    missed = "yes" if now_s() * 1000 > ms(deadline) else "no"
    tag = " (reconciled)" if reconciled else ""
    return (f"Wake disposition, item {n} W{k}: {CASES[case]}{tag}. Trigger: {trigger} at "
            f"{iso_utc(now_s())}. Deadline: {deadline}; missed: {missed}.")


def require_sections(text: str, case: str, what: str) -> None:
    lines = [l.strip() for l in text.splitlines()]
    wanted = ["Evidence:"] + ([] if case == "settled" else ["Blocker:", "Next check:"])
    for head in wanted:
        if not any(l.startswith(head) for l in lines):
            raise Refused(f"{what} has no line starting {head!r}")


def snooze_line(item: Item, now_ms: float) -> dict | None:
    """The latest `Snoozed until` comment on the item, by anyone, when no `Unsnoozed` comment
    follows it and its time is ahead, has no time zone, or can't be read; else None. Any age
    counts: an old undated line holds until an `Unsnoozed` line or a later `Snoozed until` line
    ends it."""
    latest = None
    for e in item.events:
        data = e.get("data") if isinstance(e.get("data"), dict) else {}
        text = data.get("text")
        if e.get("kind") != "commented" or not isinstance(text, str):
            continue
        if SNOOZE_LINE.match(text):
            latest = e
        elif UNSNOOZE_LINE.match(text):
            latest = None
    if latest is None:
        return None
    stamp = SNOOZE_LINE.match(latest["data"]["text"]).group(1).rstrip(":.,;")
    try:
        until = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return latest
    return latest if until.tzinfo is None or until.timestamp() * 1000 > now_ms else None


CARRY_HOPS_MAX = 5


def unclear_send(item: Item, w: Wait) -> str | None:
    """Correction 1 per key: an earlier wait under the same key with a `Re-send` line and no
    `Sent: msg_` receipt in its closing record may have sent, so no wait under that key sends
    again. Looks at earlier waits on this item and along the record's `Carried from` chain."""
    key = w.field("key")
    here, last, origin = item, w.k - 1, w  # on each item, waits W1 to W<last>
    for hops in range(CARRY_HOPS_MAX + 1):
        for j in sorted(markers_on(here)):
            wj = Wait(here, j) if j <= last else None
            if wj is None or wj.record is None or wj.resend is None or wj.field("key") != key:
                continue
            first = wj.closing["data"]["text"].split("\n", 1)[0] if wj.closing else ""
            if not SENT_RECEIPT.search(first):
                return f"item {here.number} W{j}, under the same key, has a Re-send line " \
                       f"{wj.resend['id']} and no Sent receipt, so a send may have gone"
        if origin.record is None or origin.field("carried_item") is None:
            return None
        if hops == CARRY_HOPS_MAX:
            break
        m, last = int(origin.field("carried_item")), int(origin.field("carried_wait"))
        here, why = read_item(m)
        if here is None:
            return f"item {m}, carried from, can't be read to rule out a send ({why})"
        origin = Wait(here, last)
    return f"the Carried from chain is longer than {CARRY_HOPS_MAX} items"


def fresh_send_check(n: int, k: int, item: Item | None, w: Wait | None) -> tuple:
    """Right before a re-send: (None, None) when it may go, else (case, reason)."""
    if item is None or w is None or w.record is None:
        return "not-settled", "the fresh read failed, so nothing was sent"
    if w.closing is not None:
        return "stop", f"a closing record {w.closing['id']} is already there"
    if w.resend is not None:
        return "not-settled", f"a Re-send line {w.resend['id']} is already there"
    if item.status == "needs_you":
        return "no-follow-up", "the item reads Needs you"
    if item.status not in OPEN_STATUSES:
        return "no-follow-up", f"the item reads {item.status}"
    now_ms = now_s() * 1000
    if isinstance(item.snoozed_until, (int, float)) and item.snoozed_until > now_ms:
        return "no-follow-up", "Orca's snooze is ahead"
    start = eid(w.record)
    for e in item.events:
        data = e.get("data") if isinstance(e.get("data"), dict) else {}
        if e.get("kind") == "status" and eid(e) > start and data.get("to") in ("done", "canceled"):
            return "no-follow-up", f"the item was closed after the record ({e['id']})"
    held = snooze_line(item, now_ms)
    if held is not None:
        return "no-follow-up", f"a Snoozed until line {held['id']} still holds"
    problem = unclear_send(item, w)
    if problem:
        return "not-settled", problem
    for role in ("owner_session", "waiting_session"):
        sid = w.field(role)
        res = run_orca(["agent", "show", f"orca_session_id:{sid}", "--json"])
        places = res.result.get("places") if res.state == "ok" else None
        if not isinstance(places, list) or not places:
            who = "owner" if role == "owner_session" else "waiting"
            return "not-settled", f"the {who} session {sid} is not open in Orca ({res.describe()})"
    return None, None


def cmd_close(a: argparse.Namespace) -> tuple:
    n, k = int(need(RE_ITEM, a.item, "--item")), wait_number(a.wait)
    if a.trigger not in TRIGGER_CASES:
        raise Refused("--trigger is wake, notice or look")
    if a.case not in CASES:
        raise Refused("--case is no-follow-up, settled, re-sent or not-settled")
    if a.case not in TRIGGER_CASES[a.trigger]:
        raise Refused(f"a {a.trigger} closes only as " + ", ".join(TRIGGER_CASES[a.trigger]))
    text = read_head_file(a.text_file, n, k, "--text-file")
    require_sections(text, a.case, "--text-file")
    body = None
    if a.case == "re-sent":
        if not a.body_file:
            raise Refused("re-sent needs --body-file")
        body = read_head_file(a.body_file, n, k, "--body-file")
    elif a.body_file:
        raise Refused("--body-file goes only with re-sent")
    item, why = read_item(n, READ_TRIES)
    if item is None:
        return EXIT_UNCLEAR, f"UNREADABLE item {n} W{k}: {why}; nothing written"
    w = Wait(item, k)
    if not w.reserved:
        return EXIT_OTHER, f"REFUSED item {n} W{k}: no W{k} marker, so it can't be closed"
    if w.record is None:
        return EXIT_OTHER, f"REFUSED item {n} W{k}: no W{k} record; close it unarmed " \
                           "(reconciliation), not by a disposition"
    if utf16_len(close_header(n, k, a.case, a.trigger, w, False) + " " * 1400 + text) > TEXT_MAX:
        return EXIT_OTHER, f"REFUSED item {n} W{k}: --text-file is too long for one comment"
    if a.trigger != "wake" and a.case == "not-settled":
        wake = w.wake_id()
        if wake is None:
            return EXIT_OTHER, f"REFUSED item {n} W{k}: no Armed or Rewake line, so no wake to " \
                               "read; an arm cut off before Waiting is closed with close-unarmed"
        state = wake_state(wake)
        if state not in ("disabled", "gone"):
            return EXIT_OTHER, f"REFUSED item {n} W{k}: a {a.trigger} closes as not settled " \
                               f"only when the wait's wake is gone or disabled; it is {state}. " \
                               "Leave the wait to its wake."
    scratch = Scratch()
    try:
        return close_claimed(n, k, a, w, text, body, scratch)
    finally:
        scratch.close()


def close_claimed(n: int, k: int, a: argparse.Namespace, w: Wait, text: str, body: str | None,
                  scratch: Scratch) -> tuple:
    clock = Clock()
    word, res = link_marker(n, k, True)
    if word == "FULL":
        line = post_blocked(n, k, scratch)
        wake = w.wake_id()
        tail = retire(n, k, wake, scratch, clock) if wake else "no wake recorded"
        return EXIT_OTHER, f"FULL item {n} W{k}: W{k}-closed can't be linked, so nothing was " \
                           f"sent or closed; {line}; {tail}. Carry the work to a fresh item."
    if word != "CLAIMED":
        code = EXIT_UNCLEAR if word == "UNCLEAR" else EXIT_OTHER
        return code, f"{word} item {n} W{k}: " + (
            "another run closed it; nothing written" if word == "NOT CLAIMED" else
            res.describe() + "; nothing sent" + ("; reconcile" if word == "UNCLEAR" else ""))
    # This run won the claim: it alone may send for W<k> or post its closing record.
    case, extra, sent = a.case, [], None
    item, _ = read_item(n) if clock.ok() else (None, None)
    w2 = Wait(item, k) if item is not None else None
    if w2 is not None and w2.closing is not None:
        return EXIT_OTHER, f"STOPPED item {n} W{k}: claimed, but a closing record " \
                           f"{w2.closing['id']} is already there; nothing sent or posted"
    if case == "re-sent":
        new_case, why = fresh_send_check(n, k, item, w2) if clock.ok() else (
            "not-settled", "out of time before the send")
        if new_case == "stop":
            return EXIT_OTHER, f"STOPPED item {n} W{k}: claimed, but {why}; nothing sent or posted"
        if new_case is None:
            address = w.field("owner")
            line = f"Re-send, item {n} W{k}: to {address} at {iso_utc(now_s())}."
            note = posted(post(n, line, scratch, "resend.txt")) if clock.ok() else None
            if note is None:
                new_case, why = "not-settled", "the Re-send line did not post, so nothing was sent"
            elif not clock.ok():
                new_case, why = "not-settled", "out of time before the send"
            else:
                sent = send_once(n, k, w, body, scratch)
                if sent[0] != "sent":
                    new_case, why = "not-settled", "re-send unclear"
                extra.append(clip(sent[1], 600))
        if new_case is not None:
            extra.insert(0, f"Planned: re-sent; recorded as {CASES[new_case]}. Blocker: {why}.")
            case = new_case
    if not clock.ok():
        detail = " ".join(extra)
        return EXIT_UNCLEAR, f"UNCLEAR item {n} W{k}: claimed, but out of time before the " \
                             f"disposition ({CASES[case]}). {detail} Reconcile."
    header = close_header(n, k, case, a.trigger, w, False)
    if extra:
        header += " " + " ".join(extra)
    res = post(n, header + "\n" + text, scratch, "disposition.txt")
    note = posted(res)
    tail = ""
    if a.trigger != "wake" and case == "settled":
        wake = w.wake_id()
        tail = "; " + (retire(n, k, wake, scratch, clock) if wake else "no wake recorded to retire")
    if note is None:
        return EXIT_UNCLEAR, f"UNCLEAR item {n} W{k}: claimed, but the disposition " \
                             f"({CASES[case]}) did not post: {res.describe()}. " \
                             f"{' '.join(extra)} Reconcile{tail}"
    if a.case == "re-sent" and (case != "re-sent" or sent is None or sent[0] != "sent"):
        word = "SEND UNCLEAR" if sent is not None and sent[0] != "sent" else "NOT SENT"
        return (EXIT_UNCLEAR if word == "SEND UNCLEAR" else EXIT_OTHER), \
            f"{word} item {n} W{k}: claimed; {CASES[case]}, disposition {note}; " + \
            " ".join(extra) + tail
    if "UNVERIFIED item" in tail:
        return EXIT_UNCLEAR, f"RETIRE UNVERIFIED item {n} W{k}: claimed; {CASES[case]}, " \
                             f"disposition {note}" + tail
    return EXIT_OK, f"CLAIMED item {n} W{k}: {CASES[case]}, disposition {note}" + (
        "; " + " ".join(extra) if extra else "") + tail


def send_once(n: int, k: int, w: Wait, body: str, scratch: Scratch) -> tuple:
    """The one re-send for W<k>. Returns ("sent" | "unclear", the sentence for the disposition)."""
    address = w.field("owner")
    head = (f"Re-sent by the Head: item {n} W{k}. Key: {w.field('key')}. Ticket: "
            f"{w.field('ticket')}. Asked by session: {w.field('waiting_session')}.")
    path = scratch.file("body.txt", head + "\n\n" + body)
    res = run_orca(["orchestration", "send", "--to", address, "--type", "question", "--subject",
                    f"Re-sent by the Head: item {n} W{k}", "--body-file", path, "--json"])
    msg = res.result.get("messageId") if res.state == "ok" else None
    if isinstance(msg, str) and RE_MSG.fullmatch(msg):
        warnings = res.result.get("warnings")
        note = f" Warnings: {json.dumps(warnings)}." if warnings else ""
        return "sent", f"Sent: {msg} to {address}.{note}"
    request = res.error_data.get("orchestrationRequestId") if res.state == "error" else None
    if isinstance(request, str) and RE_UUID.fullmatch(request):
        shown = run_orca(["orchestration", "request-show", "--request", request, "--json"])
        state = json.dumps(shown.result)[:300] if shown.state == "ok" else shown.describe()
        return "unclear", f"Send unclear: {res.describe()}; request {request}; " \
                          f"request-show: {state}. Not sent again."
    return "unclear", f"Send unclear: {res.describe()}; no request id printed. Not sent again."


def cmd_retire(a: argparse.Namespace) -> tuple:
    n, k = int(need(RE_ITEM, a.item, "--item")), wait_number(a.wait)
    wake = need(RE_UUID, a.id, "--id")
    scratch = Scratch()
    try:
        line = retire(n, k, wake, scratch)
    finally:
        scratch.close()
    return (EXIT_UNCLEAR if line.startswith("UNVERIFIED") else EXIT_OK), line


def cmd_reconcile(a: argparse.Namespace) -> tuple:
    n, k = int(need(RE_ITEM, a.item, "--item")), wait_number(a.wait)
    final = a.final
    if final is not None and final not in ("no-follow-up", "settled", "not-settled", "unarmed"):
        raise Refused("--final is no-follow-up, settled, not-settled or unarmed (reconcile "
                      "never sends)")
    text = read_head_file(a.text_file, n, k, "--text-file")
    if final is not None:
        require_sections(text, "settled" if final == "unarmed" else final, "--text-file")
    item, why = read_item(n, READ_TRIES)
    if item is None:
        return EXIT_UNCLEAR, f"UNREADABLE item {n} W{k}: {why}; nothing written"
    w = Wait(item, k)
    if not w.closed or w.closed_ev is None:
        return EXIT_OTHER, f"REFUSED item {n} W{k}: W{k} is not closed; an open wait is closed " \
                           "by close or close-unarmed"
    if w.closing is not None:
        return EXIT_OTHER, f"REFUSED item {n} W{k}: it already has its closing record " \
                           f"{w.closing['id']}"
    if final == "unarmed" and w.armed is not None:
        return EXIT_OTHER, f"REFUSED item {n} W{k}: it has an Armed line {w.armed[0]['id']}, so " \
                           "it was armed; reconcile it with a disposition"
    if final not in (None, "unarmed") and w.record is None:
        return EXIT_OTHER, f"REFUSED item {n} W{k}: no W{k} record, so no disposition; use " \
                           "--final unarmed"
    actor = w.closed_ev.get("actor") if isinstance(w.closed_ev.get("actor"), dict) else {}
    chat = actor.get("chatId") if RE_UUID.fullmatch(str(actor.get("chatId", ""))) else "unknown"
    at = w.closed_ev.get("at")
    claimed_at = iso_utc(at / 1000) if isinstance(at, (int, float)) else "unknown"
    resend = w.resend["id"] if w.resend else "none"
    facts = f"Claimed by chat {chat} at {claimed_at}. Re-send line: {resend}."
    scratch = Scratch()
    try:
        if final is None:
            line = f"Reconcile note, item {n} W{k}: evidence only; this closes nothing. {facts}"
            res = post(n, line + "\n" + text, scratch, "note.txt")
            note = posted(res)
            if note is None:
                return EXIT_UNCLEAR, f"UNCLEAR item {n} W{k}: the note did not post: " \
                                     f"{res.describe()}"
            return EXIT_OK, f"NOTED item {n} W{k}: note {note}; W{k} still has no closing record"
        if not isinstance(at, (int, float)) or now_s() < at / 1000 + RECONCILE_AFTER_S:
            until = iso_utc(at / 1000 + RECONCILE_AFTER_S) if isinstance(at, (int, float)) \
                else "unknown"
            return EXIT_OTHER, f"REFUSED item {n} W{k}: the winner may still post until " \
                               f"{until}; post a reconcile note now, the disposition after"
        if final == "unarmed":
            header = f"UNARMED, item {n} W{k}: reconciled; wake none recorded. {facts}"
        else:
            header = close_header(n, k, final, "reconcile", w, True) + " " + facts
        res = post(n, header + "\n" + text, scratch, "disposition.txt")
        note = posted(res)
        if note is None:
            return EXIT_UNCLEAR, f"UNCLEAR item {n} W{k}: the reconciled closing record did not " \
                                 f"post: {res.describe()}"
        label = "unarmed" if final == "unarmed" else CASES[final]
        # Two reconciliations at once can each post: the first after W<k>-closed counts.
        again, why = read_item(n)
        first = Wait(again, k).closing if again is not None else None
        if first is None:
            return EXIT_UNCLEAR, f"UNCHECKED item {n} W{k}: {label}, closing record {note} " \
                                 f"posted, but the read after it failed ({why or 'not found'}), " \
                                 "so a second closing record isn't ruled out"
        if first["id"] != note:
            return EXIT_OTHER, f"DUPLICATE item {n} W{k}: closing record {note} landed after " \
                               f"{first['id']}, which counts; nothing more written"
        return EXIT_OK, f"RECONCILED item {n} W{k}: {label}, closing record {note}"
    finally:
        scratch.close()


def rewake_time() -> str:
    """REWAKE_AFTER_S from now, up to the next whole minute, in UTC."""
    t = math.ceil((now_s() + REWAKE_AFTER_S) / 60) * 60
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:00+00:00")


def cmd_rewake(a: argparse.Namespace) -> tuple:
    """A fresh one-time wake for a wait that has no closing record and no wake still due (its
    latest Armed or Rewake wake's time is ahead and Orca shows it enabled; a wake whose state
    can't be read counts as not due, so a spare can result, and a spare only runs check).
    It adds no link: only a `Rewake` line, and the wake's run starts with check like any wake."""
    n, k = int(need(RE_ITEM, a.item, "--item")), wait_number(a.wait)
    item, why = read_item(n, READ_TRIES)
    if item is None:
        return EXIT_UNCLEAR, f"UNCOVERED item {n} W{k}: the item can't be read ({why}); no wake " \
                             "made"
    w = Wait(item, k)
    if not w.reserved:
        return EXIT_OTHER, f"NO WAIT item {n} W{k}: no W{k} marker; no wake made"
    if item.status in ("done", "canceled"):
        return EXIT_OTHER, f"CLOSED item {n} W{k}: the item is {item.status}; no wake made"
    if w.closing is not None:
        return EXIT_OTHER, f"CLOSED item {n} W{k}: closing record {w.closing['id']}; no wake made"
    if w.blocked is not None:
        return EXIT_OTHER, f"BLOCKED item {n} W{k}: at Orca's link cap ({w.blocked['id']}); " \
                           "carry the work to a fresh item; no wake made"
    if w.record is None:
        return EXIT_OTHER, f"REFUSED item {n} W{k}: reserved with no record, so a wake can't " \
                           "close it; once the reserving chat ended its turn, close it with " \
                           "close-unarmed --step reservation-without-record; no wake made"
    cur = w.current_wake()
    if cur is not None and ms(cur[2]) > now_s() * 1000:
        state = wake_state(cur[1])
        if state == "enabled":
            return EXIT_OK, f"COVERED item {n} W{k}: wake {cur[1]} is due at {cur[2]}; no wake " \
                            "made"
    if len(w.rewakes) >= REWAKE_MAX:
        return EXIT_UNCLEAR, f"UNCOVERED item {n} W{k}: it has had {REWAKE_MAX} rewakes, the " \
                             "most it gets; no wake made. Reconcile it from your reads"
    target = rewake_time()
    scratch = Scratch()
    try:
        wake, err, unknown = step_create(n, k, item, target,
                                         f"Item {n} W{k} rewake {len(w.rewakes) + 1}")
        if err:
            tail = retire(n, k, wake, scratch) if wake else (
                "a wake may exist with an id Orca didn't print" if unknown else "no wake made")
            return EXIT_UNCLEAR, f"UNCOVERED item {n} W{k}: no fresh wake ({err}); {tail}"
        res = post(n, f"Rewake, item {n} W{k}: wake {wake}, target {target}.", scratch,
                   "rewake.txt")
        note = posted(res)
        if note is None:
            return EXIT_UNCLEAR, f"UNRECORDED item {n} W{k}: wake {wake} made for {target}, but " \
                                 f"the Rewake line did not post ({res.describe()}), so the item " \
                                 "may not name it"
        return EXIT_OK, f"REWOKEN item {n} W{k}: wake {wake}, target {target}; line {note}"
    finally:
        scratch.close()


def wake_state(wake: str) -> str:
    res = run_orca(["automations", "show", "--id", wake, "--json"])
    auto = res.result.get("automation") if res.state == "ok" else None
    if isinstance(auto, dict) and auto.get("id") == wake and isinstance(auto.get("enabled"), bool):
        return "enabled" if auto["enabled"] else "disabled"
    if res.state == "error" and res.message.strip() == "Automation not found.":
        return "gone"
    return "unreadable (" + res.describe() + ")"


def findings_for(item: Item) -> list:
    n, out = item.number, []
    seen = markers_on(item)
    now_ms = now_s() * 1000
    for k in sorted(seen):
        w = Wait(item, k)
        if not w.reserved:
            out.append(f"ITEM {n} W{k}: W{k}-closed is linked with no W{k} (a stray marker)")
            continue
        if w.blocked is not None:
            out.append(f"ITEM {n} W{k}: blocked at the link cap ({w.blocked['id']}); " + (
                f"carried ({w.carried['id']})" if w.carried else "not carried to a fresh item"))
            continue
        if w.reserved and not w.closed:
            if w.record is None:
                out.append(f"ITEM {n} W{k}: reserved with no record")
                continue
            if ms(w.field("deadline")) < now_ms:
                out.append(f"ITEM {n} W{k}: open past its deadline {w.field('deadline')}")
            wake = w.wake_id()
            state = wake_state(wake) if wake else "none recorded"
            if state != "enabled":
                out.append(f"ITEM {n} W{k}: open, and its wake is {state}")
        elif w.closed and w.closing is None:
            notes = f"; {len(w.notes)} reconcile note(s)" if w.notes else ""
            out.append(f"ITEM {n} W{k}: closed with no closing record{notes}")
    note = item.wait_text if item.status == "waiting" and isinstance(item.wait_text, str) else ""
    m = re.match(r"W([1-9][0-9]{0,3}) wake ([0-9a-f]{8})", note)
    if m:
        k, prefix = int(m.group(1)), m.group(2)
        w = Wait(item, k)
        later = [j for j in seen if j > k and seen[j][0]]
        if w.closed:
            out.append(f"ITEM {n}: Waiting names W{k}, which is closed (a spent wake)" + (
                f", superseded by W{max(later)}" if later else ""))
        elif not w.reserved:
            out.append(f"ITEM {n}: Waiting names W{k}, which has no marker")
        elif w.armed is not None and not w.armed[1].startswith(prefix):
            out.append(f"ITEM {n}: Waiting names wake {prefix}, not W{k}'s armed wake "
                       f"{w.armed[1][:8]} (a superseded wake)")
        elif later:
            out.append(f"ITEM {n}: Waiting names W{k}, superseded by W{max(later)}")
    free = LINK_CAP - len(item.links)
    if free <= LINKS_PER_WAIT and (seen or m):
        out.append(f"ITEM {n}: {free} free link slot(s) of Orca's {LINK_CAP}")
    return out


def cmd_restart(a: argparse.Namespace) -> tuple:
    bot = need(RE_BOT, a.bot, "--bot")
    numbers, cursor = [], None
    for _ in range(SHOW_PAGES_MAX):
        args = ["bot", "item", "list", "--bot", bot, "--status",
                "planned,in-progress,waiting,needs-you", "--limit", "100"]
        res = run_orca(args + (["--cursor", cursor] if cursor else []) + ["--json"])
        items = res.result.get("items") if res.state == "ok" else None
        if not isinstance(items, list):
            return EXIT_UNCLEAR, f"UNREADABLE restart: bot item list: {res.describe()}"
        numbers += [i.get("number") for i in items if isinstance(i, dict)
                    and isinstance(i.get("number"), int)]
        nxt = res.result.get("nextCursor")
        if not nxt:
            break
        if not isinstance(nxt, str) or not re.fullmatch(r"\d+:\d+", nxt) or nxt == cursor:
            return EXIT_UNCLEAR, "UNREADABLE restart: bot item list printed a bad cursor"
        cursor = nxt
    lines, unreadable = [], []
    for n in numbers:
        item, why = read_item(n)
        if item is None:
            unreadable.append(f"ITEM {n}: unreadable: {why}")
            continue
        lines += findings_for(item)
    lines += unreadable
    first = (f"INCOMPLETE RESTART {len(lines)} finding(s) on {len(numbers)} open item(s), "
             f"{len(unreadable)} unreadable" if unreadable else
             f"RESTART {len(lines)} finding(s) on {len(numbers)} open item(s)")
    return (EXIT_UNCLEAR if unreadable else EXIT_OK), "\n".join([first] + lines)


# ------------------------------------------------------------------------------ main


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="head_wait.py", description="Head's wake for a waiting item",
                                allow_abbrev=False)
    p.add_argument("--version", action="version", version=f"head_wait.py dv {VERSION}")
    sub = p.add_subparsers(dest="command", required=True)

    def cmd(name: str, *flags: str, optional: tuple = ()) -> argparse.ArgumentParser:
        s = sub.add_parser(name, allow_abbrev=False)
        for f in flags:
            s.add_argument("--" + f, required=True, dest=f.replace("-", "_"))
        for f in optional:
            s.add_argument("--" + f, dest=f.replace("-", "_"))
        return s

    arm_flags = ("item", "wait", "target", "deadline", "owner", "owner-session",
                 "waiting-session", "ticket", "key", "record-file")
    cmd("arm", *arm_flags).add_argument("--carried-from", dest="carried")
    cmd("check", "item", optional=("wait",))
    cmd("close", "item", "wait", "trigger", "case", "text-file", optional=("body-file",))
    cmd("retire", "item", "wait", "id")
    cmd("reconcile", "item", "wait", "text-file", optional=("final",))
    cmd("rewake", "item", "wait")
    cmd("restart", "bot")
    cmd("reserve", "item", "wait")
    cmd("claim", "item", "wait")
    cmd("close-unarmed", "item", "wait", "step", optional=("wake-id",))
    return p


COMMANDS = {"arm": cmd_arm, "check": cmd_check, "close": cmd_close, "retire": cmd_retire,
            "reconcile": cmd_reconcile, "rewake": cmd_rewake, "restart": cmd_restart,
            "reserve": cmd_reserve, "claim": cmd_claim, "close-unarmed": cmd_close_unarmed}


def main(argv: list | None = None) -> int:
    a = parser().parse_args(argv)
    BUDGET["start"] = mono()
    try:
        code, line = COMMANDS[a.command](a)
    except Refused as e:
        say(f"REFUSED: {e}; nothing sent to Orca")
        return EXIT_USAGE
    except (ValueError, OSError, KeyError, TypeError) as e:
        say(f"UNCLEAR: {a.command} stopped on {type(e).__name__}: {e}; run rewake for the wait, "
            "then restart")
        return EXIT_UNCLEAR
    finally:
        BUDGET["start"] = None
    say(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
