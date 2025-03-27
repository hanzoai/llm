"""
OpenAI Agents SDK integration for MCP servers.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from llm._logging import verbose_logger
from llm.proxy.auth.user_api_key_auth import user_api_key_auth
from llm.proxy._types import UserAPIKeyAuth
from .mcp_config import mcp_server_config, MCPServerTracker
from .tool_registry import global_mcp_tool_registry

# Create router
router = APIRouter(
    prefix="/v1/functions",
    tags=["OpenAI Functions"],
)


class FunctionCallParams(BaseModel):
    """Parameters for a function call"""
    arguments: Dict[str, Any] = Field(..., description="Arguments to pass to the function")


class FunctionCallResponse(BaseModel):
    """Response from a function call"""
    content: Any = Field(..., description="Content returned by the function")
    role: str = Field("tool", description="The role of the message")
    name: str = Field(..., description="The name of the function that was called")


@router.post("/{function_name}/call", response_model=FunctionCallResponse)
async def call_function(
    function_name: str,
    params: FunctionCallParams,
    request: Request,
    user: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Call a function using the OpenAI Agents SDK format.
    
    This endpoint is compatible with the OpenAI Assistants API and allows
    function/tool calling through Hanzo MCP servers.
    """
    # Get MCP tools
    tool = global_mcp_tool_registry.get_tool(function_name)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Function '{function_name}' not found",
        )
    
    # Get the server name from the tool
    server_name = getattr(tool, "server_name", "default")
    
    # Check if this server is enabled
    server_config = mcp_server_config.get_server_config(server_name)
    if server_config and server_config.get("enabled", True) is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"MCP server '{server_name}' is disabled",
        )
    
    # Track usage
    async with MCPServerTracker(
        server_name=server_name,
        tool_name=function_name,
        user_api_key_dict=user,
    ) as tracker:
        try:
            # Add input arguments metadata
            tracker.add_metadata("arguments", params.arguments)
            
            # Call the tool handler
            result = tool.handler(**params.arguments)
            
            # Calculate rough token estimate
            result_str = str(result)
            input_tokens = len(str(params.arguments)) // 4  # Rough estimate
            output_tokens = len(result_str) // 4  # Rough estimate
            
            # Set token counts in the tracker
            tracker.set_token_counts(input_tokens, output_tokens)
            
            # Return the result in OpenAI Assistants API format
            return FunctionCallResponse(
                content=result,
                name=function_name,
            )
        except Exception as e:
            tracker.error_message = str(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error calling function '{function_name}': {str(e)}",
            )


class AvailableFunctionSchema(BaseModel):
    """Schema for a function's parameters"""
    type: str = Field("object", description="The type of the schema")
    properties: Dict[str, Dict[str, Any]] = Field(..., description="Properties of the schema")
    required: List[str] = Field(default_factory=list, description="Required properties")


class AvailableFunction(BaseModel):
    """Schema for an available function"""
    name: str = Field(..., description="Name of the function")
    description: str = Field(..., description="Description of the function")
    parameters: AvailableFunctionSchema = Field(..., description="Parameters schema for the function")


class AvailableFunctionsResponse(BaseModel):
    """Response containing all available functions"""
    functions: List[AvailableFunction] = Field(..., description="List of available functions")


@router.get("/available", response_model=AvailableFunctionsResponse)
async def get_available_functions(user: UserAPIKeyAuth = Depends(user_api_key_auth)):
    """
    Get all available functions that can be called.
    
    This endpoint is compatible with the OpenAI Assistants API and allows
    discovery of available tools from enabled MCP servers.
    """
    # Get all tools from enabled MCP servers
    all_tools = []
    for tool in global_mcp_tool_registry.list_tools():
        server_name = getattr(tool, "server_name", "default")
        
        # Skip tools from disabled servers
        server_config = mcp_server_config.get_server_config(server_name)
        if server_config and server_config.get("enabled", True) is False:
            continue
        
        # Convert MCP tool to OpenAI Assistants function format
        all_tools.append(AvailableFunction(
            name=tool.name,
            description=tool.description,
            parameters=AvailableFunctionSchema(
                properties=tool.input_schema.get("properties", {}),
                required=tool.input_schema.get("required", []),
            ),
        ))
    
    return AvailableFunctionsResponse(functions=all_tools)