#!/usr/bin/env python3
"""
Base detector class for all detection methods
"""

from abc import ABC, abstractmethod
from typing import List

from models import MCPServer, DeviationResult


class BaseDetector(ABC):
    """Base class for all deviation detectors"""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    @abstractmethod
    async def detect(self, servers: List[MCPServer]) -> List[DeviationResult]:
        """
        Detect deviations in MCP server tools
        
        Args:
            servers: List of scanned MCP servers
            
        Returns:
            List of deviation results
        """
        pass
