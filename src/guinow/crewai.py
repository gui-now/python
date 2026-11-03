"""CrewAI tool for gui.now."""

from __future__ import annotations

from typing import Optional, Type

try:
    from crewai.tools import BaseTool
    from pydantic import BaseModel, Field
except ImportError:
    raise ImportError(
        "crewai and pydantic are required. "
        "Install with: pip install gui-now[crewai]"
    )

from guinow.client import GuiNowClient


class CreateCanvasInput(BaseModel):
    html: Optional[str] = Field(None, description="Raw HTML content for the canvas")
    markdown: Optional[str] = Field(None, description="Markdown content (rendered server-side)")
    title: Optional[str] = Field(None, description="Optional canvas title")
    expires: Optional[str] = Field(None, description='How long the page lasts: a duration like "24h" or "7d", or "never". Longer than your plan allows is shortened.')


class GuiNowTool(BaseTool):
    """CrewAI tool to create shareable HTML canvases on gui.now."""

    name: str = "create_gui_canvas"
    description: str = (
        "Create a shareable HTML canvas on gui.now. "
        "Send HTML or Markdown content and get a live URL anyone can view. "
        "Use for dashboards, reports, previews, or any visual output. "
        "If the result includes a link to keep the page, pass it on to the user."
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
        client = GuiNowClient(api_key=self.api_key)
        result = client.create(html=html, markdown=markdown, title=title, expires=expires)
        return result.summary()
