# MCP Server Types in Hanzo AI

Hanzo AI supports multiple types of MCP (Model Context Protocol) servers through different execution methods. This document explains the various ways to run MCP servers and how to configure them.

## Supported MCP Server Types

### 1. Node.js-based MCP Servers (NPX)

Most MCP servers are JavaScript/TypeScript-based and can be run using NPX:

```json
{
    "brave_search": {
        "command": "npx",
        "args": [
            "@modelcontextprotocol/server-brave-search"
        ],
        "env": {
            "BRAVE_API_KEY": "${BRAVE_API_KEY}"
        },
        "enabled": true
    }
}
```

### 2. Python-based MCP Servers (UVX)

For Python-based MCP servers, Hanzo AI uses the `uvx` command, which is a launcher that ensures proper environment isolation:

```json
{
    "hanzo_mcp": {
        "command": "uvx",
        "args": [
            "hanzo-mcp"
        ],
        "env": {},
        "enabled": true
    }
}
```

### 3. Custom Python Module MCP Servers

You can also run custom Python modules as MCP servers:

```json
{
    "custom_python_mcp": {
        "command": "python",
        "args": [
            "-m",
            "custom_mcp_module"
        ],
        "env": {},
        "enabled": false
    }
}
```

### 4. Docker-based MCP Servers

For containerized MCP servers, you can use Docker:

```json
{
    "stable_diffusion": {
        "command": "docker",
        "args": [
            "run",
            "-i",
            "--rm",
            "mcp/stable-diffusion"
        ],
        "env": {},
        "enabled": true
    }
}
```

## Environment Variables

Environment variables can be specified directly or through placeholders:

```json
"env": {
    "OPENAI_API_KEY": "${OPENAI_API_KEY}"
}
```

When using placeholders like `${OPENAI_API_KEY}`, Hanzo AI will substitute them with values from:

1. Environment variables
2. Secret manager configurations
3. UI-defined values

## Enabling/Disabling Servers

Each MCP server can be enabled or disabled using the `enabled` flag:

```json
"enabled": true  // Server will be activated on startup
"enabled": false // Server will be inactive
```

You can override these settings in the config.yaml file or through the admin UI.

## Creating Custom MCP Servers

### Python-based MCP Servers

To create a Python-based MCP server:

1. Create a package with the MCP protocol implementation
2. Install it with `pip install -e .` or publish it to PyPI
3. Configure it in Hanzo AI using the `uvx` command

Example minimal implementation:

```python
#!/usr/bin/env python3
from mcp_framework import Server, MessageType, Message
import json

server = Server()

@server.function("custom_function")
async def custom_function(params):
    # Your custom function implementation
    return {"result": "Hello, world!"}

server.start()
```

### JavaScript-based MCP Servers

For JavaScript/TypeScript MCP servers:

1. Use the MCP SDK to create your implementation
2. Publish it to npm or run it locally
3. Configure it in Hanzo AI using the `npx` command

## Advanced Configuration

For more advanced configuration options, see the full documentation at [Hanzo AI MCP Documentation](/docs/mcp.md).