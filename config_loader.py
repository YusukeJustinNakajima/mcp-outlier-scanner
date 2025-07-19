#!/usr/bin/env python3
"""
Configuration loader for Claude Desktop MCP servers
"""

import os
import json
import platform
from pathlib import Path
from typing import List, Dict, Any

from models import MCPServer


class MCPConfigLoader:
    """Load and parse Claude Desktop MCP configuration"""
    
    @staticmethod
    def get_config_path() -> Path:
        """Get the Claude Desktop config file path based on OS"""
        system = platform.system()
        
        if system == "Windows":
            base_path = os.environ.get('APPDATA', '')
            if not base_path:
                base_path = Path.home() / "AppData" / "Roaming"
            else:
                base_path = Path(base_path)
        elif system == "Darwin":  # macOS
            base_path = Path.home() / "Library" / "Application Support"
        else:  # Linux
            base_path = Path.home() / ".config"
        
        return base_path / "Claude" / "claude_desktop_config.json"
    
    @staticmethod
    def load_config() -> Dict[str, Any]:
        """Load the Claude Desktop configuration"""
        config_path = MCPConfigLoader.get_config_path()
        
        if not config_path.exists():
            raise FileNotFoundError(f"Claude Desktop config not found at: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def parse_servers(config: Dict[str, Any]) -> List[MCPServer]:
        """Parse MCP servers from configuration"""
        servers = []
        mcp_servers = config.get('mcpServers', {})
        
        for name, server_config in mcp_servers.items():
            server = MCPServer(
                name=name,
                command=server_config.get('command', ''),
                args=server_config.get('args', []),
                env=server_config.get('env', {})
            )
            servers.append(server)
        
        return servers
