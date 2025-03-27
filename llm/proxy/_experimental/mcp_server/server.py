"""
LLM MCP Server Routes
"""

import asyncio
from typing import Any, Dict, List, Union

from anyio import BrokenResourceError
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from llm._logging import verbose_logger

# Check if MCP is available
# "mcp" requires python 3.10 or higher, but several llm users use python 3.8
# We're making this conditional import to avoid breaking users who use python 3.8.
try:
    from mcp.server import Server

    MCP_AVAILABLE = True
except ImportError as e:
    verbose_logger.debug(f"MCP module not found: {e}")
    MCP_AVAILABLE = False
    router = APIRouter(
        prefix="/mcp",
        tags=["mcp"],
    )


if MCP_AVAILABLE:
    from mcp.server import NotificationOptions, Server
    from mcp.server.models import InitializationOptions
    from mcp.types import EmbeddedResource as MCPEmbeddedResource
    from mcp.types import ImageContent as MCPImageContent
    from mcp.types import TextContent as MCPTextContent
    from mcp.types import Tool as MCPTool

    from .sse_transport import SseServerTransport
    from .tool_registry import global_mcp_tool_registry

    ########################################################
    ############ Initialize the MCP Server #################
    ########################################################
    router = APIRouter(
        prefix="/mcp",
        tags=["mcp"],
    )
    server: Server = Server("llm-mcp-server")
    sse: SseServerTransport = SseServerTransport("/mcp/sse/messages")

    ########################################################
    ############### MCP Server Routes #######################
    ########################################################

    @server.list_tools()
    async def list_tools() -> list[MCPTool]:
        """
        List all available tools
        """
        tools = []
        for tool in global_mcp_tool_registry.list_tools():
            tools.append(
                MCPTool(
                    name=tool.name,
                    description=tool.description,
                    inputSchema=tool.input_schema,
                )
            )

        return tools

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: Dict[str, Any] | None
    ) -> List[Union[MCPTextContent, MCPImageContent, MCPEmbeddedResource]]:
        """
        Call a specific tool with the provided arguments
        """
        from fastapi import Request
        from llm.proxy.proxy_server import user_api_key_auth
        
        # Get the current request to fetch user information
        request = Request(scope={})
        user_api_key_dict = None
        try:
            # This may not always succeed in the MCP context
            # but we'll try to get user info when available
            user_api_key_dict = await user_api_key_auth(request)
        except Exception:
            pass
        
        tool = global_mcp_tool_registry.get_tool(name)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
        if arguments is None:
            raise HTTPException(
                status_code=400, detail="Request arguments are required"
            )

        # Get the server name from the tool
        server_name = getattr(tool, "server_name", "default")
        
        # Check if this server is enabled
        from .mcp_config import mcp_server_config
        server_config = mcp_server_config.get_server_config(server_name)
        if server_config and server_config.get("enabled", True) is False:
            raise HTTPException(
                status_code=403, 
                detail=f"MCP server '{server_name}' is disabled"
            )
            
        # Use the tracker to log usage
        from .mcp_config import MCPServerTracker
        async with MCPServerTracker(
            server_name=server_name,
            tool_name=name,
            user_api_key_dict=user_api_key_dict
        ) as tracker:
            try:
                # Add input arguments metadata
                tracker.add_metadata("arguments", arguments)
                
                # Call the tool handler
                result = tool.handler(**arguments)
                
                # Convert result to string and calculate rough token estimate
                result_str = str(result)
                input_tokens = len(str(arguments)) // 4  # Rough estimate
                output_tokens = len(result_str) // 4  # Rough estimate
                
                # Set token counts in the tracker
                tracker.set_token_counts(input_tokens, output_tokens)
                
                return [MCPTextContent(text=result_str, type="text")]
            except Exception as e:
                tracker.error_message = str(e)
                return [MCPTextContent(text=f"Error: {str(e)}", type="text")]

    @router.get("/", response_class=StreamingResponse)
    async def handle_sse(request: Request):
        verbose_logger.info("new incoming SSE connection established")
        async with sse.connect_sse(request) as streams:
            try:
                await server.run(streams[0], streams[1], options)
            except BrokenResourceError:
                pass
            except asyncio.CancelledError:
                pass
            except ValidationError:
                pass
            except Exception:
                raise
        await request.close()

    @router.post("/sse/messages")
    async def handle_messages(request: Request):
        verbose_logger.info("incoming SSE message received")
        await sse.handle_post_message(request.scope, request.receive, request._send)
        await request.close()

    options = InitializationOptions(
        server_name="llm-mcp-server",
        server_version="0.1.0",
        capabilities=server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )
