"""
Admin UI routes for managing MCP servers.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from llm._logging import verbose_logger
from llm.proxy.auth.user_api_key_auth import user_api_key_auth
from llm.proxy._types import UserAPIKeyAuth, LLMUserRoles
from fastapi.templating import Jinja2Templates
import os

# Create templates instance
templates = Jinja2Templates(directory=os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
    "management_endpoints/ui_templates"
))

from .mcp_config import mcp_server_config

# Create router
router = APIRouter(
    prefix="/ui/mcp-servers",
    tags=["UI MCP Servers"],
)


class MCPServerStats(BaseModel):
    """MCP server statistics"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_duration_ms: float = 0
    average_duration_ms: float = 0
    input_tokens: int = 0
    output_tokens: int = 0


@router.get("/", response_class=HTMLResponse)
async def get_mcp_servers_ui(
    request: Request,
    user: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """Admin UI for managing MCP servers."""
    # Only admins can access this endpoint
    if user.user_role != LLMUserRoles.PROXY_ADMIN:
        return RedirectResponse(url="/ui/login")
    
    # Get all MCP servers and usage stats
    servers = mcp_server_config.get_all_servers()
    usage_stats = mcp_server_config.get_server_usage_stats()
    
    # Create a list of servers with stats
    server_list = []
    for name, config in servers.items():
        server_stats = MCPServerStats(**usage_stats.get(name, {}))
        server_list.append({
            "name": name,
            "config": config,
            "stats": server_stats,
            "is_enabled": config.get("enabled", True),
        })
    
    # Sort by name
    server_list.sort(key=lambda x: x["name"])
    
    # Render the template
    return templates.TemplateResponse(
        "mcp_servers.html",
        {
            "request": request,
            "user": user,
            "servers": server_list,
            "active_page": "mcp-servers",
        },
    )


@router.post("/enable/{server_name}")
async def enable_mcp_server(
    server_name: str,
    user: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """Enable an MCP server."""
    # Only admins can access this endpoint
    if user.user_role != LLMUserRoles.PROXY_ADMIN:
        return RedirectResponse(url="/ui/login")
    
    # Enable the server
    success = mcp_server_config.enable_server(server_name, True)
    if not success:
        return RedirectResponse(
            url=f"/ui/mcp-servers?error=Failed+to+enable+{server_name}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    
    return RedirectResponse(
        url="/ui/mcp-servers",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/disable/{server_name}")
async def disable_mcp_server(
    server_name: str,
    user: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """Disable an MCP server."""
    # Only admins can access this endpoint
    if user.user_role != LLMUserRoles.PROXY_ADMIN:
        return RedirectResponse(url="/ui/login")
    
    # Disable the server
    success = mcp_server_config.enable_server(server_name, False)
    if not success:
        return RedirectResponse(
            url=f"/ui/mcp-servers?error=Failed+to+disable+{server_name}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    
    return RedirectResponse(
        url="/ui/mcp-servers",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/update/{server_name}")
async def update_mcp_server(
    server_name: str,
    enabled: Optional[bool] = Form(None),
    env_vars: str = Form(""),
    user: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """Update an MCP server configuration."""
    # Only admins can access this endpoint
    if user.user_role != LLMUserRoles.PROXY_ADMIN:
        return RedirectResponse(url="/ui/login")
    
    # Get the server configuration
    server_config = mcp_server_config.get_server_config(server_name)
    if not server_config:
        return RedirectResponse(
            url=f"/ui/mcp-servers?error=Server+{server_name}+not+found",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    
    # Update enabled status if provided
    if enabled is not None:
        success = mcp_server_config.enable_server(server_name, enabled)
        if not success:
            return RedirectResponse(
                url=f"/ui/mcp-servers?error=Failed+to+update+{server_name}",
                status_code=status.HTTP_303_SEE_OTHER,
            )
    
    # Update environment variables if provided
    if env_vars:
        # Parse environment variables from form data
        env_vars_dict = {}
        for line in env_vars.strip().split("\n"):
            if "=" in line:
                key, value = line.split("=", 1)
                env_vars_dict[key.strip()] = value.strip()
        
        # Update server configuration
        server_config["env"] = env_vars_dict
        
        # Save the updated configuration
        try:
            import json
            import os
            
            with open(mcp_server_config.config_path, "w") as f:
                all_servers = mcp_server_config.get_all_servers()
                all_servers[server_name] = server_config
                json.dump(all_servers, f, indent=4)
        except Exception as e:
            verbose_logger.error(f"Error updating server configuration: {e}")
            return RedirectResponse(
                url=f"/ui/mcp-servers?error=Failed+to+update+{server_name}:+{str(e)}",
                status_code=status.HTTP_303_SEE_OTHER,
            )
    
    return RedirectResponse(
        url="/ui/mcp-servers",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/logs/{server_name}", response_class=HTMLResponse)
async def get_mcp_server_logs_ui(
    request: Request,
    server_name: str,
    user: UserAPIKeyAuth = Depends(user_api_key_auth),
    limit: int = 100,
):
    """View logs for an MCP server."""
    # Only admins can access this endpoint
    if user.user_role != LLMUserRoles.PROXY_ADMIN:
        return RedirectResponse(url="/ui/login")
    
    # Get server configuration and logs
    server_config = mcp_server_config.get_server_config(server_name)
    if not server_config:
        return RedirectResponse(
            url=f"/ui/mcp-servers?error=Server+{server_name}+not+found",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    
    # Get logs for this server
    logs = mcp_server_config.get_usage_logs(server_name).get(server_name, [])
    
    # Limit the logs
    logs = logs[-limit:]
    
    # Render the template
    return templates.TemplateResponse(
        "mcp_server_logs.html",
        {
            "request": request,
            "user": user,
            "server_name": server_name,
            "server_config": server_config,
            "logs": logs,
            "active_page": "mcp-servers",
        },
    )