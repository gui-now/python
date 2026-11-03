# gui-now

Python SDK + agent tools for [GUI](https://gui.now) — instant shareable HTML canvases.

## Install

```bash
pip install gui-now
```

With framework integrations:

```bash
pip install gui-now[langchain]
pip install gui-now[llamaindex]
pip install gui-now[crewai]
pip install gui-now[all]
```

## Quick Start

```python
from guinow import create_canvas

url = create_canvas(html="<h1>Hello World</h1>", title="My Canvas")
print(url)  # https://gui.now/abc123
```

### Keeping a page

Without an account or Pro key, a page lasts 24 hours by default (up to 72).
`create()` then also returns `claim_url`: a one-time link a person opens to
sign in and keep the page in their GUI library. If you're an agent, show it to
your user.

```python
canvas = client.create(html="<h1>Report</h1>")
print(canvas.summary())
# Canvas created: https://gui.now/abc123 (expires 2026-11-04T12:00:00.000Z)
# To keep it, open https://gui.now/claim/abc123#token=... and sign in.
```

### Full Client

```python
from guinow import GuiNowClient

client = GuiNowClient(api_key="your-pro-key")  # or set GUI_NOW_API_KEY env var
result = client.create(
    html="<h1>Dashboard</h1>",
    title="Q1 Report",
    expires="never",
)
print(result.url)
print(result.expires_at)  # None: this page never expires
```

`expires` takes a duration like `"30m"`, `"24h"` or `"7d"`, or `"never"`.
Each plan has a limit: 72 hours without an account, 7 days with a free account,
none with a Pro key. Ask for more and the API shortens it to your limit;
`result.expires_clamped` is then `True`.

Pass `agent="Claude Code"` (or set it once on the client, or `GUI_NOW_AGENT`)
to label pages with the agent that made them in the owner's library.

### Every input format

```python
client.create(html="<h1>Hi</h1>")                       # raw HTML
client.create(markdown="# Hi\n\nRendered server-side.")  # Markdown
client.create_diagram("graph TD\n  A-->B", title="Flow")  # Mermaid
client.create(frames=[                                   # multi-tab canvas
    {"html": "<h1>Overview</h1>", "label": "Overview"},
    {"html": "<h1>Detail</h1>", "label": "Detail"},
])
```

### Update and extend

`create()` returns an `edit_token`. Keep it — it is the only way to change a
canvas afterwards. Free tier allows 3 edits per canvas; Pro is unlimited.

```python
canvas = client.create(html="<h1>Draft</h1>")

client.update(canvas.id, canvas.edit_token, html="<h1>Final</h1>")
client.update(canvas.id, canvas.edit_token, title="Renamed")
client.update(canvas.id, canvas.edit_token, password=None)  # remove protection

client.extend(canvas.id)                                   # 24h from now
client.extend(canvas.id, edit_token=canvas.edit_token, expires="72h")
canvas.open()                                              # open in a browser
```

Omitting `password` leaves existing protection alone; passing `None` removes it.

`extend()` with no token adds 24 hours, but a page nobody owns can't go past
72 hours after it was made. Past that it raises `GuiNowError` with
`status == 409` and `max_expires_at` set. To choose a duration, pass the edit
token; the same plan limits apply.

Errors raise `GuiNowError`, with the HTTP status on `.status`
(`RateLimitError` for 429s).

## LangChain

```python
from guinow.langchain import GuiNowTool

tool = GuiNowTool()
# Add to your agent's tools list
agent = initialize_agent(tools=[tool], ...)
```

## LlamaIndex

```python
from guinow.llamaindex import get_guinow_tool

tool = get_guinow_tool()
agent = ReActAgent.from_tools([tool], ...)
```

## CrewAI

```python
from guinow.crewai import GuiNowTool

tool = GuiNowTool()
agent = Agent(tools=[tool], ...)
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GUI_NOW_API_KEY` | Pro API key for higher rate limits and longer expiry |
| `GUI_NOW_URL` | Override the API base URL (defaults to `https://gui.now`) |
| `GUI_NOW_AGENT` | Agent name to label pages with in the owner's library |

`GUI_NEW_API_KEY` and `GUI_NEW_URL` are the pre-rename names and are still read
as fallbacks, so keys exported before the move to gui.now keep working.

## Development

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

The tests run against a local fake of the API, using only the standard library.

## License

MIT
