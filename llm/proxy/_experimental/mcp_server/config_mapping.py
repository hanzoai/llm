"""
Maps between config.yaml and database settings for MCP servers.
"""
import os
import json
from typing import Dict, Any, Optional

from llm._logging import verbose_logger
from .mcp_config import mcp_server_config


def load_config_from_yaml(config: Dict[str, Any]) -> None:
    """
    Load MCP server configuration from config.yaml

    Args:
        config: The MCP server configuration from config.yaml
    """
    try:
        mcp_servers = config.get("mcp_servers", {})
        
        # Get existing servers from JSON file
        existing_servers = mcp_server_config.get_all_servers()
        
        # Update servers from config
        for server_name, server_config in mcp_servers.items():
            # Ensure server exists in JSON
            if server_name not in existing_servers:
                existing_servers[server_name] = {
                    "command": server_config.get("command", "docker"),
                    "args": server_config.get("args", []),
                    "env": server_config.get("env", {}),
                    "enabled": server_config.get("enabled", True),
                }
            else:
                # Update existing server
                existing_servers[server_name].update({
                    "command": server_config.get("command", existing_servers[server_name].get("command", "docker")),
                    "args": server_config.get("args", existing_servers[server_name].get("args", [])),
                    "env": server_config.get("env", existing_servers[server_name].get("env", {})),
                    "enabled": server_config.get("enabled", existing_servers[server_name].get("enabled", True)),
                })
        
        # Save updated servers to JSON file
        with open(mcp_server_config.config_path, "w") as f:
            json.dump(existing_servers, f, indent=4)
    except Exception as e:
        verbose_logger.error(f"Error loading MCP server configuration from config.yaml: {e}")


def get_config_for_yaml() -> Dict[str, Any]:
    """
    Get MCP server configuration for config.yaml

    Returns:
        Dictionary with MCP server configuration
    """
    try:
        # Get servers from JSON file
        servers = mcp_server_config.get_all_servers()
        
        # Convert to config.yaml format
        mcp_servers = {}
        for server_name, server_config in servers.items():
            mcp_servers[server_name] = {
                "command": server_config.get("command", "docker"),
                "args": server_config.get("args", []),
                "env": server_config.get("env", {}),
                "enabled": server_config.get("enabled", True),
            }
        
        return {"mcp_servers": mcp_servers}
    except Exception as e:
        verbose_logger.error(f"Error getting MCP server configuration for config.yaml: {e}")
        return {"mcp_servers": {}}


def load_mcp_server_configs_on_startup(config: Dict[str, Any]) -> None:
    """
    Load MCP server configuration on proxy server startup

    Args:
        config: The proxy server configuration
    """
    # First load any overrides from config.yaml
    if config and "mcp_servers" in config:
        verbose_logger.info("Loading MCP server configuration from config.yaml")
        load_config_from_yaml(config)
    else:
        verbose_logger.info("No MCP servers specified in config.yaml, using default configuration")
    
    # List enabled MCP servers
    enabled_servers = mcp_server_config.get_enabled_servers()
    if enabled_servers:
        print("\n\033[1;34mEnabled MCP Servers:\033[0m")
        for name, server_config in enabled_servers.items():
            command = server_config.get("command", "")
            args = " ".join(server_config.get("args", []))
            print(f"\033[1;32m - {name}\033[0m ({command} {args})")
    else:
        print("\n\033[1;33mNo MCP servers enabled. Check mcp_servers.json or add them to config.yaml under 'mcp_servers' section.\033[0m")


def update_database_config(server_name: str, enabled: bool, env_vars: Optional[Dict[str, str]] = None) -> bool:
    """
    Update MCP server configuration in database

    Args:
        server_name: Name of the MCP server
        enabled: Whether the server is enabled
        env_vars: Environment variables for the server

    Returns:
        True if successful, False otherwise
    """
    try:
        # Get server configuration
        server_config = mcp_server_config.get_server_config(server_name)
        if not server_config:
            return False
        
        # Update server configuration
        server_config["enabled"] = enabled
        if env_vars is not None:
            server_config["env"] = env_vars
        
        # Save the updated configuration
        all_servers = mcp_server_config.get_all_servers()
        all_servers[server_name] = server_config
        
        with open(mcp_server_config.config_path, "w") as f:
            json.dump(all_servers, f, indent=4)
        
        return True
    except Exception as e:
        verbose_logger.error(f"Error updating MCP server configuration in database: {e}")
        return False