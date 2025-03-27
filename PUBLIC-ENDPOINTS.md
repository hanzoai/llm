# Hanzo AI Public Endpoints

Hanzo AI provides several public endpoints that allow users to browse available models and MCP servers without authentication.

## Model Endpoint

### `/models`

This endpoint displays a list of all available models through Hanzo AI with their pricing and capabilities.

Features:
- Search for models by name
- Filter by provider (OpenAI, Anthropic, etc.)
- Filter by type (chat, embedding, image generation, etc.)
- View context window sizes
- See input and output token pricing
- View model capabilities (function calling, vision, etc.)

## MCP Servers Endpoint

### `/mcps`

This endpoint displays a list of all available Model Calling Protocol (MCP) servers that can be used with Hanzo AI.

Features:
- Search for MCP servers by name
- View launch commands for each server
- See required environment variables
- Instructions for using MCP servers with Hanzo AI

## MCP Server Management

### `/mcp/admin/*`

These admin endpoints allow administrators to manage MCP servers:

- `GET /mcp/admin/servers` - List all MCP servers
- `GET /mcp/admin/servers/{server_name}` - Get server configuration
- `PATCH /mcp/admin/servers/{server_name}` - Update server configuration
- `GET /mcp/admin/usage` - Get usage statistics
- `GET /mcp/admin/usage/logs` - Get detailed usage logs

These endpoints require admin authentication.

### Configuration and Usage Tracking

MCP servers are now tracked for usage, allowing administrators to:

1. Enable/disable specific MCP servers
2. Track token usage per server
3. Monitor performance metrics
4. Analyze usage patterns
5. Control costs associated with MCP servers

Usage data is stored in `/mcp_usage_logs.json` and includes:
- Timestamp
- Server name
- Tool name
- Duration
- Success/failure status
- User information
- Token counts

## OpenAI Agents SDK Integration

Hanzo AI now provides full compatibility with the OpenAI Agents SDK for using MCP servers:

### `/v1/functions/available`

- Returns a list of all available functions from enabled MCP servers
- Compatible with OpenAI Assistants API format
- Requires authentication

### `/v1/functions/{function_name}/call`

- Calls an MCP server function with provided arguments
- Returns results in the format expected by OpenAI Assistants API
- Tracks usage for cost management
- Requires authentication

### Configuration

MCP servers can be configured in multiple ways:

1. **Config.yaml**: Configure MCP servers in your proxy configuration file:
   ```yaml
   mcp_servers:
     brave_search:
       command: "docker"
       args: ["run", "-i", "--rm", "-e", "BRAVE_API_KEY", "mcp/brave-search"]
       env:
         BRAVE_API_KEY: "YOUR_API_KEY_HERE"
       enabled: true
   ```

2. **Admin UI**: Configure and monitor MCP servers through the admin UI at `/ui/mcp-servers`

3. **API**: Use the admin API endpoints at `/mcp/admin/servers` to programmatically manage servers

## Scraping MCP Servers

Hanzo AI provides a script to scrape MCP server information from various sources and update the `mcp_servers.json` file.

### Usage

```bash
# Run the script with default output path
./scripts/scrape_mcp_servers.py

# Specify a custom output path
./scripts/scrape_mcp_servers.py --output /path/to/output.json
```

### What the Script Does

1. Scrapes MCP server information from glama.ai
2. Searches GitHub repositories for MCP server definitions
3. Searches NPM packages for MCP servers
4. Merges new server information with existing servers
5. Adds example servers if no new servers are found

### Adding New MCP Servers Manually

You can manually add new MCP servers to the `mcp_servers.json` file. Each server should have the following structure:

```json
{
    "server_name": {
        "command": "docker",
        "args": [
            "run",
            "-i",
            "--rm",
            "-e",
            "API_KEY_ENV_VAR",
            "mcp/server-image"
        ],
        "env": {
            "API_KEY_ENV_VAR": "YOUR_API_KEY_HERE"
        }
    }
}
```

### Using MCP Servers in Your Application

```python
import llm
from llm.experimental_mcp_client import MCPClient

client = MCPClient(
    api_key="your_hanzo_api_key",
    base_url="https://api.hanzo.ai"
)

result = client.run_tool(
    name="brave-search",
    params={"query": "latest AI developments"}
)
print(result)
```