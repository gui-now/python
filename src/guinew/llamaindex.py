"""LlamaIndex tool for gui.new."""

from __future__ import annotations

from typing import Optional

try:
    from llama_index.core.tools import FunctionTool
except ImportError:
    raise ImportError(
        "llama_index is required. "
        "Install with: pip install guinew[llamaindex]"
    )

from guinew.client import GuiNewClient


def _create_canvas(
    html: str = "",
    markdown: str = "",
    title: str = "",
    expires: str = "",
) -> str:
    """Create a shareable HTML canvas on gui.new.

    Args:
        html: Raw HTML content for the canvas
        markdown: Markdown content (rendered server-side). Use instead of html for text content.
        title: Optional canvas title
        expires: Expiry duration: 1h, 24h, 7d, 14d, 30d

    Returns:
        The shareable canvas URL
    """
    client = GuiNewClient()
    result = client.create(
        html=html or None,
        markdown=markdown or None,
        title=title or None,
        expires=expires or None,
    )
    return f"Canvas created: {result.url} (expires {result.expires_at})"


def get_guinew_tool() -> FunctionTool:
    """Get a LlamaIndex FunctionTool for gui.new canvas creation."""
    return FunctionTool.from_defaults(
        fn=_create_canvas,
        name="create_gui_canvas",
        description=(
            "Create a shareable HTML canvas on gui.new. "
            "Send HTML or Markdown content and get a live URL anyone can view."
        ),
    )
