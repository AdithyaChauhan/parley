"""The seven Kubernetes demos (T32): what Kubernetes adds, measured from outside.

From the repo root, with the cluster up and the backend's venv:
    backend/.venv/Scripts/python deploy/k8s/demo.py 1 2 3 4 5 6 7
Results are in docs/kubernetes.md.

It acts like the real app, through the front door: HTTP to send, one live line
per tab, a ping every 25 s, reconnect with backoff (D21), and catch-up by message
number. Sends retry with the same client_msg_id (D18). Five test users with 4 tabs
each stay within D24's limits: 10 tickets a minute leaves room for a tab to reconnect.
Demo 1 needs only the front door, so CI runs it too. The others also use kubectl.
"""

import asyncio
import json
import os
import random
import shutil
import statistics
import subprocess
import sys
import time
import uuid
from collections import Counter

import httpx2
import websockets
from websockets.asyncio.client import connect

# 127.0.0.1, not localhost: on Windows, localhost costs about 1 s per try (D22).
BASE = os.environ.get("PARLEY_URL", "http://127.0.0.1:8090")
LIVE = BASE.replace("http", "ws", 1) + "/api/live"
NODE = "parley-control-plane"
KUBECTL = ["kubectl", "--context", "kind-parley", "-n", "parley"]
PASSWORD = "demo-password-only-for-the-local-cluster"


def now() -> float:
    return time.monotonic()


def say(text: str) -> None:
    print(text, flush=True)


def seconds(values: list[float]) -> str:
    if not values:
        return "none"
    return f"median {statistics.median(values):.1f} s, slowest {max(values):.1f} s (n={len(values)})"


class Failed(Exception):
    pass


def check(ok: bool, what: str) -> None:
    say(f"  {'PASS' if ok else 'FAIL'}: {what}")
    if not ok:
        raise Failed(what)


async def until(condition, timeout: float, step: float = 0.1) -> bool:
    end = now() + timeout
    while now() < end:
        if condition():
            return True
        await asyncio.sleep(step)
    return condition()


# ---- kubectl ----


def run(args: list[str]) -> str:
    # A few tries: while images load, this laptop's API server can answer slowly.
    for attempt in range(4):
        try:
            done = subprocess.run(args, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            continue
        if done.returncode == 0:
            return done.stdout
        if "Unable to connect" not in done.stderr and "timed out" not in done.stderr:
            break
        time.sleep(3)
    raise Failed(f"{' '.join(args)}: {done.stderr.strip()}")


async def kubectl(*args: str) -> str:
    return await asyncio.to_thread(run, KUBECTL + list(args))


async def pods(app: str) -> list[dict]:
    """Name, ready and restarts of each pod of one app, old ones included."""
    raw = json.loads(await kubectl("get", "pods", "-l", f"app={app}", "-o", "json"))
    found = []
    for pod in raw["items"]:
        statuses = pod["status"].get("containerStatuses") or [{}]
        found.append(
            {
                "name": pod["metadata"]["name"],
                "uid": pod["metadata"]["uid"],
                "stopping": "deletionTimestamp" in pod["metadata"],
                "ready": bool(statuses[0].get("ready")),
                "restarts": statuses[0].get("restartCount", 0),
                "container": (statuses[0].get("containerID") or "").removeprefix("containerd://"),
            }
        )
    return found


async def live_lines_on(pod: str) -> int:
    """What the pod itself says, from its /metrics page, to check the apps' count."""
    code = "import urllib.request as u; print(u.urlopen('http://127.0.0.1:8000/metrics', timeout=5).read().decode())"
    page = await kubectl("exec", pod, "--", "python", "-c", code)
    for line in page.splitlines():
        if line.startswith("live_lines_open "):
            return int(float(line.split()[1]))
    raise Failed(f"{pod} has no live_lines_open")


# ---- One user, and their tabs ----


class Person:
    def __init__(self, name: str):
        self.name = name
        self.email = f"{name.lower()}@demo.example.com"
        self.http = httpx2.AsyncClient(base_url=BASE, timeout=70)
        self.token = ""
        self.id = ""
        self.lines: list[Line] = []
        # chat id -> how each client_msg_id reached this person.
        self.got: dict[str, dict[str, str]] = {}
        self.highest: dict[str, int] = {}
        self.tickets: list[tuple[int, int]] = []

    async def enter(self) -> None:
        """Log in, or sign up the first time. Sign-ups are limited to 5 an hour (D24)."""
        body = {"email": self.email, "password": PASSWORD}
        reply = await self.http.post("/api/auth/login", json=body)
        if reply.status_code == 401:
            reply = await self.http.post("/api/auth/signup", json={**body, "name": self.name})
        reply.raise_for_status()
        self.token = reply.json()["access_token"]
        me = await self.api("GET", "/api/auth/me")
        self.id = me.json()["id"]

    async def api(self, method: str, path: str, **kwargs) -> httpx2.Response:
        """Like the app: an expired pass (401) means refresh once, then ask again."""
        reply = await self._ask(method, path, **kwargs)
        if reply.status_code == 401:
            refresh = await self.http.post("/api/auth/refresh")
            refresh.raise_for_status()
            self.token = refresh.json()["access_token"]
            reply = await self._ask(method, path, **kwargs)
        return reply

    def _ask(self, method: str, path: str, **kwargs):
        return self.http.request(method, path, headers={"Authorization": f"Bearer {self.token}"}, **kwargs)

    async def chat_with(self, other: "Person") -> str:
        reply = await self.api("POST", "/api/chats/direct", json={"email": other.email})
        reply.raise_for_status()
        return reply.json()["id"]

    def tabs(self, count: int, auto_read: bool = True) -> None:
        for _ in range(count):
            self.lines.append(Line(self, auto_read))

    async def close_tabs(self) -> None:
        for line in self.lines:
            line.task.cancel()
        await asyncio.gather(*(line.task for line in self.lines), return_exceptions=True)
        self.lines.clear()

    def received(self, chat_id: str, seq: int, cmid: str, how: str) -> None:
        self.got.setdefault(chat_id, {}).setdefault(cmid, how)
        self.highest[chat_id] = max(self.highest.get(chat_id, 0), seq)

    async def catch_up(self, chat_id: str) -> list[dict]:
        """Everything after what I have, by number, never by time (D21)."""
        found = []
        while True:
            after = self.highest.get(chat_id, 0)
            reply = await self.api("GET", f"/api/chats/{chat_id}/messages", params={"after": after, "limit": 100})
            if reply.status_code != 200:
                return found
            page = reply.json()
            for message in page["messages"]:
                self.received(chat_id, message["seq"], message["client_msg_id"], "catch-up")
                found.append(message)
            if not page["has_more"]:
                return found


class Line:
    """One browser tab's live line. It stays up by itself, like frontend/src/lib/live.ts."""

    def __init__(self, person: Person, auto_read: bool):
        self.person = person
        self.auto_read = auto_read
        self.copy: str | None = None  # the pod that said hello on the current line
        self.up = False
        self.ever_up = False
        self.dropped_at: float | None = None
        self.moves: list[dict] = []  # one per drop: how long it took, and from where to where
        self.close_codes: list[int | None] = []
        self.events: list[dict] = []
        self.socket = None
        self.last_error = ""
        self.task = asyncio.create_task(self._stay_up())

    async def _stay_up(self) -> None:
        failures = 0
        while True:
            try:
                await self._one_connection()
                failures = 0
            except asyncio.CancelledError:
                raise
            except Exception as error:  # a refused ticket, a dead pod, a timeout: all mean "try again"
                self.last_error = repr(error)
            if self.up:
                self.up = False
                self.dropped_at = now()
                failures = 0
            # 1, 2, 4 ... up to 30 s, plus a little random extra (D21).
            await asyncio.sleep(min(2**failures, 30) + random.random())
            failures += 1

    async def _one_connection(self) -> None:
        reply = await self.person.api("POST", "/api/live/ticket")
        self.person.tickets.append((round(now()), reply.status_code))
        if reply.status_code != 200:
            raise ConnectionError(f"ticket {reply.status_code}")
        async with connect(f"{LIVE}?ticket={reply.json()['ticket']}", ping_interval=None, open_timeout=10) as socket:
            self.socket = socket
            hello = json.loads(await asyncio.wait_for(socket.recv(), 10))
            if hello["type"] != "hello":
                raise ConnectionError(f"expected hello, got {hello['type']}")
            old_copy, self.copy, self.up, self.ever_up = self.copy, hello["data"]["copy"], True, True
            if self.dropped_at is not None:
                self.moves.append({"took": now() - self.dropped_at, "from": old_copy, "to": self.copy})
                self.dropped_at = None
                for chat_id in list(self.person.got):
                    await self.person.catch_up(chat_id)
            pinger = asyncio.create_task(self._ping(socket))
            try:
                async for raw in socket:
                    await self._on_event(socket, json.loads(raw))
            except websockets.ConnectionClosed:
                pass
            finally:
                pinger.cancel()
                self.close_codes.append(socket.close_code)

    async def _ping(self, socket) -> None:
        """Every 25 s; no pong within 10 s means the line is dead (D21)."""
        while True:
            await asyncio.sleep(25)
            self.pongs_before = sum(event["type"] == "pong" for event in self.events)
            await socket.send(json.dumps({"type": "ping"}))
            await asyncio.sleep(10)
            if sum(event["type"] == "pong" for event in self.events) == self.pongs_before:
                await socket.close(code=4000)
                return

    async def _on_event(self, socket, event: dict) -> None:
        self.events.append({**event, "at": now()})
        if event["type"] != "message.new":
            return
        message = event["data"]
        chat_id, seq = message["chat_id"], message["seq"]
        self.person.received(chat_id, seq, message["client_msg_id"], "live")
        # A browser with the chat open says so, so the ticks move.
        if self.auto_read and message["sender_id"] != self.person.id:
            await socket.send(json.dumps({"type": "read", "data": {"chat_id": chat_id, "seq": seq}}))


# ---- A steady chat, and the "was anything lost?" check ----


# What's running, so a demo that fails can't leak traffic into the next one.
_running: list = []


class Traffic:
    """Each person sends to their partner, one message at a time, in order (D21)."""

    def __init__(self, pairs: list[tuple[Person, Person, str]], rate_each: float):
        _running.append(self)
        self.pairs = pairs
        self.rate_each = rate_each
        self.sent: list[dict] = []
        self.retries: Counter = Counter()
        self.running = True
        self.tasks = [asyncio.create_task(self._sender(a, b, chat)) for a, b, chat in pairs]

    async def _sender(self, me: Person, partner: Person, chat_id: str) -> None:
        while self.running:
            await asyncio.sleep(1 / self.rate_each)
            await self._send_one(me, partner, chat_id)

    async def _send_one(self, me: Person, partner: Person, chat_id: str) -> None:
        cmid = str(uuid.uuid4())
        body = {"client_msg_id": cmid, "body": f"demo {cmid[:8]}"}
        started = now()
        while True:
            try:
                reply = await me.api("POST", f"/api/chats/{chat_id}/messages", json=body)
                if reply.status_code in (200, 201):
                    self.sent.append(
                        {"chat": chat_id, "cmid": cmid, "to": partner, "seq": reply.json()["seq"], "took": now() - started}
                    )
                    me.received(chat_id, reply.json()["seq"], cmid, "mine")
                    return
                self.retries[str(reply.status_code)] += 1
                await asyncio.sleep(float(reply.headers.get("Retry-After", 1)))
            except httpx2.HTTPError as error:
                self.retries[type(error).__name__] += 1
                await asyncio.sleep(1)

    async def finish(self) -> None:
        self.running = False
        await asyncio.gather(*self.tasks)

    def stop(self) -> None:
        self.running = False
        for task in self.tasks:
            task.cancel()

    async def report_losses(self) -> None:
        """Every accepted message must be saved exactly once, and reach its partner."""
        saved_by_chat = {}
        for _, partner, chat_id in self.pairs:
            await partner.catch_up(chat_id)
            if chat_id not in saved_by_chat:
                saved_by_chat[chat_id] = await all_saved(partner, chat_id)
        wanted_ids = Counter(item["cmid"] for item in self.sent)
        saved_ids = Counter(m["client_msg_id"] for page in saved_by_chat.values() for m in page)
        lost = [cmid for cmid in wanted_ids if saved_ids[cmid] == 0]
        doubled = [cmid for cmid in wanted_ids if saved_ids[cmid] > 1]
        holes = 0
        for page in saved_by_chat.values():
            numbers = sorted(m["seq"] for m in page)
            holes += len(numbers) and numbers[-1] - numbers[0] + 1 - len(numbers)
        how = Counter(item["to"].got.get(item["chat"], {}).get(item["cmid"], "never") for item in self.sent)
        slowest = max((item["took"] for item in self.sent), default=0)
        say(f"  {len(self.sent)} sent. Reached the partner: {dict(how)}. Sends that had to retry: {dict(self.retries)}.")
        say(f"  Slowest send, retries included: {slowest:.1f} s.")
        check(not lost and not doubled and not holes, f"{len(lost)} lost, {len(doubled)} doubled, {holes} holes in the numbers")
        check(how["never"] == 0, "every message reached its partner, live or by catch-up")


async def all_saved(person: Person, chat_id: str) -> list[dict]:
    messages, after = [], 0
    while True:
        reply = await person.api("GET", f"/api/chats/{chat_id}/messages", params={"after": after, "limit": 100})
        reply.raise_for_status()
        page = reply.json()
        messages += page["messages"]
        if not page["has_more"]:
            return messages
        after = page["messages"][-1]["seq"]


# One log-in per run: logging in 5 users for each demo would hit D24's 30 per 15 min.
_ring: tuple[list[Person], list[tuple[Person, Person, str]]] | None = None


async def people_in_pairs() -> tuple[list[Person], list[tuple[Person, Person, str]]]:
    """Five users in a ring: Ana -> Ben -> Cleo -> Dev -> Esi -> Ana."""
    global _ring
    if _ring is not None:
        return _ring
    people = [Person(name) for name in ("Ana", "Ben", "Cleo", "Dev", "Esi")]
    for person in people:
        await person.enter()
    pairs = []
    for index, person in enumerate(people):
        partner = people[(index + 1) % len(people)]
        pairs.append((person, partner, await person.chat_with(partner)))
    for person, partner, chat_id in pairs:
        # Start from what's already there, so old messages don't count as new.
        for who in (person, partner):
            who.got.setdefault(chat_id, {})
            who.highest.setdefault(chat_id, 0)
            await who.catch_up(chat_id)
    _ring = people, pairs
    return _ring


async def open_tabs(people: list[Person], each: int, auto_read: bool = True) -> list["Line"]:
    for person in people:
        person.tabs(each, auto_read)
    lines = [line for person in people for line in person.lines]
    if not await until(lambda: all(line.up for line in lines), 40):
        errors = Counter(line.last_error for line in lines if not line.up)
        raise Failed(f"only {sum(line.up for line in lines)} of {len(lines)} lines came up: {dict(errors)}")
    return lines


async def close_tabs(people: list[Person]) -> None:
    for person in people:
        await person.close_tabs()


def spread(lines: list[Line]) -> Counter:
    return Counter(line.copy for line in lines if line.up)


async def wait_ready(app: str, count: int, timeout: float) -> bool:
    end = now() + timeout
    while now() < end:
        current = await pods(app)
        if sum(pod["ready"] and not pod["stopping"] for pod in current) >= count:
            return True
        await asyncio.sleep(1)
    return False


async def health() -> tuple[int, dict]:
    async with httpx2.AsyncClient(timeout=70) as client:
        reply = await client.get(f"{BASE}/api/health")
        return reply.status_code, reply.json() if reply.status_code == 200 else {}


class HealthWatch:
    """Asks /api/health through the front door all the time, like a stream of users."""

    def __init__(self, every: float = 0.25):
        _running.append(self)
        self.answers: list[tuple[float, int, str, str]] = []
        self.failures: list[str] = []
        self.started = now()
        self.every = every
        self.task = asyncio.create_task(self._watch())

    async def _watch(self) -> None:
        async with httpx2.AsyncClient(timeout=10) as client:
            while True:
                asked = now()
                try:
                    reply = await client.get(f"{BASE}/api/health")
                    data = reply.json() if reply.status_code == 200 else {}
                    self.answers.append((now(), reply.status_code, data.get("version", ""), data.get("copy", "")))
                except (httpx2.HTTPError, ValueError) as error:
                    self.failures.append(f"{now() - self.started:.0f} s: {type(error).__name__} after {now() - asked:.1f} s")
                    self.answers.append((now(), 0, "", ""))
                await asyncio.sleep(self.every)

    def stop(self) -> None:
        self.task.cancel()

    def bad(self) -> Counter:
        return Counter(status for _, status, _, _ in self.answers if status != 200)

    def slowest_gap(self) -> float:
        """The longest time with no answer, as a user would feel it."""
        times = [answer[0] for answer in self.answers]
        return max((b - a for a, b in zip(times, times[1:])), default=0)


# ---- The demos ----


async def demo_1() -> None:
    say("\n== Demo 1: two users chat through the front door")
    ana, ben = Person("Ana"), Person("Ben")
    await ana.enter()
    await ben.enter()
    chat_id = await ana.chat_with(ben)
    await ben.chat_with(ana)
    await ana.catch_up(chat_id)
    await ben.catch_up(chat_id)

    await open_tabs([ana], 1, auto_read=False)
    ana_line = ana.lines[0]
    await open_tabs([ben], 1, auto_read=False)
    ben_line = ben.lines[0]
    say(f"  Ana's line is on {ana_line.copy}, Ben's on {ben_line.copy}.")

    def news(line: Line, kind: str, test) -> bool:
        return any(event["type"] == kind and test(event["data"]) for event in line.events)

    check(await until(lambda: news(ana_line, "presence", lambda d: d["user_id"] == ben.id and d["online"]), 5), "online: Ana hears that Ben came online")

    cmid = str(uuid.uuid4())
    started = now()
    reply = await ana.api("POST", f"/api/chats/{chat_id}/messages", json={"client_msg_id": cmid, "body": "Hello from Kubernetes"})
    check(reply.status_code == 201, "send: Ana's message is saved (201)")
    seq = reply.json()["seq"]
    arrived = await until(lambda: news(ben_line, "message.new", lambda d: d["client_msg_id"] == cmid), 5, 0.01)
    check(arrived, f"live push: Ben gets it in {(now() - started) * 1000:.0f} ms")

    await ben_line.socket.send(json.dumps({"type": "delivered", "data": {"chat_id": chat_id, "seq": seq}}))
    check(await until(lambda: news(ana_line, "receipt", lambda d: d["user_id"] == ben.id and d["delivered_up_to"] >= seq), 5), "two grey ticks: Ana hears 'delivered'")
    await ben_line.socket.send(json.dumps({"type": "read", "data": {"chat_id": chat_id, "seq": seq}}))
    check(await until(lambda: news(ana_line, "receipt", lambda d: d["user_id"] == ben.id and d["read_up_to"] >= seq), 5), "two teal ticks: Ana hears 'read'")

    await ben_line.socket.send(json.dumps({"type": "typing", "data": {"chat_id": chat_id}}))
    check(await until(lambda: news(ana_line, "typing", lambda d: d["user_id"] == ben.id), 5), "typing: Ana sees Ben typing")

    await ben.close_tabs()
    check(await until(lambda: news(ana_line, "presence", lambda d: d["user_id"] == ben.id and not d["online"]), 8), "offline: Ana hears that Ben left")
    await ana.close_tabs()
    status, data = await health()
    check(status == 200 and data.get("status") == "ok", f"health through the front door: {data}")


async def demo_2() -> None:
    say("\n== Demo 2: at least 20 live lines split over both backend pods")
    people, _ = await people_in_pairs()
    lines = await open_tabs(people, 4)
    split = spread(lines)
    say(f"  {len(lines)} lines from {len(people)} users: {dict(split)}")
    for name in split:
        say(f"  {name} itself says it has {await live_lines_on(name)} live lines open.")
    check(len(lines) >= 20, f"{len(lines)} lines open")
    check(len(split) == 2 and max(split.values()) - min(split.values()) <= 2, "split evenly over both pods (within 2)")
    await close_tabs(people)


async def demo_3() -> None:
    say("\n== Demo 3: delete a backend pod mid-chat")
    people, pairs = await people_in_pairs()
    lines = await open_tabs(people, 5)
    traffic = Traffic(pairs, 0.5)
    watch = HealthWatch()
    await asyncio.sleep(8)
    split = spread(lines)
    victim = split.most_common(1)[0][0]
    say(f"  Before: {dict(split)}. Deleting {victim}, with {split[victim]} lines on it.")
    deleted_at = now()
    await kubectl("delete", "pod", victim, "--wait=false")

    on_victim = [line for line in lines if line.copy == victim]
    moved = await until(lambda: all(line.up and line.copy != victim for line in on_victim), 60)
    moved_after = now() - deleted_at
    for line in on_victim:
        if not line.up or line.copy == victim:
            say(f"  Still not moved: {line.person.name}, up={line.up}, on {line.copy}, last error {line.last_error}, codes {line.close_codes}, tickets {line.person.tickets}")
    check(moved, f"all {len(on_victim)} lines moved to the other pod, the last {moved_after:.1f} s after the delete")
    say(f"  Each line, closed to back on: {seconds([m['took'] for line in on_victim for m in line.moves])}.")
    say(f"  Close codes seen: {dict(Counter(code for line in on_victim for code in line.close_codes))} (1012 = server restarting, D28).")

    check(await wait_ready("backend", 2, 120), f"a new pod is ready, {now() - deleted_at:.1f} s after the delete")
    current = [pod["name"] for pod in await pods("backend") if not pod["stopping"]]
    check(victim not in current, f"it's a new pod: {current}")
    before = spread(lines)
    say(f"  After: {dict(before)}. New tabs should go to whichever pod has fewer lines.")
    # Past the ticket limit's minute (D24): these tabs just reconnected.
    await asyncio.sleep(60)
    for person in people:
        person.tabs(1)
    newer = [person.lines[-1] for person in people]
    await until(lambda: all(line.up for line in newer), 30)
    after = spread(lines + newer)
    say(f"  5 new tabs went to: {dict(spread(newer))}. Now: {dict(after)}.")
    gap = lambda counts: abs(counts[current[0]] - counts[current[1]])
    check(gap(after) <= max(2, gap(before) - 5), "they evened the pods out (least_conn)")
    watch.stop()
    await traffic.finish()
    await asyncio.sleep(1)
    say(f"  Health through the front door: {len(watch.answers)} asks. Not 200: {dict(watch.bad())}. Longest gap between answers: {watch.slowest_gap():.1f} s.")
    check(not watch.bad(), "no failed asks")
    await traffic.report_losses()
    await close_tabs(people)


async def freeze(pod: dict) -> int:
    """SIGSTOP the pod's main process from the kind node: it's alive, but stuck."""
    raw = await asyncio.to_thread(run, ["docker", "exec", NODE, "crictl", "inspect", pod["container"]])
    pid = json.loads(raw)["info"]["pid"]
    await asyncio.to_thread(run, ["docker", "exec", NODE, "kill", "-STOP", str(pid)])
    state = await asyncio.to_thread(run, ["docker", "exec", NODE, "sh", "-c", f"grep State /proc/{pid}/status"])
    say(f"  Froze process {pid} in {pod['name']}: {state.strip()}.")
    return pid


async def demo_4() -> None:
    say("\n== Demo 4: a stuck copy restarts by itself")
    people, pairs = await people_in_pairs()
    lines = await open_tabs(people, 4)
    traffic = Traffic(pairs, 0.5)
    watch = HealthWatch()
    await asyncio.sleep(5)
    split = spread(lines)
    current = [pod for pod in await pods("backend") if not pod["stopping"]]
    frozen = max(current, key=lambda pod: split[pod["name"]])
    other = next(pod for pod in current if pod["name"] != frozen["name"])
    say(f"  Before: {dict(split)}.")
    on_frozen = [line for line in lines if line.copy == frozen["name"]]

    frozen_at = now()
    await freeze(frozen)

    marks: dict[str, float] = {}
    while now() - frozen_at < 120:
        state = {pod["name"]: pod for pod in await pods("backend")}
        pod = state.get(frozen["name"])
        elapsed = now() - frozen_at
        if pod and not pod["ready"] and "not ready" not in marks:
            marks["not ready"] = elapsed
            say(f"  {elapsed:5.1f} s: readiness failed. Kubernetes stops listing the pod, so Nginx stops using it.")
        if pod and pod["restarts"] > frozen["restarts"] and "restarted" not in marks:
            marks["restarted"] = elapsed
            say(f"  {elapsed:5.1f} s: liveness failed, and Kubernetes restarted the container.")
        if "lines moved" not in marks and all(line.up and line.moves for line in on_frozen):
            marks["lines moved"] = elapsed
            say(f"  {elapsed:5.1f} s: all {len(on_frozen)} of its lines are up again.")
        if "restarted" in marks and pod and pod["ready"] and "ready again" not in marks:
            marks["ready again"] = elapsed
            say(f"  {elapsed:5.1f} s: the restarted container passed its probes.")
        if len(marks) == 4:
            break
        await asyncio.sleep(0.5)
    check(len(marks) == 4, f"all four steps happened: {sorted(marks)}")
    state = {pod["name"]: pod for pod in await pods("backend")}
    check(state[other["name"]]["restarts"] == other["restarts"], "the healthy pod wasn't touched")
    say(f"  Each line, closed to back on: {seconds([m['took'] for line in on_frozen for m in line.moves])}.")
    say(f"  Close codes seen: {dict(Counter(code for line in on_frozen for code in line.close_codes))}.")
    await asyncio.sleep(5)
    watch.stop()
    await traffic.finish()
    await asyncio.sleep(1)
    say(f"  Health through the front door: {len(watch.answers)} asks. Not 200: {dict(watch.bad())} (0 = timed out at 10 s).")
    await traffic.report_losses()
    await close_tabs(people)


async def demo_5() -> None:
    say("\n== Demo 5: a rolling update under light load (~5 messages/s)")
    people, pairs = await people_in_pairs()
    lines = await open_tabs(people, 2)
    status, before = await health()
    new_tag = f"demo5-{int(time.time())}"
    say(f"  Running version: {before['version']}. Rolling out {new_tag}.")
    traffic = Traffic(pairs, 1.0)
    watch = HealthWatch()
    await asyncio.sleep(5)

    lowest_ready = 2
    roll = asyncio.create_task(asyncio.to_thread(roll_out, new_tag))
    started = now()
    seen_pods: set[str] = set()
    last_state = ""
    roll_began = 0.0
    while not roll.done():
        current = await pods("backend")
        seen_pods |= {pod["name"] for pod in current}
        # The roll itself starts when a third pod appears. Before that, up.sh is
        # building and loading images, and only the laptop's stalls show here.
        if len(seen_pods) > 2:
            roll_began = roll_began or now()
            lowest_ready = min(lowest_ready, sum(pod["ready"] and not pod["stopping"] for pod in current))
        state = ", ".join(sorted(f"{pod['name'][-5:]}:{'stopping' if pod['stopping'] else 'ready' if pod['ready'] else 'starting'}" for pod in current))
        if state != last_state:
            say(f"  {now() - started:5.0f} s: {state}")
            last_state = state
        await asyncio.sleep(2)
    say(f"  up.sh steps: {await roll}")
    say(f"  up.sh took {now() - started:.0f} s. Pods seen: {len(seen_pods)}.")
    check(lowest_ready >= 2, f"one pod at a time: during the roll, never fewer than {lowest_ready} ready and not stopping")
    await asyncio.sleep(5)
    watch.stop()
    await traffic.finish()
    await asyncio.sleep(1)
    during_roll = Counter(status for at, status, _, _ in watch.answers if status != 200 and at >= roll_began)
    before_roll = Counter(status for at, status, _, _ in watch.answers if status != 200 and at < roll_began)
    say(f"  Health through the front door: {len(watch.answers)} asks. Not 200, while images were building and loading: {dict(before_roll)}. During the roll: {dict(during_roll)}.")
    say(f"  The failed asks, by time since the watch began: {watch.failures}")
    check(not during_roll, "no gap: every health ask answered 200 during the roll")
    await traffic.report_losses()

    versions = Counter()
    copies = Counter()
    for _ in range(20):
        _, data = await health()
        versions[data.get("version")] += 1
        copies[data.get("copy")] += 1
    say(f"  20 asks afterwards: versions {dict(versions)}, copies {dict(copies)}.")
    check(set(versions) == {new_tag}, f"every answer shows the new version {new_tag}")
    await until(lambda: all(line.up for line in lines), 40)
    say(f"  Lines are back on the new pods: {dict(spread(lines))}, {sum(len(line.moves) for line in lines)} moves in all.")
    running = {pod["name"] for pod in await pods("backend") if not pod["stopping"]}
    check(all(line.copy in running for line in lines), f"all lines are on the new pods: {sorted(running)}")
    await close_tabs(people)


def roll_out(tag: str) -> str:
    bash = shutil.which("bash")
    done = subprocess.run(
        [bash, "deploy/k8s/up.sh"], env={**os.environ, "PARLEY_TAG": tag}, capture_output=True, text=True, timeout=540
    )
    if done.returncode != 0:
        raise Failed(f"up.sh failed: {done.stdout[-800:]} {done.stderr[-800:]}")
    return "; ".join(line[3:] for line in done.stdout.splitlines() if line.startswith("== "))


async def demo_6() -> None:
    say("\n== Demo 6: Redis is stopped for a minute")
    people, pairs = await people_in_pairs()
    lines = await open_tabs(people, 3)
    traffic = Traffic(pairs, 0.4)
    watch = HealthWatch(0.5)
    await asyncio.sleep(5)
    say(f"  Before: {dict(spread(lines))}.")
    backend_before = {pod["name"]: pod["restarts"] for pod in await pods("backend")}
    worker_before = {pod["name"]: pod["restarts"] for pod in await pods("worker")}
    sent_before = len(traffic.sent)

    await kubectl("scale", "statefulset/redis", "--replicas=0")
    # The minute starts only once Redis is really gone.
    asked_at = now()
    while await pods("redis"):
        if now() - asked_at > 90:
            raise Failed("Redis didn't stop")
        await asyncio.sleep(1)
    say(f"  Redis is gone, {now() - asked_at:.1f} s after asking.")
    stopped_at = now()
    lowest_ready = 2
    lowest_up = len(lines)
    while now() - stopped_at < 60:
        current = await pods("backend")
        lowest_ready = min(lowest_ready, sum(pod["ready"] for pod in current))
        lowest_up = min(lowest_up, sum(line.up for line in lines))
        await asyncio.sleep(1)
    sent_during = len(traffic.sent) - sent_before
    during = [item["took"] for item in traffic.sent[sent_before:]]
    say(f"  During the minute: {sent_during} messages saved, lines up at the lowest {lowest_up} of {len(lines)}. Send times: {seconds(during)}.")
    codes = Counter(code for line in lines for code in line.close_codes)
    say(f"  Close codes so far: {dict(codes)} (1011 = closed on purpose because Redis is down, D24).")
    check(codes[1011] > 0 and lowest_up < len(lines), "lines close cleanly once Redis is gone (D24)")
    check(sent_during > 10, "sends kept working (D24)")
    check(lowest_ready == 2, "both backends stayed ready for the whole minute")

    await kubectl("scale", "statefulset/redis", "--replicas=1")
    started_back = now()
    await kubectl("rollout", "status", "statefulset/redis", "--timeout=120s")
    say(f"  Redis is back after {now() - started_back:.1f} s.")
    back = await until(lambda: all(line.up for line in lines), 90)
    check(back, f"all {len(lines)} lines came back, {now() - started_back:.1f} s after Redis was started again")

    check({pod["name"]: pod["restarts"] for pod in await pods("backend")} == backend_before, f"no backend restarted: {backend_before}")
    check({pod["name"]: pod["restarts"] for pod in await pods("worker")} == worker_before, f"the worker didn't restart: {worker_before}")

    # Pub/sub works again: a brand-new message arrives live on the line, not by catch-up.
    live_before = sum(how == "live" for got in people[1].got.values() for how in got.values())
    await asyncio.sleep(8)
    live_after = sum(how == "live" for got in people[1].got.values() for how in got.values())
    check(live_after > live_before, "live pushes work again")
    watch.stop()
    await traffic.finish()
    await asyncio.sleep(1)
    say(f"  Health through the front door: {len(watch.answers)} asks. Not 200: {dict(watch.bad())}. Longest gap between answers: {watch.slowest_gap():.1f} s.")
    check(not watch.bad(), "health answered 200 for the whole outage")
    await traffic.report_losses()
    await close_tabs(people)


async def database_summary() -> tuple[str, str]:
    """Row counts and a fingerprint of the messages, asked straight from PostgreSQL."""
    query = "select (select count(*) from users), count(*), md5(string_agg(id::text, ',' order by id)) from messages"
    raw = await kubectl("exec", "postgres-0", "--", "sh", "-c", f'psql -At -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "{query}"')
    claim = json.loads(await kubectl("get", "pvc", "data-postgres-0", "-o", "json"))
    return raw.strip(), claim["spec"]["volumeName"]


async def demo_7() -> None:
    say("\n== Demo 7: delete the PostgreSQL pod")
    people, pairs = await people_in_pairs()
    traffic = Traffic(pairs[:1], 1.0)
    await asyncio.sleep(3)
    await traffic.finish()
    await traffic.report_losses()

    data_before, volume_before = await database_summary()
    pod_before = (await pods("postgres"))[0]
    backends_before = {pod["name"]: pod["restarts"] for pod in await pods("backend")}
    say(f"  Before: users|messages|fingerprint = {data_before}, volume {volume_before}.")

    deleted_at = now()
    await kubectl("delete", "pod", "postgres-0", "--wait=false")
    # Wait for the new pod, not the old one still on its way out.
    while True:
        current = await pods("postgres")
        if current and current[0]["uid"] != pod_before["uid"] and current[0]["ready"]:
            break
        if now() - deleted_at > 180:
            raise Failed("PostgreSQL didn't come back")
        await asyncio.sleep(0.5)
    say(f"  A new postgres-0 was ready {now() - deleted_at:.1f} s after the delete.")

    data_after, volume_after = await database_summary()
    say(f"  After:  users|messages|fingerprint = {data_after}, volume {volume_after}.")
    check(data_before == data_after, "the same data")
    check(volume_before == volume_after, "the same volume")
    check((await pods("postgres"))[0]["uid"] != pod_before["uid"], "it really was a new pod")

    traffic = Traffic(pairs[:1], 1.0)
    await asyncio.sleep(4)
    await traffic.finish()
    await traffic.report_losses()
    check({pod["name"]: pod["restarts"] for pod in await pods("backend")} == backends_before, "no backend restarted: liveness doesn't depend on the database")


DEMOS = {"1": demo_1, "2": demo_2, "3": demo_3, "4": demo_4, "5": demo_5, "6": demo_6, "7": demo_7}


async def main(wanted: list[str]) -> int:
    failed = []
    for index, number in enumerate(wanted):
        try:
            if index:
                # Each user may get 10 tickets a minute (D24). Let it clear, so one
                # demo's reconnects don't slow the next demo's.
                await asyncio.sleep(70)
            await DEMOS[number]()
        except Failed as failure:
            say(f"  Demo {number} stopped: {failure}")
            failed.append(number)
        for thing in _running:
            thing.stop()
        _running.clear()
        if _ring:
            await close_tabs(_ring[0])
    say(f"\nDemos run: {' '.join(wanted)}. Failed: {' '.join(failed) or 'none'}.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:] or list(DEMOS))))
