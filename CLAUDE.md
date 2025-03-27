# Hanzo AI - MCP Server Integration

## Overview

This document outlines the changes made to integrate Model Calling Protocol (MCP) servers with Hanzo AI.

## Public Endpoints

### `/models` and `/api/models`

- Public endpoints to browse all available models
- HTML version at `/models.html` with filtering and searching
- JSON data accessible at `/models` or `/api/models` with `Accept: application/json` header
- No authentication required

### `/mcps` and `/api/mcps`

- Public endpoints to browse all available MCP servers
- HTML version at `/mcps.html` with filtering and searching
- JSON data accessible at `/mcps` or `/api/mcps` with `Accept: application/json` header
- No authentication required

## MCP Server Management

### Configuration and Usage Tracking

MCP servers can be configured in multiple ways:

1. **Config.yaml**:
```yaml
mcp_servers:
  brave_search:
    command: "docker"
    args: ["run", "-i", "--rm", "-e", "BRAVE_API_KEY", "mcp/brave-search"]
    env:
      BRAVE_API_KEY: "YOUR_API_KEY_HERE"
    enabled: true
```

2. **Admin UI**: `/ui/mcp-servers`
   - Enable/disable servers
   - Configure environment variables
   - View usage statistics
   - View detailed logs

3. **Admin API**: 
   - `GET /mcp/admin/servers` - List all servers
   - `GET /mcp/admin/servers/{server_name}` - View server configuration
   - `PATCH /mcp/admin/servers/{server_name}` - Update server configuration
   - `GET /mcp/admin/usage` - View usage statistics
   - `GET /mcp/admin/usage/logs` - View detailed logs

### Usage Tracking

- All MCP server usage is tracked in `/mcp_usage_logs.json`
- Metrics include tokens, duration, success/failure, user info
- Usage statistics available in admin UI and API
- Cost control by enabling/disabling servers

## OpenAI Agents SDK Integration

### Drop-in Replacement

Hanzo AI can be used as a drop-in replacement for OpenAI's Assistants API:

```python
from openai import OpenAI

client = OpenAI(
    api_key="your_hanzo_api_key",
    base_url="https://api.hanzo.ai/v1"
)

# Create an assistant with MCP tools
assistant = client.beta.assistants.create(
    model="gpt-4-turbo",
    tools=[{"type": "function", "function": {"name": "brave_search", ...}}]
)
```

### Function Discovery and Calling

- List available functions: `GET /v1/functions/available`
- Call functions: `POST /v1/functions/{function_name}/call`
- Compatible with OpenAI's format for tool calls

## Scraping MCP Servers

- Script to discover MCP servers: `/scripts/scrape_mcp_servers.py`
- Scrapes from GitHub, NPM, and other sources
- Updates `mcp_servers.json` with new servers

## Implementation Details

### Files Added/Modified

- `/llm/proxy/_experimental/mcp_server/mcp_config.py` - Configuration and tracking
- `/llm/proxy/_experimental/mcp_server/admin_routes.py` - Admin API endpoints
- `/llm/proxy/_experimental/mcp_server/admin_ui_routes.py` - Admin UI
- `/llm/proxy/_experimental/mcp_server/openai_agents_integration.py` - OpenAI compatibility
- `/llm/proxy/_experimental/mcp_server/config_mapping.py` - Config file mapping
- `/llm/proxy/management_endpoints/ui_templates/mcp_servers.html` - Admin UI template
- `/llm/proxy/management_endpoints/ui_templates/mcp_server_logs.html` - Logs template

### Runtime Configuration

- MCP servers can be enabled/disabled at runtime
- Environment variables can be updated without restart
- Usage is tracked in real-time