# guinow

Python SDK + agent tools for [gui.now](https://gui.now) — instant shareable HTML canvases.

## Install

```bash
pip install guinow
```

With framework integrations:

```bash
pip install guinow[langchain]
pip install guinow[llamaindex]
pip install guinow[crewai]
pip install guinow[all]
```

## Quick Start

```python
from guinow import create_canvas

url = create_canvas(html="<h1>Hello World</h1>", title="My Canvas")
print(url)  # https://gui.now/abc123
```

### Full Client

```python
from guinow import GuiNowClient

client = GuiNowClient(api_key="your-pro-key")  # or set GUI_NOW_API_KEY env var
result = client.create(
    html="<h1>Dashboard</h1>",
    title="Q1 Report",
    expires="7d",
)
print(result.url)
print(result.expires_at)
```

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

client.extend(canvas.id)   # push expiry to 24h from now
canvas.open()              # open the URL in a browser
```

Omitting `password` leaves existing protection alone; passing `None` removes it.

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

`GUI_NEW_API_KEY` and `GUI_NEW_URL` are the pre-rename names and are still read
as fallbacks, so keys exported before the move to gui.now keep working.

## License

MIT
