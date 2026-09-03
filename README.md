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

## License

MIT
