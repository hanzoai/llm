"""
Admin routes for MCP servers.
"""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from llm._logging import verbose_logger
from llm.proxy.auth.user_api_key_auth import user_api_key_auth
from llm.proxy._types import UserAPIKeyAuth, LLMUserRoles
from .mcp_config import mcp_server_config
from .config_mapping import update_database_config

# Create routers
router = APIRouter(
    prefix="/mcp/admin",
    tags=["mcp-admin"],
)

# Create a public router for accessing MCP info without authentication
public_router = APIRouter(
    prefix="/api/mcps",
    tags=["mcp-public"],
)


class MCPServerConfigModel(BaseModel):
    """Config model for MCP servers"""
    name: str
    enabled: bool = True
    command: str
    args: List[str]
    env: Dict[str, str]


class MCPServerUpdateModel(BaseModel):
    """Update model for MCP servers"""
    enabled: Optional[bool] = None
    env: Optional[Dict[str, str]] = None


@router.get("/servers", response_model=Dict[str, MCPServerConfigModel])
async def get_servers(
    user: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Get all MCP server configurations.
    """
    # Only admins can access this endpoint
    if user.user_role != LLMUserRoles.PROXY_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can access MCP server configurations",
        )
    
    servers = mcp_server_config.get_all_servers()
    return {name: MCPServerConfigModel(name=name, **config) for name, config in servers.items()}


@router.get("/servers/{server_name}", response_model=MCPServerConfigModel)
async def get_server(
    server_name: str,
    user: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Get configuration for a specific MCP server.
    """
    # Only admins can access this endpoint
    if user.user_role != LLMUserRoles.PROXY_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can access MCP server configurations",
        )
    
    server_config = mcp_server_config.get_server_config(server_name)
    if not server_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server '{server_name}' not found",
        )
    
    return MCPServerConfigModel(name=server_name, **server_config)


@router.patch("/servers/{server_name}", response_model=MCPServerConfigModel)
async def update_server(
    server_name: str,
    update_data: MCPServerUpdateModel,
    user: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Update configuration for a specific MCP server.
    """
    # Only admins can access this endpoint
    if user.user_role != LLMUserRoles.PROXY_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can update MCP server configurations",
        )
    
    server_config = mcp_server_config.get_server_config(server_name)
    if not server_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server '{server_name}' not found",
        )
    
    # Update enabled status and environment variables
    env_vars = update_data.env if update_data.env is not None else None
    enabled = update_data.enabled if update_data.enabled is not None else server_config.get("enabled", True)
    
    # Update the database configuration
    success = update_database_config(
        server_name=server_name,
        enabled=enabled,
        env_vars=env_vars
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update MCP server '{server_name}'",
        )
    
    # Get updated server config
    updated_config = mcp_server_config.get_server_config(server_name)
    return MCPServerConfigModel(name=server_name, **updated_config)


@router.get("/usage")
async def get_usage_stats(
    server_name: Optional[str] = None,
    user: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Get usage statistics for MCP servers.
    """
    # Only admins can access this endpoint
    if user.user_role != LLMUserRoles.PROXY_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can access MCP server usage statistics",
        )
    
    # Get usage statistics
    usage_stats = mcp_server_config.get_server_usage_stats(server_name)
    return usage_stats


@router.get("/usage/logs")
async def get_usage_logs(
    server_name: Optional[str] = None,
    limit: int = 100,
    user: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Get usage logs for MCP servers.
    """
    # Only admins can access this endpoint
    if user.user_role != LLMUserRoles.PROXY_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can access MCP server usage logs",
        )
    
    # Get usage logs
    usage_logs = mcp_server_config.get_usage_logs(server_name)
    
    # Limit the number of logs returned
    for server, logs in usage_logs.items():
        usage_logs[server] = logs[-limit:] if len(logs) > limit else logs
    
    return usage_logs


@public_router.get("/", response_model=Dict[str, MCPServerConfigModel])
async def get_public_servers():
    """
    Get all enabled MCP server configurations for public view.
    This endpoint is public and does not require authentication.
    """
    # Get only enabled servers for public view
    servers = mcp_server_config.get_enabled_servers()
    return {name: MCPServerConfigModel(name=name, **config) for name, config in servers.items()}