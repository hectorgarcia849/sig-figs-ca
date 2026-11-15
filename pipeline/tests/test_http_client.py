"""Tests for the retrying web client, run offline against scripted answers.

Each test scripts what the "server" does on each attempt, then checks how many
attempts were made, how long the client would have waited, and what it passed
on. Waits are only recorded, never slept, so the tests run instantly.
"""

import httpx
import pytest

from public_spend_tracker_pipeline.http_client import RetryingTransport

TEST_URL = "https://example.test/data"

# Stands in for a failed connection in a script of server behaviour.
CONNECTION_FAILS = "connection fails"


class ScriptedServer:
    """A fake server that gives the scripted outcome on each attempt, in order.

    Each outcome is a status code to answer with, or CONNECTION_FAILS.
    """

    def __init__(self, *outcomes: int | str) -> None:
        self.outcomes = list(outcomes)
        self.attempts = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        outcome = self.outcomes[self.attempts]
        self.attempts += 1
        if outcome == CONNECTION_FAILS:
            raise httpx.ConnectError("could not connect", request=request)
        return httpx.Response(outcome)


def make_client(server: ScriptedServer, waits: list[float]) -> httpx.Client:
    """A client with three attempts and a 5-second first wait, recording waits."""
    transport = RetryingTransport(
        httpx.MockTransport(server),
        max_attempts=3,
        first_wait_seconds=5,
        wait=waits.append,
    )
    return httpx.Client(transport=transport)


def test_server_error_then_success_is_retried():
    server = ScriptedServer(503, 200)
    waits: list[float] = []
    response = make_client(server, waits).get(TEST_URL)
    assert response.status_code == 200
    assert server.attempts == 2
    assert waits == [5]


def test_gives_up_after_last_attempt_and_passes_on_the_answer():
    server = ScriptedServer(503, 503, 503)
    waits: list[float] = []
    response = make_client(server, waits).get(TEST_URL)
    assert response.status_code == 503
    assert server.attempts == 3
    assert waits == [5, 10]  # the wait doubles


def test_not_found_is_not_retried():
    server = ScriptedServer(404)
    waits: list[float] = []
    response = make_client(server, waits).get(TEST_URL)
    assert response.status_code == 404
    assert server.attempts == 1
    assert waits == []


def test_failed_connection_then_success_is_retried():
    server = ScriptedServer(CONNECTION_FAILS, 200)
    waits: list[float] = []
    response = make_client(server, waits).get(TEST_URL)
    assert response.status_code == 200
    assert server.attempts == 2


def test_connection_failing_every_time_raises_the_error():
    server = ScriptedServer(CONNECTION_FAILS, CONNECTION_FAILS, CONNECTION_FAILS)
    waits: list[float] = []
    with pytest.raises(httpx.ConnectError):
        make_client(server, waits).get(TEST_URL)
    assert server.attempts == 3
    assert waits == [5, 10]


def test_request_body_is_sent_again_on_retry():
    """Statistics Canada's details request is a POST, so its body must survive a retry."""
    bodies: list[bytes] = []

    def server(request: httpx.Request) -> httpx.Response:
        bodies.append(request.read())
        return httpx.Response(503 if len(bodies) == 1 else 200)

    transport = RetryingTransport(httpx.MockTransport(server), wait=lambda seconds: None)
    response = httpx.Client(transport=transport).post(TEST_URL, json=[{"productId": 10100005}])
    assert response.status_code == 200
    assert bodies[0] == bodies[1] == b'[{"productId":10100005}]'
