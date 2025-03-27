"""
Configuration and usage tracking for MCP servers in Hanzo AI.
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import asyncio

from llm._logging import verbose_logger
from llm.proxy._types import UserAPIKeyAuth


class MCPServerConfig:
    """Configuration for MCP servers including tracking usage"""
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        usage_log_path: Optional[str] = None
    ):
        """
        Initialize the MCP server configuration.
        
        Args:
            config_path: Path to the MCP server configuration file
            usage_log_path: Path to the MCP server usage log file
        """
        self.config_path = config_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "../../mcp_servers.json"
        )
        self.usage_log_path = usage_log_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "../../mcp_usage_logs.json"
        )
        
        # Load server configurations
        self.servers = self._load_servers()
        
        # Load usage logs
        self.usage_logs = self._load_usage_logs()
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    def _load_servers(self) -> Dict[str, Dict[str, Any]]:
        """Load MCP server configurations from file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            verbose_logger.error(f"Error loading MCP server configuration: {e}")
            return {}
    
    def _load_usage_logs(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load MCP server usage logs from file"""
        try:
            if os.path.exists(self.usage_log_path):
                with open(self.usage_log_path, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            verbose_logger.error(f"Error loading MCP server usage logs: {e}")
            return {}
    
    def _save_usage_logs(self) -> None:
        """Save MCP server usage logs to file"""
        try:
            with open(self.usage_log_path, 'w') as f:
                json.dump(self.usage_logs, f, indent=4)
        except Exception as e:
            verbose_logger.error(f"Error saving MCP server usage logs: {e}")
    
    def get_server_config(self, server_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific MCP server.
        
        Args:
            server_name: Name of the MCP server
            
        Returns:
            Server configuration or None if not found
        """
        return self.servers.get(server_name)
    
    def get_all_servers(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all MCP server configurations.
        
        Returns:
            Dictionary of server configurations
        """
        return self.servers
    
    def get_enabled_servers(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all enabled MCP server configurations.
        
        Returns:
            Dictionary of enabled server configurations
        """
        return {
            name: config for name, config in self.servers.items()
            if config.get("enabled", True)
        }
    
    def enable_server(self, server_name: str, enabled: bool = True) -> bool:
        """
        Enable or disable an MCP server.
        
        Args:
            server_name: Name of the MCP server
            enabled: Whether to enable or disable the server
            
        Returns:
            True if successful, False otherwise
        """
        if server_name not in self.servers:
            return False
        
        # Update the server configuration
        self.servers[server_name]["enabled"] = enabled
        
        # Save the updated configuration
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.servers, f, indent=4)
            return True
        except Exception as e:
            verbose_logger.error(f"Error saving MCP server configuration: {e}")
            return False
    
    async def track_usage(
        self,
        server_name: str,
        tool_name: str,
        user_api_key_dict: Optional[UserAPIKeyAuth] = None,
        duration_ms: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track usage of an MCP server.
        
        Args:
            server_name: Name of the MCP server
            tool_name: Name of the tool being used
            user_api_key_dict: User API key information
            duration_ms: Duration of the request in milliseconds
            success: Whether the request was successful
            error_message: Error message if the request failed
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            extra_metadata: Additional metadata to include in the log
        """
        async with self._lock:
            # Create a usage log entry
            entry = {
                "timestamp": datetime.now().isoformat(),
                "server_name": server_name,
                "tool_name": tool_name,
                "duration_ms": duration_ms,
                "success": success,
            }
            
            # Add user information if available
            if user_api_key_dict:
                entry["user_id"] = user_api_key_dict.user_id
                entry["team_id"] = user_api_key_dict.team_id
                entry["end_user_id"] = user_api_key_dict.end_user_id
            
            # Add error message if available
            if error_message:
                entry["error_message"] = error_message
            
            # Add token counts if available
            if input_tokens is not None:
                entry["input_tokens"] = input_tokens
            if output_tokens is not None:
                entry["output_tokens"] = output_tokens
            
            # Add extra metadata if available
            if extra_metadata:
                entry["metadata"] = extra_metadata
            
            # Add the entry to the usage logs
            if server_name not in self.usage_logs:
                self.usage_logs[server_name] = []
            self.usage_logs[server_name].append(entry)
            
            # Save the updated usage logs
            self._save_usage_logs()
    
    def get_usage_logs(self, server_name: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get usage logs for MCP servers.
        
        Args:
            server_name: Name of the MCP server to get logs for, or None for all servers
            
        Returns:
            Dictionary of usage logs
        """
        if server_name:
            return {server_name: self.usage_logs.get(server_name, [])}
        return self.usage_logs
    
    def get_server_usage_stats(self, server_name: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get usage statistics for MCP servers.
        
        Args:
            server_name: Name of the MCP server to get stats for, or None for all servers
            
        Returns:
            Dictionary of usage statistics
        """
        stats = {}
        
        servers = [server_name] if server_name else self.usage_logs.keys()
        
        for srv in servers:
            if srv not in self.usage_logs:
                continue
            
            logs = self.usage_logs[srv]
            total_calls = len(logs)
            successful_calls = sum(1 for log in logs if log.get("success", False))
            failed_calls = total_calls - successful_calls
            
            # Calculate total and average duration
            durations = [log.get("duration_ms", 0) for log in logs if "duration_ms" in log]
            total_duration = sum(durations)
            avg_duration = total_duration / len(durations) if durations else 0
            
            # Count total tokens
            input_tokens = sum(log.get("input_tokens", 0) for log in logs if "input_tokens" in log)
            output_tokens = sum(log.get("output_tokens", 0) for log in logs if "output_tokens" in log)
            
            # Get tool usage statistics
            tool_stats = {}
            for log in logs:
                tool_name = log.get("tool_name", "unknown")
                if tool_name not in tool_stats:
                    tool_stats[tool_name] = {"count": 0, "success": 0, "failure": 0}
                
                tool_stats[tool_name]["count"] += 1
                if log.get("success", False):
                    tool_stats[tool_name]["success"] += 1
                else:
                    tool_stats[tool_name]["failure"] += 1
            
            stats[srv] = {
                "total_calls": total_calls,
                "successful_calls": successful_calls,
                "failed_calls": failed_calls,
                "total_duration_ms": total_duration,
                "average_duration_ms": avg_duration,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "tools": tool_stats,
            }
        
        return stats


# Create a global instance of the MCP server configuration
mcp_server_config = MCPServerConfig()


class MCPServerTracker:
    """Context manager for tracking MCP server usage"""
    
    def __init__(
        self, 
        server_name: str,
        tool_name: str,
        user_api_key_dict: Optional[UserAPIKeyAuth] = None,
        config: Optional[MCPServerConfig] = None
    ):
        """
        Initialize the MCP server tracker.
        
        Args:
            server_name: Name of the MCP server
            tool_name: Name of the tool being used
            user_api_key_dict: User API key information
            config: MCP server configuration
        """
        self.server_name = server_name
        self.tool_name = tool_name
        self.user_api_key_dict = user_api_key_dict
        self.config = config or mcp_server_config
        self.start_time = None
        self.success = False
        self.error_message = None
        self.input_tokens = None
        self.output_tokens = None
        self.extra_metadata = {}
    
    async def __aenter__(self):
        """Start tracking MCP server usage"""
        self.start_time = time.time() * 1000  # Convert to milliseconds
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Stop tracking MCP server usage"""
        end_time = time.time() * 1000  # Convert to milliseconds
        duration_ms = end_time - self.start_time if self.start_time else None
        
        self.success = exc_type is None
        if exc_val:
            self.error_message = str(exc_val)
        
        await self.config.track_usage(
            server_name=self.server_name,
            tool_name=self.tool_name,
            user_api_key_dict=self.user_api_key_dict,
            duration_ms=duration_ms,
            success=self.success,
            error_message=self.error_message,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            extra_metadata=self.extra_metadata
        )
    
    def set_token_counts(self, input_tokens: int, output_tokens: int) -> None:
        """
        Set token counts for the MCP server usage.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        """
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
    
    def add_metadata(self, key: str, value: Any) -> None:
        """
        Add metadata to the MCP server usage.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.extra_metadata[key] = value