"""Core client for the gui.now API."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional


DEFAULT_BASE_URL = "https://gui.now"

# Sent as x-gui-client so the owner's library can show "Python" as the source
# of a page. A label only; the API never uses it for auth or billing.
CLIENT_NAME = "gui-now-python"


def _default_base_url() -> str:
    # GUI_NEW_URL is the pre-rename name; still honoured so existing setups
    # keep working without the user having to re-export anything.
    return (
        os.environ.get("GUI_NOW_URL")
        or os.environ.get("GUI_NEW_URL")
        or DEFAULT_BASE_URL
    )


def _default_api_key() -> Optional[str]:
    # GUI_NEW_API_KEY is the pre-rename name; see above.
    return os.environ.get("GUI_NOW_API_KEY") or os.environ.get("GUI_NEW_API_KEY")


def _default_agent() -> Optional[str]:
    return os.environ.get("GUI_NOW_AGENT") or None


@dataclass
class CanvasResult:
    id: str
    url: str
    edit_token: str
    # ISO timestamp, or None when the page never expires.
    expires_at: Optional[str]
    pro: bool
    format: str
    password_protected: bool = False
    # True when the requested expires was longer than your tier allows and the
    # API shortened it.
    expires_clamped: bool = False
    # For pages made without an account or Pro key: a one-time link a person
    # opens to sign in and keep the page in their library. Show it to the
    # human. Only returned on create.
    claim_url: Optional[str] = None
    # True when the page was created into a signed-in account.
    owned: bool = False

    def open(self) -> None:
        """Open the canvas URL in the default browser."""
        import webbrowser

        webbrowser.open(self.url)

    def summary(self) -> str:
        """One or two lines an agent can pass straight to a person."""
        expiry = (
            "never expires"
            if self.expires_at is None
            else f"expires {self.expires_at}"
        )
        if self.expires_clamped:
            expiry += ", shortened to your plan's limit"
        text = f"Canvas created: {self.url} ({expiry})"
        if self.claim_url:
            text += f"\nTo keep it, open {self.claim_url} and sign in."
        return text


class GuiNowError(Exception):
    """An error from the GUI API.

    status is the HTTP status (None for errors raised before any request).
    On a 409 from extend, max_expires_at is the latest expiry the page can
    reach.
    """

    def __init__(
        self,
        message: str,
        *,
        status: Optional[int] = None,
        body: Optional[dict] = None,
    ):
        super().__init__(message)
        self.status = status
        self.body = body or {}
        mx = self.body.get("max_expires_at")
        self.max_expires_at: Optional[str] = mx if isinstance(mx, str) else None


class RateLimitError(GuiNowError):
    def __init__(self, retry_after: str = "3600"):
        self.retry_after = retry_after
        super().__init__(
            f"Rate limited. Retry after {retry_after} seconds.", status=429
        )


class _Unset:
    """Sentinel so update() can tell 'omitted' from an explicit None."""

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "<unset>"


_UNSET = _Unset()


class GuiNowClient:
    """Client for the gui.now API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        agent: Optional[str] = None,
    ):
        """
        Args:
            api_key:  Pro key. Defaults to GUI_NOW_API_KEY.
            base_url: API origin. Defaults to GUI_NOW_URL or https://gui.now.
            agent:    name of the agent publishing, e.g. "Claude Code", shown
                      in the owner's library. Defaults to GUI_NOW_AGENT. A
                      label only, never used for auth.
        """
        self.api_key = api_key or _default_api_key()
        self.base_url = (base_url or _default_base_url()).rstrip("/")
        self.agent = agent or _default_agent()

    # ---- create -----------------------------------------------------------

    def create(
        self,
        *,
        html: Optional[str] = None,
        markdown: Optional[str] = None,
        mermaid: Optional[str] = None,
        frames: Optional[list] = None,
        title: Optional[str] = None,
        theme: Optional[str] = None,
        expires: Optional[str] = None,
        password: Optional[str] = None,
        agent: Optional[str] = None,
    ) -> CanvasResult:
        """Create a canvas.

        Exactly one content argument is needed:
            html:     raw HTML.
            markdown: Markdown, rendered server-side.
            mermaid:  a Mermaid diagram, rendered pannable and zoomable.
            frames:   multi-tab views, [{"html": ..., "label": ...}, ...].

        Args:
            title:    display name for the toolbar and OG meta.
            theme:    "dark" (default) or "light".
            expires:  a duration like "30m", "24h" or "7d", or "never".
                      Defaults: 24h anonymous, 72h with a free account, never
                      with a Pro key. Longer than your tier allows (72h
                      anonymous, 7d free) is shortened, and the result has
                      expires_clamped=True.
            password: Pro only: password-protect the canvas.
            agent:    overrides the client's agent label for this page.

        Pages made without an account or Pro key come back with claim_url:
        show it to the person so they can keep the page.
        """
        body: dict[str, Any] = {}
        if html is not None:
            body["html"] = html
        if markdown is not None:
            body["markdown"] = markdown
        if mermaid is not None:
            body["mermaid"] = mermaid
        if frames is not None:
            body["frames"] = frames
        if title is not None:
            body["title"] = title
        if theme is not None:
            body["theme"] = theme
        if expires is not None:
            body["expires"] = expires
        if password is not None:
            body["password"] = password
        agent = agent or self.agent
        if agent:
            body["agent"] = agent

        if not any(
            body.get(k) for k in ("html", "markdown", "mermaid", "frames")
        ):
            raise GuiNowError(
                "One of html, markdown, mermaid or frames is required"
            )

        return _parse(self._request("POST", "/api/canvas", body))

    def create_diagram(
        self,
        mermaid: str,
        *,
        title: Optional[str] = None,
        theme: Optional[str] = None,
        expires: Optional[str] = None,
    ) -> CanvasResult:
        """Create a Mermaid diagram canvas."""
        return self.create(
            mermaid=mermaid, title=title, theme=theme, expires=expires
        )

    # ---- update -----------------------------------------------------------

    def update(
        self,
        canvas_id: str,
        edit_token: str,
        *,
        html: Optional[str] = None,
        title: Optional[str] = None,
        frames: Optional[list] = None,
        password: Any = _UNSET,
    ) -> dict:
        """Replace a canvas's content. Free tier allows 3 edits; Pro unlimited.

        Pass password=None to remove password protection, or omit it to leave
        whatever protection the canvas already has untouched.
        """
        body: dict[str, Any] = {}
        if html is not None:
            body["html"] = html
        if title is not None:
            body["title"] = title
        if frames is not None:
            body["frames"] = frames
        if password is not _UNSET:
            body["password"] = password

        if not body:
            raise GuiNowError("update needs at least one field to change")

        return self._request(
            "PUT",
            f"/api/canvas/{_quote(canvas_id)}",
            body,
            headers={"Authorization": f"Bearer {edit_token}"},
        )

    def extend(
        self,
        canvas_id: str,
        *,
        edit_token: Optional[str] = None,
        expires: Optional[str] = None,
    ) -> dict:
        """Push a canvas's expiry forward, measured from now.

        With no arguments: 24h from now. A page nobody owns stops at 72h after
        it was created; past that the API answers 409 and the GuiNowError
        carries max_expires_at.

        Pass the edit token to choose a duration ("7d", "never"), shortened to
        the page's tier limit. Returns {"id", "expires_at", "extended"} and
        expires_clamped when the request was shortened.
        """
        # The API ignores expires without auth and just adds 24h; say so here
        # instead of letting the caller think they got what they asked for.
        if expires is not None and not edit_token:
            raise GuiNowError(
                "extend: pass edit_token to choose an expiry; "
                "without it extend adds 24h"
            )
        body: dict[str, Any] = {}
        if expires is not None:
            body["expires"] = expires
        headers = {"Authorization": f"Bearer {edit_token}"} if edit_token else None
        return self._request(
            "POST", f"/api/canvas/{_quote(canvas_id)}/extend", body, headers=headers
        )

    # ---- transport --------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        body: dict,
        headers: Optional[dict] = None,
    ) -> dict:
        req_headers = {"Content-Type": "application/json", "x-gui-client": CLIENT_NAME}
        if self.api_key:
            req_headers["x-api-key"] = self.api_key
        if headers:
            req_headers.update(headers)

        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(body).encode("utf-8"),
            headers=req_headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise RateLimitError(e.headers.get("Retry-After", "3600")) from e
            raw = e.read().decode("utf-8", errors="replace")
            body: dict = {}
            detail = raw
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    body = parsed
                    detail = parsed.get("error", raw)
            except json.JSONDecodeError:
                pass
            raise GuiNowError(
                f"API error ({e.code}): {detail}", status=e.code, body=body
            ) from e


def _quote(canvas_id: str) -> str:
    return urllib.parse.quote(canvas_id, safe="")


def _parse(d: dict) -> CanvasResult:
    return CanvasResult(
        id=d["id"],
        url=d["url"],
        edit_token=d["edit_token"],
        expires_at=d.get("expires_at"),
        pro=d.get("pro", False),
        format=d.get("format", "html"),
        password_protected=d.get("password_protected", False),
        expires_clamped=bool(d.get("expires_clamped", False)),
        claim_url=d.get("claim_url"),
        owned=bool(d.get("owned", False)),
    )


# ---- module-level conveniences using a default client ---------------------


def create(**kwargs) -> CanvasResult:
    return GuiNowClient().create(**kwargs)


def create_diagram(mermaid: str, **kwargs) -> CanvasResult:
    return GuiNowClient().create_diagram(mermaid, **kwargs)


def update(canvas_id: str, edit_token: str, **kwargs) -> dict:
    return GuiNowClient().update(canvas_id, edit_token, **kwargs)


def extend(canvas_id: str, **kwargs) -> dict:
    return GuiNowClient().extend(canvas_id, **kwargs)


def create_canvas(
    html: Optional[str] = None,
    markdown: Optional[str] = None,
    title: Optional[str] = None,
    expires: Optional[str] = None,
) -> str:
    """Quick helper — create a canvas and return just the URL."""
    return GuiNowClient().create(
        html=html, markdown=markdown, title=title, expires=expires
    ).url
