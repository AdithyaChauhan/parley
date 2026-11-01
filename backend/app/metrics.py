"""Parley's numbers for Prometheus (D32). Every backend number is defined here,
in one list, and each feature bumps its own. Prometheus reads them all from
/metrics (main.py) every 15 s.

Three kinds: a Counter only goes up (Prometheus works out "per second" from how
fast it grows), a Gauge goes up and down, and a Histogram drops each timing into
buckets, so Grafana can read p50, p95 and p99."""

import time

from fastapi import Request
from fastapi.routing import iter_route_contexts
from prometheus_client import Counter, Gauge, Histogram, disable_created_metrics

# Without this, every counter also shows a second "_created" line (when it
# started). Prometheus doesn't need it here, and /metrics is easier to read.
disable_created_metrics()

# Every HTTP request, by method, route template and status (the middleware below).
HTTP_REQUESTS = Counter("http_requests_total", "HTTP requests handled", ["method", "route", "status"])
HTTP_SECONDS = Histogram(
    "http_request_duration_seconds", "How long HTTP requests took", ["method", "route", "status"]
)

# Open live lines (WebSockets) on this copy, read from the switchboard (manager.py).
LIVE_LINES = Gauge("live_lines_open", "Open live lines on this copy")

# New messages saved. A resend of the same message isn't counted again (D18).
MESSAGES_SENT = Counter("messages_sent_total", "New messages saved")

# The radio (D23): one shout per person on the sending copy, and every event
# this copy heard for its own lines.
PUSHES_PUBLISHED = Counter("live_pushes_published_total", "Live events published on Redis, one per person")
PUSHES_RECEIVED = Counter("live_pushes_received_total", "Live events this copy heard on Redis")

# Requests refused with 429, by the limit rule that refused them (D24).
RATE_LIMITED = Counter("rate_limited_total", "Requests refused with 429", ["rule"])


# Route -> its full template, like /api/chats/{chat_id}/messages. A route's own
# .path is only its part inside its router (/chats/{chat_id}/messages, no /api),
# so the full one comes from FastAPI's list of routes. Filled on the first
# request, when every route is in. Keyed by id(): routes can't be dict keys.
_templates: dict[int, str] = {}


def _route(request: Request) -> str:
    """The route's template, never the real id: one group per route, not one
    per chat (D32). FastAPI notes the matched route while it routes. An address
    with no route (a bot trying random links) gets one shared label, so those
    can't make thousands of groups either."""
    route = request.scope.get("route")
    if route is None:
        return "unmatched"
    if not _templates:
        for context in iter_route_contexts(request.app.routes):
            _templates[id(context.original_route)] = context.path_format
    return _templates.get(id(route), route.path)


async def measure(request: Request, call_next):
    """Times every HTTP request and counts it. The live line is a WebSocket, not
    HTTP, so it never comes through here: live_lines_open covers it."""
    start = time.perf_counter()
    # If the route crashes, there's no response to read: the browser gets a 500.
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        route = _route(request)
        # Prometheus's own visits every 15 s aren't Parley's traffic: an idle
        # Parley shows 0 requests/s.
        if route != "/metrics":
            labels = (request.method, route, str(status))
            HTTP_REQUESTS.labels(*labels).inc()
            HTTP_SECONDS.labels(*labels).observe(time.perf_counter() - start)
