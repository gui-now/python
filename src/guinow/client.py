"""Core client for gui.now API."""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional


API_URL = "https://gui.now/api/canvas"


@dataclass
class CanvasResult:
    id: str
    url: str
    edit_token: str
    expires_at: str
    pro: bool
    format: str
    password_protected: bool = False


class GuiNowError(Exception):
    pass


class RateLimitError(GuiNowError):
    def __init__(self, retry_after: str = "3600"):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after} seconds.")


class GuiNowClient:
    """Client for gui.now API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GUI_NOW_API_KEY")

    def create(
        self,
        *,
        html: Optional[str] = None,
        markdown: Optional[str] = None,
        title: Optional[str] = None,
        theme: Optional[str] = None,
        expires: Optional[str] = None,
        password: Optional[str] = None,
    ) -> CanvasResult:
        """Create a canvas and return the result."""
        body: dict = {}
        if html is not None:
            body["html"] = html
        if markdown is not None:
            body["markdown"] = markdown
        if title is not None:
            body["title"] = title
        if theme is not None:
            body["theme"] = theme
        if expires is not None:
            body["expires"] = expires
        if password is not None:
            body["password"] = password

        if not body.get("html") and not body.get("markdown"):
            raise GuiNowError("Either html or markdown is required")

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return CanvasResult(
                    id=result["id"],
                    url=result["url"],
                    edit_token=result["edit_token"],
                    expires_at=result["expires_at"],
                    pro=result.get("pro", False),
                    format=result.get("format", "html"),
                    password_protected=result.get("password_protected", False),
                )
        except urllib.error.HTTPError as e:
            if e.code == 429:
                retry_after = e.headers.get("Retry-After", "3600")
                raise RateLimitError(retry_after)
            body_text = e.read().decode("utf-8", errors="replace")
            raise GuiNowError(f"API error ({e.code}): {body_text}")


def create_canvas(
    html: Optional[str] = None,
    markdown: Optional[str] = None,
    title: Optional[str] = None,
    expires: Optional[str] = None,
) -> str:
    """Quick helper — create a canvas and return the URL."""
    client = GuiNowClient()
    result = client.create(html=html, markdown=markdown, title=title, expires=expires)
    return result.url
