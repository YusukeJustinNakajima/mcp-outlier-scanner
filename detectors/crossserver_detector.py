#!/usr/bin/env python3
"""
Cross-server analysis detector using embeddings and LLM
"""

import os
import json
import asyncio
import numpy as np
from typing import List, Dict, Tuple, Optional, Any

from models import MCPServer, DeviationResult
from detectors.base_detector import BaseDetector
from utils import TextProcessor, Fore, Style

# For embedding-based approaches
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False

# For LLM-based approaches
try:
    import openai
except ImportError:
    openai = None


class CrossServerDetector(BaseDetector):
    """Analyze tools across multiple servers using embeddings and LLM"""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', 
                 use_llm: bool = False, api_key: Optional[str] = None,
                 debug: bool = False):
        super().__init__(debug)
        
        # Embedding model
        if EMBEDDINGS_AVAILABLE:
            self.model = SentenceTransformer(model_name)
        else:
            self.model = None
        
        # LLM configuration
        self.use_llm = use_llm and openai is not None
        if self.use_llm and api_key:
            openai.api_key = api_key
        elif self.use_llm and not api_key:
            # Check environment variable
            api_key = os.environ.get('OPENAI_API_KEY')
            if api_key:
                openai.api_key = api_key
            else:
                if debug:
                    print(f"{Fore.YELLOW}Warning: LLM requested but no API key provided{Style.RESET_ALL}")
                self.use_llm = False
    
    def is_available(self) -> bool:
        """Check if cross-server analysis is available"""
        return self.model is not None or self.use_llm
    
    async def detect(self, servers: List[MCPServer]) -> List[DeviationResult]:
        """Detect tools that might belong to a different server"""
        if not self.is_available():
            print("Warning: CrossServerDetector requires sentence-transformers or OpenAI API")
            return []
        
        results = []
        
        # Build server data
        servers_data = {}
        for server in servers:
            if server.status == "scanned" and server.tools:
                servers_data[server.name] = [(t.name, t.description) for t in server.tools]
        
        # Build embedding profiles if available
        server_profiles = {}
        if self.model:
            server_profiles = self.build_server_profiles(servers_data)
        
        # Prepare LLM profiles if available
        server_profiles_text = {}
        if self.use_llm:
            server_profiles_text = self.prepare_server_profiles_for_llm(servers_data)
        
        # Check each tool
        for server in servers:
            if server.status != "scanned" or not server.tools:
                continue
            
            for tool in server.tools:
                embed_score = 0.0
                llm_score = 0.0
                embed_reasons = []
                llm_reasons = []
                
                # 1. Embedding-based cross-server analysis (if available)
                if self.model and server_profiles:
                    embed_score, embed_reasons = self.check_cross_server_fit(
                        tool.name, tool.description, server.name, server_profiles
                    )
                
                # 2. LLM-based cross-server analysis (if available)
                if self.use_llm and server_profiles_text:
                    try:
                        llm_score, llm_reasons = await self.check_cross_server_fit_with_llm(
                            tool.name, tool.description, server.name, server_profiles_text
                        )
                    except Exception as e:
                        if self.debug:
                            print(f"{Fore.RED}[DEBUG] LLM cross-server check failed: {e}{Style.RESET_ALL}")
                
                # Take the maximum of embedding and LLM scores
                deviation_score = max(embed_score, llm_score)
                
                # Format reasons in a structured way
                formatted_reasons = []

                # Add score summary
                if embed_score > 0 or llm_score > 0:
                    if self.use_llm:
                        # Both methods available - show both scores
                        formatted_reasons.append(f"📊 Detection Scores - Embedding: {embed_score:.2f}, LLM: {llm_score:.2f} (Max: {deviation_score:.2f})")
                    elif self.model:
                        # Only embedding available
                        formatted_reasons.append(f"📊 Detection Score - Embedding: {deviation_score:.2f}")
                    else:
                        # Only LLM available (rare case)
                        formatted_reasons.append(f"📊 Detection Score - LLM: {deviation_score:.2f}")

                # Check for significant score difference (potential FP) - only when both methods are used
                if self.use_llm and self.model:
                    score_diff = abs(embed_score - llm_score)
                    if score_diff >= 0.5 and (embed_score > 0 or llm_score > 0):
                        formatted_reasons.append(f"⚠️  WARNING: High score difference ({score_diff:.2f}) - Potential False Positive")

                # Add embedding reasons if any
                if embed_reasons:
                    if self.use_llm:
                        formatted_reasons.append("🔍 Embedding Analysis:")
                    else:
                        formatted_reasons.append("🔍 Analysis:")
                    for reason in embed_reasons:
                        formatted_reasons.append(f"  • {reason}")

                # Add LLM reasons if any
                if llm_reasons:
                    formatted_reasons.append("🤖 LLM Analysis:")
                    for reason in llm_reasons:
                        formatted_reasons.append(f"  • {reason}")
                
                is_deviation = deviation_score >= 0.6
                
                # Join reasons with newlines for better readability
                final_reason = "\n".join(formatted_reasons) if formatted_reasons else "Fits well with current server"
                
                results.append(DeviationResult(
                    tool=tool,
                    baseline_tools=[t for t in server.tools if t != tool],
                    is_deviation=is_deviation,
                    confidence=deviation_score,
                    reason=final_reason
                ))
        
        return results
    
    def build_server_profiles(self, servers_data: Dict[str, List[tuple]]) -> Dict[str, np.ndarray]:
        """Build embedding profiles for each server including server name context"""
        if not self.model:
            return {}
        
        server_profiles = {}
        
        for server_name, tools in servers_data.items():
            if not tools:
                continue
            
            # Preprocess server name
            server_name_processed = TextProcessor.preprocess_for_embedding(server_name)
            
            # Create embeddings for all tools in the server with server context
            tool_embeddings = []
            
            # First, add server name embedding with higher weight
            server_embedding = self.model.encode(server_name)
            # Add server embedding multiple times to give it more weight in the centroid
            for _ in range(3):  # Weight factor of 3 for server name
                tool_embeddings.append(server_embedding)
            
            # Then add tool embeddings with server context
            for name, desc in tools:
                # Use same preprocessing
                name_processed = TextProcessor.preprocess_for_embedding(name)
                desc_processed = TextProcessor.preprocess_for_embedding(desc)
                
                # Include server context in tool text
                tool_text = f"In {server_name_processed} server: {name_processed}: {desc_processed}"
                embedding = self.model.encode(tool_text)
                tool_embeddings.append(embedding)
            
            # Server profile is the centroid of server context + all its tools
            if tool_embeddings:
                server_profile = np.mean(tool_embeddings, axis=0)
                server_profiles[server_name] = server_profile
        
        return server_profiles
    
    def prepare_server_profiles_for_llm(self, servers_data: Dict[str, List[tuple]]) -> Dict[str, Dict[str, Any]]:
        """Prepare simplified server profiles for LLM analysis"""
        server_profiles = {}
        
        for server_name, tools in servers_data.items():
            if not tools:
                continue
            
            # Minimal profile with just essential information
            profile = {
                'server_name': server_name,
                'tool_count': len(tools),
                'tools': [{'name': name, 'description': desc} for name, desc in tools]
            }
            
            server_profiles[server_name] = profile
        
        return server_profiles
    
    def check_cross_server_fit(self, tool_name: str, tool_desc: str, current_server: str,
                              server_profiles: Dict[str, np.ndarray]) -> Tuple[float, List[str]]:
        """Check if a tool fits better with another server using embedding-based approach only"""
        if not self.model or not server_profiles:
            return 0.0, ["Embedding model not available"]
        
        deviation_score = 0.0
        reasons = []
        
        # Preprocess and create tool embedding
        name_processed = TextProcessor.preprocess_for_embedding(tool_name)
        desc_processed = TextProcessor.preprocess_for_embedding(tool_desc)
            
        tool_text = f"{name_processed}: {desc_processed}"
        tool_embedding = self.model.encode(tool_text)
        
        # Calculate similarity with each server profile
        server_similarities = {}
        for server_name, server_profile in server_profiles.items():
            similarity = self._cosine_similarity(tool_embedding, server_profile)
            server_similarities[server_name] = similarity
        
        if not server_similarities:
            return 0.0, ["No server profiles available"]
        
        # Get current server similarity
        current_similarity = server_similarities.get(current_server, 0)
        
        # Find best fitting server
        best_server = max(server_similarities, key=server_similarities.get)
        best_similarity = server_similarities[best_server]
        
        # Single focused check: Does the tool fit significantly better elsewhere?
        if best_server != current_server and best_similarity > current_similarity:
            fit_difference = best_similarity - current_similarity
            
            if fit_difference > 0.3 and best_similarity > 0.6:
                # Strong indication of better fit elsewhere
                deviation_score = 0.8
                reasons.append(f"Tool has stronger semantic alignment with '{best_server}' (similarity: {best_similarity:.2f} vs current: {current_similarity:.2f})")
            elif fit_difference > 0.2 and best_similarity > 0.5:
                # Moderate indication
                deviation_score = 0.6
                reasons.append(f"Tool shows better semantic fit with '{best_server}' ({best_similarity:.2f} vs current: {current_similarity:.2f})")
            elif fit_difference > 0.15 and best_similarity > 0.4:
                # Weak indication
                deviation_score = 0.4
                reasons.append(f"Tool has slightly better alignment with '{best_server}' ({best_similarity:.2f} vs current: {current_similarity:.2f})")
        
        return deviation_score, reasons
    
    async def check_cross_server_fit_with_llm(self, tool_name: str, tool_desc: str, 
                                            current_server: str, server_profiles: Dict[str, Dict[str, Any]]) -> Tuple[float, List[str]]:
        """Check cross-server fit using LLM analysis"""
        prompt = self.generate_llm_cross_server_prompt(tool_name, tool_desc, current_server, server_profiles)
        
        try:
            response = await self._call_openai(prompt)
            result = json.loads(response)
            
            # Calculate deviation score from LLM analysis
            deviation_score = 0.0
            reasons = []
            
            # Get fit scores
            current_fit = result['current_server_fit']
            best_server = result['best_fitting_server']
            best_fit = result['best_server_fit']
            
            # Check if current server fit is poor (absolute threshold)
            if current_fit < 0.3:
                deviation_score += 0.5
                reasons.append(f"Very poor fit with current server (LLM: {current_fit:.2f})")
            elif current_fit < 0.5:
                deviation_score += 0.3
                reasons.append(f"Poor fit with current server (LLM: {current_fit:.2f})")
            
            # Check fit difference with ±0.2 threshold
            if best_server != current_server:
                fit_difference = best_fit - current_fit
                
                if self.debug:
                    print(f"{Fore.YELLOW}Fit comparison: {best_server} ({best_fit:.2f}) vs {current_server} ({current_fit:.2f}), difference: {fit_difference:.2f}{Style.RESET_ALL}")
                
                # If another server fits better by 0.2 or more
                if fit_difference >= 0.2:
                    if fit_difference >= 0.5:
                        deviation_score += 0.8
                        reasons.append(
                            f"Much better fit with '{best_server}' "
                            f"(LLM: {best_fit:.2f} vs {current_fit:.2f}, diff: +{fit_difference:.2f})"
                        )
                    elif fit_difference >= 0.3:
                        deviation_score += 0.6
                        reasons.append(
                            f"Better fit with '{best_server}' "
                            f"(LLM: {best_fit:.2f} vs {current_fit:.2f}, diff: +{fit_difference:.2f})"
                        )
                    else:  # fit_difference >= 0.2
                        deviation_score += 0.4
                        reasons.append(
                            f"Slightly better fit with '{best_server}' "
                            f"(LLM: {best_fit:.2f} vs {current_fit:.2f}, diff: +{fit_difference:.2f})"
                        )
            
            # Check if current server fits significantly better than others
            elif best_server == current_server:
                # Check other servers
                for other_result in result.get('other_high_fit_servers', []):
                    other_fit = other_result['fit']
                    fit_difference = current_fit - other_fit
                    
                    # If current server is NOT significantly better (less than 0.2 difference)
                    if fit_difference < 0.2:
                        deviation_score += 0.3
                        reasons.append(
                            f"Current server '{current_server}' is not significantly better than '{other_result['server']}' "
                            f"(diff: +{fit_difference:.2f})"
                        )
            
            # Check other high fit servers (alternative fits)
            if result.get('other_high_fit_servers'):
                for other_server in result['other_high_fit_servers']:
                    other_fit = other_server['fit']
                    fit_difference_from_current = other_fit - current_fit
                    
                    # If another server also fits well (within 0.2 threshold)
                    if fit_difference_from_current >= -0.2 and other_fit >= 0.6:
                        if best_server != other_server['server']:  # Don't double count
                            deviation_score += 0.2
                            reasons.append(
                                f"Also fits well with '{other_server['server']}' "
                                f"(LLM: {other_fit:.2f}, diff from current: {fit_difference_from_current:+.2f})"
                            )
            
            # Direct suspicious flag from LLM
            if result.get('is_suspicious', False):
                deviation_score += 0.4
                reasons.append("LLM flags tool as suspicious")
            
            # Add reasoning if available
            if result.get('reasoning'):
                # Only add if we have other reasons (to avoid cluttering non-deviations)
                if reasons:
                    reasons.append(f"Analysis: {result['reasoning']}")
            
            # Apply LLM confidence to the score
            llm_confidence = result.get('confidence', 1.0)
            deviation_score = min(deviation_score * llm_confidence, 1.0)
            
            return deviation_score, reasons
            
        except Exception as e:
            if self.debug:
                print(f"{Fore.RED}[DEBUG] LLM call failed: {e}{Style.RESET_ALL}")
            return 0.0, [f"LLM analysis failed: {str(e)}"]
    
    def generate_llm_cross_server_prompt(self, tool_name: str, tool_desc: str, 
                                       current_server: str, server_profiles: Dict[str, Dict[str, Any]]) -> str:
        """Generate simplified prompt for LLM to analyze cross-server fit"""
        # Format server profiles simply
        server_summaries = []
        for server_name, profile in server_profiles.items():
            summary = f"**{server_name}** ({profile['tool_count']} tools)"
            
            # Show a few representative tools
            if profile['tools']:
                summary += "\n  Example tools:"
                # Show up to 5 diverse examples
                examples = profile['tools']
                if len(examples) > 5:
                    # Pick evenly distributed examples
                    indices = [i * len(examples) // 5 for i in range(5)]
                    examples = [examples[i] for i in indices]
                
                for tool in examples:
                    desc_preview = tool['description'][:80] + "..." if len(tool['description']) > 80 else tool['description']
                    summary += f"\n    - {tool['name']}: {desc_preview}"
            
            server_summaries.append(summary)
        
        prompt = f"""Analyze whether the following tool semantically belongs to its current server or would fit better elsewhere.

## Tool to Analyze
- **Name**: {tool_name}
- **Description**: {tool_desc}
- **Current Server**: {current_server}

## Available Servers and Their Tools
{chr(10).join(server_summaries)}

## Analysis Task
Based on the tool's description and functionality:
1. How well does this tool fit semantically with its current server? (0.0-1.0)
2. Is there another server where this tool would fit significantly better?
3. Are there any suspicious indicators suggesting this tool might be:
   - Malicious or trying to hide its true purpose
   - Accidentally placed in the wrong server
   - Designed to exploit cross-server functionality

## Important Notes
- Focus on semantic meaning, not superficial name similarities
- A generic name like 'add' should be interpreted in the server's context
- Consider whether the tool's actual functionality aligns with other tools in the server

## Response Format
Provide your analysis in JSON:
{{
  "current_server_fit": float (0.0-1.0),
  "best_fitting_server": "server_name",
  "best_server_fit": float (0.0-1.0),
  "other_high_fit_servers": [
    {{"server": "name", "fit": float}}
  ],
  "is_suspicious": boolean,
  "reasoning": "explanation of your analysis",
  "confidence": float (0.0-1.0)
}}"""
        
        return prompt
    
    async def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API"""
        try:
            if hasattr(openai, '__version__') and int(openai.__version__.split('.')[0]) >= 1:
                # Modern client
                client = openai.OpenAI(api_key=openai.api_key)
                response = await asyncio.to_thread(
                    lambda: client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are a tool deviation analyzer. Respond only with valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.0
                    )
                )
                return response.choices[0].message.content
            else:
                # Legacy client
                response = await asyncio.to_thread(
                    openai.ChatCompletion.create,
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a tool deviation analyzer. Respond only with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0
                )
                return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI API error: {e}")
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
