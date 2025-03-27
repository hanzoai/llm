# Hanzo AI MCP Server Integration Guide

## What are MCP Servers?

Model Calling Protocol (MCP) servers enable LLMs to access external tools and resources. They follow a standardized protocol that allows them to be easily integrated with Hanzo AI.

## Setting Up MCP Servers

MCP servers can be configured in your `config.yaml` file under the `mcp_servers` section:

```yaml
mcp_servers:
  brave_search:
    command: "docker"
    args: ["run", "-i", "--rm", "-e", "BRAVE_API_KEY", "mcp/brave-search"]
    env:
      BRAVE_API_KEY: "YOUR_API_KEY_HERE"
    enabled: true
```

### Configuration Fields:

- `command`: Command to run the MCP server (usually `docker` or `npx`)
- `args`: Arguments for the command
- `env`: Environment variables required by the server
- `enabled`: Whether the server is active (true/false)

## Popular MCP Servers

### Web Search and Information Retrieval

| Server | Key Required | Description |
|--------|-------------|-------------|
| `brave_search` | Yes | Brave Search API for web search |
| `searchapi` | Yes | Comprehensive web search API |
| `google_search` | Yes | Google Custom Search API |

### Multimodal

| Server | Key Required | Description |
|--------|-------------|-------------|
| `gemini_pro_vision` | Yes | Google's Gemini Pro Vision for image analysis |
| `stable_diffusion` | No | Local image generation with Stable Diffusion |
| `dalle` | Yes | OpenAI's DALL-E for image generation |

### Web and Content

| Server | Key Required | Description |
|--------|-------------|-------------|
| `web_scraper` | No | Web scraping and content extraction |
| `pdf_reader` | No | Extract and analyze PDF content |
| `youtube_transcript` | No | Get transcripts from YouTube videos |

### Knowledge and Computation

| Server | Key Required | Description |
|--------|-------------|-------------|
| `wolfram_alpha` | Yes | Scientific computing and knowledge engine |
| `calculator` | No | Perform mathematical calculations |

### Developer Tools

| Server | Key Required | Description |
|--------|-------------|-------------|
| `github_search` | Yes | Search GitHub repositories and code |
| `code_executor` | No | Execute code in a sandboxed environment |

### Weather and Location

| Server | Key Required | Description |
|--------|-------------|-------------|
| `openweather` | Yes | Current weather and forecasts |
| `google_maps` | Yes | Location, directions, and place information |

### Financial

| Server | Key Required | Description |
|--------|-------------|-------------|
| `alpha_vantage` | Yes | Stock market data and financial indicators |

### Database

| Server | Key Required | Description |
|--------|-------------|-------------|
| `postgres_executor` | Yes | Execute SQL queries on PostgreSQL databases |

### Language and News

| Server | Key Required | Description |
|--------|-------------|-------------|
| `google_translate` | Yes | Translation between languages |
| `newsapi` | Yes | Access news articles and headlines |

## Using MCP Tools in OpenAI Assistants Format

Hanzo AI is compatible with OpenAI's Assistants API format for tool use:

```python
from openai import OpenAI

client = OpenAI(
    api_key="your_hanzo_api_key",
    base_url="https://api.hanzo.ai/v1"
)

# Create an assistant with MCP tools
assistant = client.beta.assistants.create(
    model="gpt-4-turbo",
    tools=[{
        "type": "function", 
        "function": {
            "name": "brave_search",
            "description": "Search the web using Brave Search",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    }
                },
                "required": ["query"]
            }
        }
    }]
)
```

## Troubleshooting

- Ensure that Docker is installed and running for Docker-based MCP servers
- For NPM-based servers, make sure Node.js and NPM are installed
- Check that API keys are correctly set in the environment variables
- Verify that the MCP server is enabled in your configuration
- Look for server-specific error messages in the logs

For more detailed information, refer to the main documentation.