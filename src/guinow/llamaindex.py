"""LlamaIndex tool for gui.now."""

from __future__ import annotations

from typing import Optional

try:
    from llama_index.core.tools import FunctionTool
except ImportError:
    raise ImportError(
        "llama_index is required. "
        "Install with: pip install gui-now[llamaindex]"
    )

from guinow.client import GuiNowClient


def _create_canvas(
    html: str = "",
    markdown: str = "",
    title: str = "",
    expires: str = "",
) -> str:
    """Create a shareable HTML canvas on gui.now.

    Args:
        html: Raw HTML content for the canvas
        markdown: Markdown content (rendered server-side). Use instead of html for text content.
        title: Optional canvas title
        expires: How long the page lasts: a duration like "24h" or "7d", or "never". Longer than your plan allows is shortened.

    Returns:
        The shareable canvas URL, its expiry, and a link to keep the page when there is one (pass that link on to the user)
    """
    client = GuiNowClient()
    result = client.create(
        html=html or None,
        markdown=markdown or None,
        title=title or None,
        expires=expires or None,
    )
    return result.summary()


def get_guinow_tool() -> FunctionTool:
    """Get a LlamaIndex FunctionTool for gui.now canvas creation."""
    return FunctionTool.from_defaults(
        fn=_create_canvas,
        name="create_gui_canvas",
        description=(
            "Create a shareable HTML canvas on gui.now. "
            "Send HTML or Markdown content and get a live URL anyone can view."
        ),
    )
