import json
from typing import Any, Callable, Dict, List, Optional

from llm._logging import verbose_logger
from llm.proxy.types_utils.utils import get_instance_fn
from llm.types.mcp_server.tool_registry import MCPTool

# Import the MCP server configuration
from .mcp_config import mcp_server_config, MCPServerTracker


class MCPToolRegistry:
    """
    A registry for managing MCP tools
    """

    def __init__(self):
        # Registry to store all registered tools
        self.tools: Dict[str, MCPTool] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Callable,
        server_name: Optional[str] = None,
    ) -> None:
        """
        Register a new tool in the registry
        
        Args:
            name: Tool name
            description: Tool description
            input_schema: JSON schema for tool input
            handler: Function to handle tool calls
            server_name: Optional name of the server this tool belongs to
        """
        tool = MCPTool(
            name=name,
            description=description,
            input_schema=input_schema,
            handler=handler,
        )
        
        # Add server_name as an attribute to the tool
        if server_name:
            setattr(tool, "server_name", server_name)
            
        self.tools[name] = tool
        verbose_logger.debug(f"Registered tool: {name} for server: {server_name or 'default'}")

    def get_tool(self, name: str) -> Optional[MCPTool]:
        """
        Get a tool from the registry by name
        """
        return self.tools.get(name)

    def list_tools(self, server_name: Optional[str] = None) -> List[MCPTool]:
        """
        List all registered and enabled tools
        
        Args:
            server_name: Optional server name to filter tools by server
            
        Returns:
            List of enabled MCPTools
        """
        # If no server_name is provided, return all tools
        if server_name is None:
            return list(self.tools.values())
            
        # Check if the server is enabled
        server_config = mcp_server_config.get_server_config(server_name)
        if server_config is None or server_config.get("enabled", True) is False:
            verbose_logger.debug(f"Server {server_name} is disabled or not found")
            return []
            
        # Get the tools for this server
        server_tools = [tool for tool in self.tools.values() 
                        if getattr(tool, "server_name", None) == server_name]
                        
        return server_tools

    def load_tools_from_config(
        self, mcp_tools_config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Load and register tools from the proxy config

        Args:
            mcp_tools_config: The mcp_tools config from the proxy config
        """
        if mcp_tools_config is None:
            raise ValueError(
                "mcp_tools_config is required, please set `mcp_tools` in your proxy config"
            )

        for tool_config in mcp_tools_config:
            if not isinstance(tool_config, dict):
                raise ValueError("mcp_tools_config must be a list of dictionaries")

            name = tool_config.get("name")
            description = tool_config.get("description")
            input_schema = tool_config.get("input_schema", {})
            handler_name = tool_config.get("handler")

            if not all([name, description, handler_name]):
                continue

            # Try to resolve the handler
            # First check if it's a module path (e.g., "module.submodule.function")
            if handler_name is None:
                raise ValueError(f"handler is required for tool {name}")
            handler = get_instance_fn(handler_name)

            if handler is None:
                verbose_logger.warning(
                    f"Warning: Could not find handler {handler_name} for tool {name}"
                )
                continue

            # Register the tool
            if name is None:
                raise ValueError(f"name is required for tool {name}")
            if description is None:
                raise ValueError(f"description is required for tool {name}")

            self.register_tool(
                name=name,
                description=description,
                input_schema=input_schema,
                handler=handler,
            )
        verbose_logger.debug(
            "all registered tools: %s", json.dumps(self.tools, indent=4, default=str)
        )


global_mcp_tool_registry = MCPToolRegistry()
