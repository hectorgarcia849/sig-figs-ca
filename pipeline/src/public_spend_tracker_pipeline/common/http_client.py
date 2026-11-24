"""Set up web connections that try again when a server has a brief problem.

Every extractor gets its web client from open_client() here, so time limits,
how we identify ourselves, encryption settings and retries are decided in one
place.

When a request fails in a way that waiting might fix (the connection fails,
the server reports an error of its own, or it asks us to slow down), the
request is sent again after a short wait. Errors that mean the request itself
is wrong, such as 404 "not found", are passed on straight away, because
asking again would get the same answer.

The retries happen underneath the client, so code using it just calls
client.get(...) or client.post(...) as usual.

One limit: if a download breaks after the file has started arriving, it is
not retried here. The extractor deletes the partial file and reports the
table as failed, and the next run tries again.
"""

from __future__ import annotations

import logging
import ssl
import time
from collections.abc import Callable

import certifi
import httpx

from public_spend_tracker_pipeline.common.settings import (
    HTTP_MAX_ATTEMPTS,
    HTTP_RETRY_WAIT_SECONDS,
    HTTP_TIMEOUT_SECONDS,
    TLS_KEY_EXCHANGE,
    USER_AGENT,
)

log = logging.getLogger(__name__)

# Server answers that mean "try again later":
#   429  too many requests: they want us to slow down
#   500  the server hit an error of its own
#   502  a server in front of theirs got a bad answer from it
#   503  the server is overloaded or down for maintenance
#   504  a server in front of theirs gave up waiting for it
RETRY_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class RetryingTransport(httpx.BaseTransport):
    """Sends each request, and sends it again if a brief problem got in the way.

    It wraps httpx's normal transport (the part that actually talks to the
    server) and tries up to max_attempts times. Before each new attempt it
    waits, starting at first_wait_seconds and doubling each time: with the
    default settings, 5 seconds and then 10.

    inner               The transport that does the real sending.
    max_attempts        Total tries, including the first.
    first_wait_seconds  Wait before the second try. Doubles after that.
    wait                The function that does the waiting. Tests pass one
                        that only records the wait, so they run instantly.
    """

    def __init__(
        self,
        inner: httpx.BaseTransport,
        max_attempts: int = HTTP_MAX_ATTEMPTS,
        first_wait_seconds: float = HTTP_RETRY_WAIT_SECONDS,
        wait: Callable[[float], None] = time.sleep,
    ) -> None:
        self.inner = inner
        self.max_attempts = max_attempts
        self.first_wait_seconds = first_wait_seconds
        self.wait = wait

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Send the request, trying again after a wait if it is worth it."""
        for attempt in range(1, self.max_attempts):
            try:
                response = self.inner.handle_request(request)
            except httpx.TransportError as error:
                problem = f"could not be reached ({type(error).__name__})"
            else:
                if response.status_code not in RETRY_STATUS_CODES:
                    return response
                response.close()  # we will not read this answer; free the connection
                problem = f"answered {response.status_code}"
            self._wait_before_next_attempt(request, problem, attempt)

        # Last attempt: whatever happens now, answer or error, is passed on.
        return self.inner.handle_request(request)

    def _wait_before_next_attempt(self, request: httpx.Request, problem: str, attempt: int) -> None:
        """Log what went wrong, then wait. The wait doubles after each attempt."""
        wait_seconds = self.first_wait_seconds * 2 ** (attempt - 1)
        log.warning(
            f"{request.url.host} {problem}, trying again in {wait_seconds:g} s "
            f"(attempt {attempt + 1} of {self.max_attempts})"
        )
        self.wait(wait_seconds)

    def close(self) -> None:
        """Close the inner transport's open connections."""
        self.inner.close()


def open_client() -> httpx.Client:
    """A web client with our time limit, user agent, encryption fix and retries.

    Use it in a with-block so its connections are closed when you are done:

        with open_client() as client:
            client.get(...)
    """
    # Trust the certificate authorities in certifi's up-to-date list (the one httpx
    # uses by default). Python's built-in list can lag behind: in November 2026 it
    # lacked the authority behind Elections Canada's certificate (Sectigo R46).
    encryption = ssl.create_default_context(cafile=certifi.where())
    encryption.set_ecdh_curve(TLS_KEY_EXCHANGE)  # see settings.TLS_KEY_EXCHANGE for why
    connection = httpx.HTTPTransport(verify=encryption)
    return httpx.Client(
        timeout=HTTP_TIMEOUT_SECONDS,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        transport=RetryingTransport(connection),
    )
