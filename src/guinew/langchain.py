"""LangChain tool for gui.new."""

from __future__ import annotations

from typing import Optional, Type

try:
    from langchain_core.tools import BaseTool
    from pydantic import BaseModel, Field
except ImportError:
    raise ImportError(
        "langchain_core and pydantic are required. "
        "Install with: pip install guinew[langchain]"
    )

from guinew.client import GuiNewClient


class CreateCanvasInput(BaseModel):
    html: Optional[str] = Field(None, description="Raw HTML content for the canvas")
    markdown: Optional[str] = Field(None, description="Markdown content (rendered server-side)")
    title: Optional[str] = Field(None, description="Optional canvas title")
    expires: Optional[str] = Field(None, description="Expiry: 1h, 24h, 7d, 14d, 30d")


class GuiNewTool(BaseTool):
    """LangChain tool to create shareable HTML canvases on gui.new."""

    name: str = "create_gui_canvas"
    description: str = (
        "Create a shareable HTML canvas on gui.new. "
        "Send HTML or Markdown content and get a live URL anyone can view. "
        "Use for dashboards, reports, previews, or any visual output."
    )
    args_schema: Type[BaseModel] = CreateCanvasInput
    api_key: Optional[str] = None

    def _run(
        self,
        html: Optional[str] = None,
        markdown: Optional[str] = None,
        title: Optional[str] = None,
        expires: Optional[str] = None,
    ) -> str:
        client = GuiNewClient(api_key=self.api_key)
        result = client.create(html=html, markdown=markdown, title=title, expires=expires)
        return f"Canvas created: {result.url} (expires {result.expires_at})"
