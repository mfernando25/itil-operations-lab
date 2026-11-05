from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from lab import database
from lab.server import LabHandler


@pytest.fixture
def live_http(isolated_db):
    database.init_db()
    server = ThreadingHTTPServer(("127.0.0.1", 0), LabHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        yield base
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def call_json(base: str, path: str, method: str = "GET", payload: dict | None = None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(base + path, data=body, method=method,
                      headers={"Content-Type": "application/json"} if body is not None else {})
    try:
        with urlopen(request, timeout=3) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def test_g6_profile_degrades_and_recovers_through_http(live_http):
    status, _ = call_json(live_http, "/api/instructor/scenarios/6/activate", "POST", {})
    assert status == 200
    status, profile = call_json(live_http, "/api/portal/student-profile")
    assert status == 502
    assert profile["status"] == "degraded"
    status, _ = call_json(live_http, "/api/instructor/scenarios/6/reset", "POST", {})
    assert status == 200
    status, profile = call_json(live_http, "/api/portal/student-profile")
    assert status == 200
    assert profile["status"] == "ok"
    assert profile["student_id"] == "STU-1042"


def test_g7_stale_read_and_teacher_reconciliation_through_http(live_http):
    status, before = call_json(live_http, "/api/demo/enrollment")
    assert status == 200
    assert before["consultation"]["status"] == "Pendiente"
    status, _ = call_json(live_http, "/api/instructor/scenarios/7/activate", "POST", {})
    assert status == 200
    status, stale = call_json(live_http, "/api/demo/enrollment")
    assert status == 200
    assert stale["consultation"]["status"] == "Pendiente"
    with urlopen(live_http + "/instructor", timeout=3) as response:
        html = response.read().decode("utf-8")
    assert 'id="reconcile-g7"' in html
    status, result = call_json(live_http, "/api/instructor/enrollment/reconcile", "POST", {})
    assert status == 200
    assert "refleja el estado vigente" in result["message"]
    status, current = call_json(live_http, "/api/demo/enrollment")
    assert status == 200
    assert current["consultation"]["status"] == "Confirmada"


def test_student_events_are_limited_to_teacher_assigned_active_group(live_http):
    status, empty = call_json(live_http, "/api/events")
    assert status == 200
    assert empty["visible_group"] is None
    assert empty["events"] == []

    call_json(live_http, "/api/instructor/scenarios/6/activate", "POST", {})
    call_json(live_http, "/api/instructor/scenarios/7/activate", "POST", {})
    status, assigned = call_json(live_http, "/api/instructor/public-group", "POST", {"group": 6})
    assert status == 200
    assert assigned["public_group"] == 6
    status, events = call_json(live_http, "/api/events")
    assert status == 200
    assert events["visible_group"] == 6
    assert {event["group_number"] for event in events["events"]} == {6}
    status, profile = call_json(live_http, "/api/portal/student-profile")
    assert status == 502
    call_json(live_http, "/api/instructor/public-group", "POST", {"group": 7})
    status, profile = call_json(live_http, "/api/portal/student-profile")
    assert status == 200
    assert profile["status"] == "ok"
    status, state = call_json(live_http, "/api/scenario-state")
    assert state == {"visible_group": 7, "active": True}
    status, events = call_json(live_http, "/api/events")
    assert status == 200
    assert events["visible_group"] == 7
    assert {event["group_number"] for event in events["events"]} == {7}
    status, enrollment = call_json(live_http, "/api/demo/enrollment")
    assert status == 200
    assert enrollment["consultation"]["status"] == "Pendiente"
