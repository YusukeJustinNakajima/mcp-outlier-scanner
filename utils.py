#!/usr/bin/env python3
"""
Common utilities for MCP outlier scanner
"""

import re
from typing import List, Set
from enum import Enum, auto

# For colored output
try:
    from colorama import init as colorama_init, Fore, Back, Style
    colorama_init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False
    # Dummy color constants if colorama not available
    class Fore:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ''
    class Style:
        BRIGHT = DIM = NORMAL = RESET_ALL = ''


class DetectionMethod(Enum):
    """Available detection methods"""
    PATTERN_ANALYSIS = auto()
    CONSISTENCY_CHECK = auto()
    CROSS_SERVER_ANALYSIS = auto()
    MULTI_APPROACH = auto()
    AI_ENHANCED = auto()


class MethodWeights:
    """Weights for different detection methods"""
    WEIGHTS = {
        DetectionMethod.PATTERN_ANALYSIS: 1.0,
        DetectionMethod.CONSISTENCY_CHECK: 1.2,
        DetectionMethod.CROSS_SERVER_ANALYSIS: 1.1,
    }
    
    @staticmethod
    def get_weight(method: DetectionMethod) -> float:
        """Get weight for a detection method"""
        return MethodWeights.WEIGHTS.get(method, 1.0)


class TextProcessor:
    """Text processing utilities"""
    
    @staticmethod
    def extract_meaningful_words(text: str) -> List[str]:
        """Extract meaningful words from text"""
        # Split by common delimiters
        words = re.split(r'[_\-\s/]+', text.lower())
        
        # Filter out very short words and common words
        common_words = {
            'the', 'a', 'an', 'to', 'from', 'with', 'for', 'and', 'or', 'but', 
            'in', 'on', 'at', 'by', 'of', 'as', 'is', 'it', 'that', 'this'
        }
        meaningful = [w for w in words if len(w) > 2 and w not in common_words]
        
        return meaningful
    
    @staticmethod
    def tokenize_camel_case(text: str) -> List[str]:
        """Split camelCase into words"""
        return re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', text)
    
    @staticmethod
    def preprocess_for_embedding(text: str) -> str:
        """Preprocess text for better embedding representation"""
        # Handle snake_case and camelCase
        processed = re.sub(r'_', ' ', text)  # Replace underscores with spaces
        processed = re.sub(r'([a-z])([A-Z])', r'\1 \2', processed)  # Split camelCase
        processed = processed.lower()
        
        return processed
