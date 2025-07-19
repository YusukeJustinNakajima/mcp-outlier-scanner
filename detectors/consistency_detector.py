#!/usr/bin/env python3
"""
Consistency-based deviation detector using embeddings and LLM
"""

import os
import json
import asyncio
import numpy as np
from typing import List, Dict, Tuple, Optional

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


class ConsistencyDetector(BaseDetector):
    """Check consistency using embeddings and LLM for semantic understanding"""
    
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
        """Check if consistency checking is available"""
        return self.model is not None or self.use_llm
    
    async def detect(self, servers: List[MCPServer]) -> List[DeviationResult]:
        """Detect tools with inconsistent naming or poor semantic fit with server"""
        if not self.is_available():
            print("Warning: ConsistencyDetector requires sentence-transformers or OpenAI API")
            return []
        
        results = []
        
        for server in servers:
            if server.status != "scanned" or not server.tools:
                continue
            
            # Prepare tools data for coherence calculation
            tools_data = [(t.name, t.description) for t in server.tools]
            
            # Calculate semantic coherence scores if multiple tools
            coherence_scores = {}
            if len(server.tools) >= 5 and self.model:
                coherence_scores = self.calculate_semantic_coherence(
                    server.name, tools_data
                )
            
            for tool in server.tools:
                deviation_score = 0.0
                reasons = []
                embed_score = 0.0
                llm_score = 0.0
                embed_reasons = []
                llm_reasons = []
                
                # 1. Embedding-based consistency check (if available)
                if self.model:
                    embed_score, embed_reasons = self.check_server_tool_consistency(
                        server.name, tool.name, tool.description
                    )
                    
                    # Add coherence score if available
                    if tool.name in coherence_scores:
                        coherence = coherence_scores[tool.name]
                        if coherence < 0.2:
                            embed_score += 0.4
                            embed_reasons.append("Low semantic coherence with other tools in server")
                        elif coherence < 0.4:
                            embed_score += 0.2
                            embed_reasons.append("Below average semantic coherence")
                    
                    embed_score = min(embed_score, 1.0)
                
                # 2. LLM-based consistency check (if available)
                if self.use_llm:
                    try:
                        llm_score, llm_reasons = await self.check_consistency_with_llm(
                            server.name, tool.name, tool.description, tools_data
                        )
                    except Exception as e:
                        if self.debug:
                            print(f"{Fore.RED}[DEBUG] LLM consistency check failed: {e}{Style.RESET_ALL}")
                
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
                final_reason = "\n".join(formatted_reasons) if formatted_reasons else "Semantically consistent with server context"
                
                results.append(DeviationResult(
                    tool=tool,
                    baseline_tools=[t for t in server.tools if t != tool],
                    is_deviation=is_deviation,
                    confidence=deviation_score,
                    reason=final_reason
                ))
        
        return results
    
    def check_server_tool_consistency(self, server_name: str, tool_name: str, tool_description: str) -> Tuple[float, List[str]]:
        """Check semantic consistency between (server+tool name) and tool description using embeddings"""
        if not self.model:
            return 0.0, ["Embedding model not available"]
        
        deviation_score = 0.0
        reasons = []
        
        # Preprocess texts for better embedding
        server_name_processed = TextProcessor.preprocess_for_embedding(server_name)
        tool_name_processed = TextProcessor.preprocess_for_embedding(tool_name)
        tool_desc_processed = TextProcessor.preprocess_for_embedding(tool_description)
        
        # Create combined context: server name + tool name
        combined_context = f"{server_name_processed} {tool_name_processed}"
        
        # Create embeddings
        context_embedding = self.model.encode(combined_context)
        description_embedding = self.model.encode(tool_desc_processed)
        
        # Check semantic similarity between (server+tool) context and description
        context_desc_similarity = self._cosine_similarity(context_embedding, description_embedding)
        
        # Evaluate the similarity
        if context_desc_similarity < 0.2:  # Very low similarity
            deviation_score += 0.8
            reasons.append("Tool description is semantically unrelated to its context (server + tool name)")
        elif context_desc_similarity < 0.35:  # Low similarity
            deviation_score += 0.6
            reasons.append("Tool description has weak semantic alignment with its context")
        elif context_desc_similarity < 0.5:  # Moderate similarity
            deviation_score += 0.4
            reasons.append("Tool description shows moderate semantic alignment with its context")
        
        return deviation_score, reasons
    
    async def check_consistency_with_llm(self, server_name: str, tool_name: str, 
                                       tool_description: str, all_tools: List[Tuple[str, str]]) -> Tuple[float, List[str]]:
        """Check consistency using LLM for deeper semantic analysis"""
        prompt = f"""Analyze the semantic consistency of a tool within its server context.

## Server Context
**Server Name**: {server_name}

## Other Tools in This Server
{self._format_tools_for_llm(all_tools, exclude_tool=tool_name)}

## Tool to Analyze
**Name**: {tool_name}
**Description**: {tool_description}

## Analysis Task
Evaluate the semantic consistency of this tool with:
1. The server's name and apparent purpose
2. The pattern and functionality of other tools in the server
3. Whether the tool's description matches what would be expected from its name in this context

Consider:
- Does the tool's functionality align with the server's domain?
- Is the description consistent with similar tools in this server?
- Are there any semantic red flags (e.g., generic descriptions, mismatched functionality)?
- Could this tool be trying to hide its true purpose with a misleading description?

## Response Format
Provide your analysis in JSON:
{{
  "server_alignment_score": float (0.0-1.0),  // How well the tool fits the server's purpose
  "description_consistency_score": float (0.0-1.0),  // How consistent the description is with the tool name
  "pattern_conformity_score": float (0.0-1.0),  // How well it matches patterns of other tools
  "suspicion_indicators": [
    "specific red flag or concern"
  ],
  "is_inconsistent": boolean,
  "confidence": float (0.0-1.0),
  "reasoning": "brief explanation"
}}"""
        
        try:
            response = await self._call_openai(prompt)
            result = json.loads(response)
            
            # Calculate deviation score from LLM analysis
            deviation_score = 0.0
            reasons = []
            
            # Server alignment
            alignment = result.get('server_alignment_score', 0.5)
            if alignment < 0.3:
                deviation_score += 0.3
                reasons.append(f"Poor alignment with server purpose (score: {alignment:.2f})")
            elif alignment < 0.5:
                deviation_score += 0.2
                reasons.append(f"Weak alignment with server purpose (score: {alignment:.2f})")
            
            # Description consistency
            desc_consistency = result.get('description_consistency_score', 0.5)
            if desc_consistency < 0.3:
                deviation_score += 0.3
                reasons.append(f"Description inconsistent with tool name (score: {desc_consistency:.2f})")
            elif desc_consistency < 0.5:
                deviation_score += 0.2
                reasons.append(f"Description weakly matches tool name (score: {desc_consistency:.2f})")
            
            # Pattern conformity
            pattern_score = result.get('pattern_conformity_score', 0.5)
            if pattern_score < 0.3:
                deviation_score += 0.2
                reasons.append(f"Doesn't follow server tool patterns (score: {pattern_score:.2f})")
            
            # Suspicion indicators
            suspicion_indicators = result.get('suspicion_indicators', [])
            if suspicion_indicators:
                deviation_score += 0.2 * len(suspicion_indicators)
                for indicator in suspicion_indicators[:2]:  # Limit to 2 indicators
                    reasons.append(f"Suspicious: {indicator}")
            
            # Direct inconsistency flag
            if result.get('is_inconsistent', False):
                deviation_score += 0.3
                
            # Add reasoning if significant
            if result.get('reasoning') and deviation_score > 0.3:
                reasons.append(f"Analysis: {result['reasoning']}")
            
            # Apply LLM confidence
            confidence = result.get('confidence', 1.0)
            deviation_score = min(deviation_score * confidence, 1.0)
            
            return deviation_score, reasons
            
        except Exception as e:
            if self.debug:
                print(f"{Fore.RED}[DEBUG] LLM call failed: {e}{Style.RESET_ALL}")
            return 0.0, [f"LLM analysis failed: {str(e)}"]
    
    def _format_tools_for_llm(self, tools: List[Tuple[str, str]], exclude_tool: str = None) -> str:
        """Format tools list for LLM prompt"""
        formatted = []
        for name, desc in tools:
            if name != exclude_tool:
                desc_preview = desc[:100] + "..." if len(desc) > 100 else desc
                formatted.append(f"- **{name}**: {desc_preview}")
        
        # Limit to 10 examples
        if len(formatted) > 10:
            formatted = formatted[:10]
            formatted.append(f"... and {len(tools) - 10} more tools")
        
        return "\n".join(formatted) if formatted else "No other tools in this server"
    
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
                            {"role": "system", "content": "You are a semantic consistency analyzer. Respond only with valid JSON."},
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
                        {"role": "system", "content": "You are a semantic consistency analyzer. Respond only with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0
                )
                return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI API error: {e}")
    
    def calculate_semantic_coherence(self, server_name: str, tools_data: List[tuple]) -> Dict[str, float]:
        """Calculate semantic coherence of each tool with the server context"""
        if not self.model or not tools_data:
            return {}
        
        coherence_scores = {}
        
        # Preprocess server name
        server_name_processed = TextProcessor.preprocess_for_embedding(server_name)
        
        # Create embeddings for all tools with preprocessing
        tool_embeddings = []
        tool_texts = []
        for name, desc in tools_data:
            name_processed = TextProcessor.preprocess_for_embedding(name)
            desc_processed = TextProcessor.preprocess_for_embedding(desc)
            tool_text = f"{name_processed}: {desc_processed}"
            tool_texts.append(tool_text)
            tool_embeddings.append(self.model.encode(tool_text))
        
        if tool_embeddings:
            # Calculate centroid of all tool embeddings
            centroid = np.mean(tool_embeddings, axis=0)
            
            # Create server context embedding
            server_context = f"Server {server_name_processed} provides: " + "; ".join(tool_texts)
            context_embedding = self.model.encode(server_context)
            
            # Calculate each tool's coherence
            for i, (name, desc) in enumerate(tools_data):
                # Distance from centroid
                centroid_similarity = self._cosine_similarity(tool_embeddings[i], centroid)
                
                # Distance from context
                context_similarity = self._cosine_similarity(tool_embeddings[i], context_embedding)
                
                # Combined coherence score (weighted more towards centroid)
                coherence = (centroid_similarity * 0.7 + context_similarity * 0.3)
                coherence_scores[name] = coherence
        
        return coherence_scores
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)