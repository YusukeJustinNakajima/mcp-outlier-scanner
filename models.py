#!/usr/bin/env python3
"""
Data models for MCP outlier scanner
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class MCPTool:
    """Represents an MCP tool"""
    name: str
    description: str
    server_name: str
    input_schema: Optional[Dict[str, Any]] = None
    
    def __str__(self):
        return f"{self.name}: {self.description}"


@dataclass
class MCPServer:
    """Represents an MCP server configuration"""
    name: str
    command: str
    args: List[str]
    env: Dict[str, str] = field(default_factory=dict)
    tools: List[MCPTool] = field(default_factory=list)
    status: str = "unknown"
    error_message: Optional[str] = None


@dataclass
class DeviationResult:
    """Result of deviation detection"""
    tool: MCPTool
    baseline_tools: List[MCPTool]
    is_deviation: bool
    confidence: float
    reason: str
    debug_info: Optional[Dict[str, Any]] = None
