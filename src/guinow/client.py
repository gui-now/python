"""Core client for the gui.now API."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional


DEFAULT_BASE_URL = "https://gui.now"


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


@dataclass
class CanvasResult:
    id: str
    url: str
    edit_token: str
    expires_at: str
    pro: bool
    format: str
    password_protected: bool = False

    def open(self) -> None:
        """Open the canvas URL in the default browser."""
        import webbrowser

        webbrowser.open(self.url)


class GuiNowError(Exception):
    pass


class RateLimitError(GuiNowError):
    def __init__(self, retry_after: str = "3600"):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after} seconds.")


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
    ):
        self.api_key = api_key or _default_api_key()
        self.base_url = (base_url or _default_base_url()).rstrip("/")

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
            expires:  Pro only: "1h", "24h", "7d", "14d", "30d".
            password: Pro only: password-protect the canvas.
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
    ) -> CanvasResult:
        """Create a Mermaid diagram canvas."""
        return self.create(mermaid=mermaid, title=title, theme=theme)

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
            f"/api/canvas/{canvas_id}",
            body,
            headers={"Authorization": f"Bearer {edit_token}"},
        )

    def extend(self, canvas_id: str) -> dict:
        """Extend the canvas expiry to 24 hours from now."""
        return self._request("POST", f"/api/canvas/{canvas_id}/extend", {})

    # ---- transport --------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        body: dict,
        headers: Optional[dict] = None,
    ) -> dict:
        req_headers = {"Content-Type": "application/json"}
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
            detail = e.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(detail).get("error", detail)
            except json.JSONDecodeError:
                pass
            raise GuiNowError(f"API error ({e.code}): {detail}") from e


def _parse(d: dict) -> CanvasResult:
    return CanvasResult(
        id=d["id"],
        url=d["url"],
        edit_token=d["edit_token"],
        expires_at=d["expires_at"],
        pro=d.get("pro", False),
        format=d.get("format", "html"),
        password_protected=d.get("password_protected", False),
    )


# ---- module-level conveniences using a default client ---------------------


def create(**kwargs) -> CanvasResult:
    return GuiNowClient().create(**kwargs)


def create_diagram(mermaid: str, **kwargs) -> CanvasResult:
    return GuiNowClient().create_diagram(mermaid, **kwargs)


def update(canvas_id: str, edit_token: str, **kwargs) -> dict:
    return GuiNowClient().update(canvas_id, edit_token, **kwargs)


def extend(canvas_id: str) -> dict:
    return GuiNowClient().extend(canvas_id)


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
