#!/usr/bin/env python3
"""
Detector Manager - Manages and combines multiple detection methods
"""

import numpy as np
from typing import List, Dict, Any, Optional
import asyncio

from models import MCPServer, DeviationResult
from utils import DetectionMethod, MethodWeights, Fore, Style
from detectors.base_detector import BaseDetector
from detectors.consistency_detector import ConsistencyDetector
from detectors.crossserver_detector import CrossServerDetector


class DetectorManager:
    """Manages multiple detection methods and combines their results"""
    
    def __init__(self, use_ai: bool = False, api_key: Optional[str] = None, debug: bool = False):
        self.use_ai = use_ai
        self.api_key = api_key
        self.debug = debug
        self.detectors = {}
        
        # Initialize available detectors
        self._initialize_detectors()

    def _initialize_detectors(self):
        """Initialize all available detectors"""
        
        # Embedding-based detectors with LLM support
        consistency_detector = ConsistencyDetector(
            use_llm=self.use_ai, 
            api_key=self.api_key, 
            debug=self.debug
        )
        if consistency_detector.is_available():
            self.detectors[DetectionMethod.CONSISTENCY_CHECK] = consistency_detector
        
        crossserver_detector = CrossServerDetector(
            use_llm=self.use_ai,
            api_key=self.api_key,
            debug=self.debug
        )
        if crossserver_detector.is_available():
            self.detectors[DetectionMethod.CROSS_SERVER_ANALYSIS] = crossserver_detector
    
    async def run_detection(self, servers: List[MCPServer], methods: Optional[List[DetectionMethod]] = None) -> List[DeviationResult]:
        """Run detection using specified methods"""
        # Determine which methods to use
        if methods is None:
            # Default to all non-AI methods
            methods = [
                DetectionMethod.CONSISTENCY_CHECK,
                DetectionMethod.CROSS_SERVER_ANALYSIS
            ]
        
        # Handle special meta-methods
        if DetectionMethod.MULTI_APPROACH in methods:
            methods = list(self.detectors.keys())
        elif DetectionMethod.AI_ENHANCED in methods:
            # AI enhanced uses all methods plus LLM verification
            methods = list(self.detectors.keys())
            if DetectionMethod.CROSS_SERVER_LLM not in methods and self.use_ai:
                methods.append(DetectionMethod.CROSS_SERVER_LLM)
        
        # Filter to only available methods
        available_methods = [m for m in methods if m in self.detectors]
        
        if not available_methods:
            print(f"{Fore.RED}No detection methods available{Style.RESET_ALL}")
            return []
        
        # Run single method if only one selected
        if len(available_methods) == 1:
            detector = self.detectors[available_methods[0]]
            return await detector.detect(servers)
        
        # Run multiple methods and combine results
        return await self._run_multiple_methods(servers, available_methods)
    
    async def _run_multiple_methods(self, servers: List[MCPServer], methods: List[DetectionMethod]) -> List[DeviationResult]:
        """Run multiple detection methods and combine results"""
        all_results = {}
        
        # Run each method
        for method in methods:
            detector = self.detectors[method]
            method_results = await detector.detect(servers)
            weight = MethodWeights.get_weight(method)
            
            # Aggregate results by tool
            for result in method_results:
                key = (result.tool.server_name, result.tool.name)
                
                if key not in all_results:
                    all_results[key] = {
                        'tool': result.tool,
                        'baseline_tools': result.baseline_tools,
                        'scores': [],
                        'reasons': [],
                        'methods': []
                    }
                
                if result.is_deviation:
                    all_results[key]['scores'].append(result.confidence * weight)
                    all_results[key]['reasons'].append(f"{method.name}: {result.reason}")
                    all_results[key]['methods'].append(method.name)
        
        # Combine results
        final_results = []
        for key, data in all_results.items():
            if data['scores']:
                # Calculate combined confidence
                avg_confidence = np.mean(data['scores'])
                num_methods = len(data['methods'])
                
                # Boost confidence if detected by multiple methods
                if num_methods > 1:
                    avg_confidence = min(1.0, avg_confidence * (1 + 0.1 * (num_methods - 1)))
                
                is_deviation = avg_confidence >= 0.6
                
                result = DeviationResult(
                    tool=data['tool'],
                    baseline_tools=data['baseline_tools'],
                    is_deviation=is_deviation,
                    confidence=avg_confidence,
                    reason=f"Detected by {num_methods} method(s): " + "; ".join(data['reasons'])
                )
                final_results.append(result)
            else:
                # Not detected as deviation by any method
                result = DeviationResult(
                    tool=data['tool'],
                    baseline_tools=data['baseline_tools'],
                    is_deviation=False,
                    confidence=0.0,
                    reason="No deviation detected by selected methods"
                )
                final_results.append(result)
        
        return final_results
