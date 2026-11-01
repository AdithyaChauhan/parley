import uuid
from contextlib import contextmanager

from prometheus_client.parser import text_string_to_metric_families


def _value(client, name, labels=None) -> float:
    """One number from /metrics, read the way Prometheus reads it. 0 if it
    isn't there yet."""
    text = client.get("/metrics").text
    for family in text_string_to_metric_families(text):
        for sample in family.samples:
            if sample.name == name and sample.labels == (labels or {}):
                return sample.value
    return 0.0


def _start_chat(client, me, email) -> str:
    response = client.post("/api/chats/direct", json={"email": email}, headers=me)
    assert response.status_code == 201
    return response.json()["id"]


def _send(client, me, chat_id, client_msg_id=None):
    return client.post(
        f"/api/chats/{chat_id}/messages",
        json={"client_msg_id": str(client_msg_id or uuid.uuid4()), "body": "hi"},
        headers=me,
    )


@contextmanager
def _open_line(client, me):
    """One open tab: get a ticket, open the line, read the hello."""
    ticket = client.post("/api/live/ticket", headers=me).json()["ticket"]
    with client.websocket_connect(f"/api/live?ticket={ticket}") as line:
        assert line.receive_json()["type"] == "hello"
        yield line


def test_a_request_moves_the_counter_and_the_timing(client):
    labels = {"method": "GET", "route": "/api/health", "status": "200"}
    count_before = _value(client, "http_requests_total", labels)
    timed_before = _value(client, "http_request_duration_seconds_count", labels)

    client.get("/api/health")

    assert _value(client, "http_requests_total", labels) == count_before + 1
    # The histogram has its own count of what it timed.
    assert _value(client, "http_request_duration_seconds_count", labels) == timed_before + 1


def test_metrics_doesnt_count_itself(client):
    client.get("/metrics")

    # Prometheus's own visits aren't Parley's traffic (an idle Parley shows 0/s).
    assert 'route="/metrics"' not in client.get("/metrics").text


def test_routes_are_labelled_by_template_never_the_real_id(client, sign_up):
    ana = sign_up("Ana")
    sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com")
    labels = {"method": "POST", "route": "/api/chats/{chat_id}/messages", "status": "201"}
    sends_before = _value(client, "http_requests_total", labels)
    messages_before = _value(client, "messages_sent_total")

    first = uuid.uuid4()
    assert _send(client, ana, chat_id, first).status_code == 201
    # A resend of the same message: answered 200, and not a new message (D18).
    assert _send(client, ana, chat_id, first).status_code == 200

    assert _value(client, "http_requests_total", labels) == sends_before + 1
    assert _value(client, "messages_sent_total") == messages_before + 1
    # The template, never the chat's real id: one group per route, not per chat.
    assert chat_id not in client.get("/metrics").text


def test_an_address_with_no_route_gets_one_shared_label(client):
    labels = {"method": "GET", "route": "unmatched", "status": "404"}
    before = _value(client, "http_requests_total", labels)

    client.get("/api/wp-admin.php")
    client.get("/api/random-123")

    assert _value(client, "http_requests_total", labels) == before + 2
    assert "wp-admin" not in client.get("/metrics").text


def test_live_lines_open_follows_the_switchboard(client, sign_up):
    ana = sign_up("Ana")
    before = _value(client, "live_lines_open")

    with _open_line(client, ana), _open_line(client, ana):
        # Two tabs, two lines.
        assert _value(client, "live_lines_open") == before + 2

    assert _value(client, "live_lines_open") == before


def test_pushes_are_counted_when_published_and_when_heard(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com")

    with _open_line(client, ben) as bens_line:
        published = _value(client, "live_pushes_published_total")
        received = _value(client, "live_pushes_received_total")

        _send(client, ana, chat_id)
        assert bens_line.receive_json()["type"] == "message.new"

        # Shouted once for each member, Ana and Ben (her other tabs would hear it too).
        assert _value(client, "live_pushes_published_total") == published + 2
        # Heard once: this copy listens only for Ben, who has a line here (D23).
        assert _value(client, "live_pushes_received_total") == received + 1


def test_a_429_is_counted_by_its_rule(client, sign_up):
    ana = sign_up("Ana")
    labels = {"rule": "ticket"}
    # Every rule is there from the start, at 0 or more.
    assert 'rate_limited_total{rule="send"}' in client.get("/metrics").text
    before = _value(client, "rate_limited_total", labels)

    # Tickets: 10 per minute per user (D24), so the 11th is refused.
    replies = [client.post("/api/live/ticket", headers=ana).status_code for _ in range(11)]

    assert replies[-1] == 429
    assert _value(client, "rate_limited_total", labels) == before + 1
