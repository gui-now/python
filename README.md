# guinew

Python SDK + agent tools for [gui.new](https://gui.new) — instant shareable HTML canvases.

## Install

```bash
pip install guinew
```

With framework integrations:

```bash
pip install guinew[langchain]
pip install guinew[llamaindex]
pip install guinew[crewai]
pip install guinew[all]
```

## Quick Start

```python
from guinew import create_canvas

url = create_canvas(html="<h1>Hello World</h1>", title="My Canvas")
print(url)  # https://gui.new/abc123
```

### Full Client

```python
from guinew import GuiNewClient

client = GuiNewClient(api_key="your-pro-key")  # or set GUI_NEW_API_KEY env var
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
from guinew.langchain import GuiNewTool

tool = GuiNewTool()
# Add to your agent's tools list
agent = initialize_agent(tools=[tool], ...)
```

## LlamaIndex

```python
from guinew.llamaindex import get_guinew_tool

tool = get_guinew_tool()
agent = ReActAgent.from_tools([tool], ...)
```

## CrewAI

```python
from guinew.crewai import GuiNewTool

tool = GuiNewTool()
agent = Agent(tools=[tool], ...)
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GUI_NEW_API_KEY` | Pro API key for higher rate limits and longer expiry |

## License

MIT
