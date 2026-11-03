"""Client tests against a local fake of the GUI API (stdlib only).

Run: PYTHONPATH=src python -m unittest discover -s tests
"""

from __future__ import annotations

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from guinow import CanvasResult, GuiNowClient, GuiNowError, RateLimitError


class FakeApi:
    """Records each request and answers with the next queued response."""

    def __init__(self) -> None:
        self.requests: list[dict] = []
        self.responses: list[tuple[int, dict, dict]] = []
        api = self

        class Handler(BaseHTTPRequestHandler):
            def _handle(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                api.requests.append(
                    {
                        "method": self.command,
                        "path": self.path,
                        "headers": {k.lower(): v for k, v in self.headers.items()},
                        "body": json.loads(raw) if raw else None,
                    }
                )
                status, body, headers = api.responses.pop(0)
                data = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                for k, v in headers.items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(data)

            do_POST = _handle
            do_PUT = _handle

            def log_message(self, *args) -> None:  # keep test output clean
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def reply(self, status: int, body: dict, headers: dict | None = None) -> None:
        self.responses.append((status, body, headers or {}))

    @property
    def last(self) -> dict:
        return self.requests[-1]

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


CREATED = {
    "id": "abc123",
    "url": "https://gui.now/abc123",
    "edit_token": "tok_secret",
    "expires_at": "2026-11-04T12:00:00.000Z",
    "pro": False,
    "format": "html",
}


class ClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.api = FakeApi()
        self.client = GuiNowClient(base_url=self.api.url)
        self.client.api_key = None  # ignore any key in the environment
        self.client.agent = None

    def tearDown(self) -> None:
        self.api.close()

    # ---- create ----------------------------------------------------------

    def test_create_returns_claim_url_for_anonymous_pages(self) -> None:
        claim = "https://gui.now/claim/abc123#token=aaaaaaaaaaaaaaaaaaaaaaaa"
        self.api.reply(201, {**CREATED, "claim_url": claim})
        result = self.client.create(html="<h1>hi</h1>")
        self.assertEqual(result.claim_url, claim)
        self.assertFalse(result.owned)
        self.assertFalse(result.expires_clamped)
        self.assertIn(claim, result.summary())

    def test_create_sends_client_header_and_agent(self) -> None:
        self.api.reply(201, CREATED)
        self.client.create(html="<p>x</p>", agent="Claude Code")
        req = self.api.last
        self.assertEqual(req["method"], "POST")
        self.assertEqual(req["path"], "/api/canvas")
        self.assertEqual(req["headers"]["x-gui-client"], "gui-now-python")
        self.assertEqual(req["body"]["agent"], "Claude Code")
        self.assertNotIn("x-api-key", req["headers"])

    def test_client_agent_is_the_default_and_per_call_wins(self) -> None:
        client = GuiNowClient(base_url=self.api.url, agent="Stratus Agent")
        client.api_key = None
        self.api.reply(201, CREATED)
        client.create(html="<p>x</p>")
        self.assertEqual(self.api.last["body"]["agent"], "Stratus Agent")
        self.api.reply(201, CREATED)
        client.create(html="<p>x</p>", agent="Cursor")
        self.assertEqual(self.api.last["body"]["agent"], "Cursor")

    def test_no_agent_means_no_agent_field(self) -> None:
        self.api.reply(201, CREATED)
        self.client.create(html="<p>x</p>")
        self.assertNotIn("agent", self.api.last["body"])

    def test_never_expires_is_none(self) -> None:
        self.api.reply(201, {**CREATED, "expires_at": None, "pro": True})
        result = self.client.create(html="<p>x</p>", expires="never")
        self.assertEqual(self.api.last["body"]["expires"], "never")
        self.assertIsNone(result.expires_at)
        self.assertIsNone(result.claim_url)
        self.assertIn("never expires", result.summary())

    def test_clamped_expiry_is_reported(self) -> None:
        self.api.reply(201, {**CREATED, "expires_clamped": True, "owned": True})
        result = self.client.create(html="<p>x</p>", expires="30d")
        self.assertTrue(result.expires_clamped)
        self.assertTrue(result.owned)
        self.assertIn("shortened", result.summary())

    def test_create_diagram_passes_expires(self) -> None:
        self.api.reply(201, {**CREATED, "format": "mermaid"})
        self.client.create_diagram("graph TD\n  A-->B", expires="2h")
        self.assertEqual(self.api.last["body"]["expires"], "2h")
        self.assertEqual(self.api.last["body"]["mermaid"], "graph TD\n  A-->B")

    def test_create_needs_content(self) -> None:
        with self.assertRaises(GuiNowError) as ctx:
            self.client.create(title="empty")
        self.assertIsNone(ctx.exception.status)
        self.assertEqual(self.api.requests, [])

    def test_bad_expires_surfaces_status_and_message(self) -> None:
        self.api.reply(400, {"error": "expires must be a duration"})
        with self.assertRaises(GuiNowError) as ctx:
            self.client.create(html="<p>x</p>", expires="soon")
        self.assertEqual(ctx.exception.status, 400)
        self.assertIn("expires must be a duration", str(ctx.exception))

    def test_rate_limit(self) -> None:
        self.api.reply(429, {"error": "slow down"}, {"Retry-After": "120"})
        with self.assertRaises(RateLimitError) as ctx:
            self.client.create(html="<p>x</p>")
        self.assertEqual(ctx.exception.retry_after, "120")
        self.assertEqual(ctx.exception.status, 429)

    def test_old_result_shape_still_parses(self) -> None:
        # The CanvasResult fields that existed before v2 keep their positions.
        r = CanvasResult("a", "u", "t", "2026-01-01T00:00:00Z", False, "html")
        self.assertIsNone(r.claim_url)
        self.assertFalse(r.expires_clamped)

    # ---- update ----------------------------------------------------------

    def test_update_sends_bearer_and_quotes_id(self) -> None:
        self.api.reply(200, {"id": "a/b", "updated": True})
        self.client.update("a/b", "tok_secret", title="T")
        req = self.api.last
        self.assertEqual(req["method"], "PUT")
        self.assertEqual(req["path"], "/api/canvas/a%2Fb")
        self.assertEqual(req["headers"]["authorization"], "Bearer tok_secret")

    # ---- extend ----------------------------------------------------------

    def test_extend_without_token_adds_24h(self) -> None:
        self.api.reply(200, {"id": "abc123", "expires_at": "x", "extended": True})
        out = self.client.extend("abc123")
        req = self.api.last
        self.assertEqual(req["path"], "/api/canvas/abc123/extend")
        self.assertNotIn("authorization", req["headers"])
        self.assertEqual(req["body"], {})  # same as before v2: no expires
        self.assertTrue(out["extended"])

    def test_extend_with_token_and_expires(self) -> None:
        self.api.reply(
            200,
            {"id": "abc123", "expires_at": None, "extended": True},
        )
        out = self.client.extend("abc123", edit_token="tok_secret", expires="never")
        req = self.api.last
        self.assertEqual(req["headers"]["authorization"], "Bearer tok_secret")
        self.assertEqual(req["body"], {"expires": "never"})
        self.assertIsNone(out["expires_at"])

    def test_extend_expires_without_token_fails_before_calling(self) -> None:
        with self.assertRaises(GuiNowError) as ctx:
            self.client.extend("abc123", expires="7d")
        self.assertIn("edit_token", str(ctx.exception))
        self.assertEqual(self.api.requests, [])

    def test_extend_past_ceiling_carries_max_expires_at(self) -> None:
        self.api.reply(
            409,
            {
                "error": "This page can't be extended past 72 hours",
                "max_expires_at": "2026-11-06T12:00:00.000Z",
            },
        )
        with self.assertRaises(GuiNowError) as ctx:
            self.client.extend("abc123")
        self.assertEqual(ctx.exception.status, 409)
        self.assertEqual(ctx.exception.max_expires_at, "2026-11-06T12:00:00.000Z")

    def test_owned_page_without_auth_is_401(self) -> None:
        self.api.reply(401, {"error": "Sign in or pass the edit token"})
        with self.assertRaises(GuiNowError) as ctx:
            self.client.extend("abc123")
        self.assertEqual(ctx.exception.status, 401)
        self.assertIsNone(ctx.exception.max_expires_at)


if __name__ == "__main__":
    unittest.main()
