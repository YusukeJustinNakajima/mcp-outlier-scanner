#!/usr/bin/env python3
"""
Report generator for MCP scanner results
"""

import json
from datetime import datetime
from typing import List, Dict, Any

from models import MCPServer, DeviationResult
from utils import Fore, Style, COLORS_AVAILABLE


class ReportGenerator:
    """Generate reports from scan results"""
    
    @staticmethod
    def generate_summary(servers: List[MCPServer], deviations: List[DeviationResult], debug: bool = False) -> str:
        """Generate a summary report with colors"""
        report = []
        
        # Header
        report.append(f"{Fore.CYAN}{Style.BRIGHT}{'='*60}")
        report.append(f"{Fore.CYAN}{Style.BRIGHT}🔍 MCP Server Scan Report")
        report.append(f"{Fore.CYAN}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")
        report.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Server summary
        total_servers = len(servers)
        successful_scans = sum(1 for s in servers if s.status == "scanned")
        failed_scans = sum(1 for s in servers if s.status == "error")
        total_tools = sum(len(s.tools) for s in servers if s.status == "scanned")
        
        report.append(f"{Style.BRIGHT}📊 Summary:{Style.RESET_ALL}")
        report.append(f"  Servers found: {Fore.WHITE}{total_servers}{Style.RESET_ALL}")
        report.append(f"  Successfully scanned: {Fore.GREEN}{successful_scans}{Style.RESET_ALL}")
        if failed_scans > 0:
            report.append(f"  Failed scans: {Fore.RED}{failed_scans}{Style.RESET_ALL}")
        report.append(f"  Total tools discovered: {Fore.BLUE}{total_tools}{Style.RESET_ALL}")
        report.append("")
        
        # Server details
        report.append(f"{Style.BRIGHT}📋 Server Details:{Style.RESET_ALL}")
        for server in servers:
            if server.status == "scanned":
                status_color = Fore.GREEN
                status_icon = "✅"
            else:
                status_color = Fore.RED
                status_icon = "❌"
            
            report.append(f"\n{status_icon} [{server.name}]")
            report.append(f"  Status: {status_color}{server.status}{Style.RESET_ALL}")
            
            if server.error_message:
                report.append(f"  Error: {Fore.RED}{server.error_message}{Style.RESET_ALL}")
            
            if server.tools:
                report.append(f"  Tools: {Fore.BLUE}{len(server.tools)}{Style.RESET_ALL}")
                for tool in server.tools[:5]:  # Show first 5 tools
                    desc_preview = tool.description[:60] + "..." if len(tool.description) > 60 else tool.description
                    report.append(f"    • {Fore.CYAN}{tool.name}{Style.RESET_ALL}: {desc_preview}")
                if len(server.tools) > 5:
                    report.append(f"    ... and {len(server.tools) - 5} more")
        
        # Deviation summary
        if deviations:
            deviation_count = sum(1 for d in deviations if d.is_deviation)
            
            report.append("")
            report.append(f"{Style.BRIGHT}⚠️  Detected Deviations:{Style.RESET_ALL}")
            report.append(f"Total deviations found: {Fore.RED}{Style.BRIGHT}{deviation_count}{Style.RESET_ALL}")
            
            if deviation_count > 0:
                report.append(f"\n{Fore.RED}{Style.BRIGHT}🚨 POTENTIAL SECURITY CONCERNS:{Style.RESET_ALL}")
                report.append(f"{Fore.YELLOW}The following tools may be malicious or unintended:{Style.RESET_ALL}")
            
            # In debug mode, show ALL analysis results
            if debug:
                report.append(f"\n{Style.BRIGHT}📊 All Analysis Results (Debug Mode):{Style.RESET_ALL}")
                for dev in deviations:
                    if dev.is_deviation:
                        confidence_color = Fore.RED if dev.confidence > 0.8 else Fore.YELLOW
                        header = f"{Fore.RED}{Style.BRIGHT}[DEVIATION]{Style.RESET_ALL}"
                    else:
                        confidence_color = Fore.GREEN
                        header = f"{Fore.GREEN}[OK]{Style.RESET_ALL}"
                    
                    report.append(f"\n{header} {dev.tool.name} (from {dev.tool.server_name})")
                    report.append(f"  {confidence_color}Confidence: {dev.confidence:.2%}{Style.RESET_ALL}")
                    report.append(f"  Analysis: {dev.reason}")
                    
                    if dev.is_deviation and dev.tool.description:
                        desc_lines = dev.tool.description.split('\n')
                        if len(desc_lines) > 3:
                            report.append(f"  Description: {desc_lines[0]}")
                            for line in desc_lines[1:3]:
                                report.append(f"              {line}")
                            report.append(f"              ... ({len(desc_lines) - 3} more lines)")
                        else:
                            report.append(f"  Description: {desc_lines[0]}")
                            for line in desc_lines[1:]:
                                report.append(f"              {line}")
            else:
                # Normal mode - only show deviations
                for dev in deviations:

                    if dev.is_deviation:
                        confidence_color = Fore.RED if dev.confidence > 0.8 else Fore.YELLOW
                        report.append(f"\n{Fore.RED}{Style.BRIGHT}[DEVIATION]{Style.RESET_ALL} {dev.tool.name} (from {dev.tool.server_name})")
                        report.append(f"  {confidence_color}Confidence: {dev.confidence:.2%}{Style.RESET_ALL}")
                        
                        # Check if reason contains multiple detection methods
                        if "Detected by" in dev.reason and " method(s): " in dev.reason:
                            # Parse multiple detection methods
                            parts = dev.reason.split("Detected by ")
                            if len(parts) > 1:
                                # Extract the detection count
                                method_info = parts[1].split(" method(s): ")
                                if len(method_info) >= 2:
                                    detection_count = method_info[0] + " method(s):"
                                    report.append(f"  Reason: Detected by {detection_count}")
                                    
                                    # Split the methods content
                                    methods_content = method_info[1]
                                    
                                    # Split by method markers
                                    import re
                                    # Pattern to match method names like CONSISTENCY_CHECK:, CROSS_SERVER_ANALYSIS:, etc.
                                    method_pattern = r'(CONSISTENCY_CHECK:|CROSS_SERVER_ANALYSIS:|SUSPICIOUS_PATTERN:)'
                                    method_parts = re.split(method_pattern, methods_content)
                                    
                                    # Process method parts (they come in pairs: name, content)
                                    i = 1
                                    while i < len(method_parts):
                                        if i + 1 < len(method_parts):
                                            method_name = method_parts[i].rstrip(':')
                                            method_content = method_parts[i + 1]
                                            
                                            # Determine method display name and color
                                            if 'CONSISTENCY_CHECK' in method_name:
                                                report.append(f"\n    {Fore.MAGENTA}{Style.BRIGHT}[CONSISTENCY CHECK]{Style.RESET_ALL}")
                                            elif 'CROSS_SERVER_ANALYSIS' in method_name:
                                                report.append(f"\n    {Fore.GREEN}{Style.BRIGHT}[CROSS-SERVER ANALYSIS]{Style.RESET_ALL}")
                                            elif 'SUSPICIOUS_PATTERN' in method_name:
                                                report.append(f"\n    {Fore.RED}{Style.BRIGHT}[SUSPICIOUS PATTERN]{Style.RESET_ALL}")
                                            else:
                                                report.append(f"\n    {Style.BRIGHT}[{method_name}]{Style.RESET_ALL}")
                                            
                                            # Process the method content line by line
                                            # Remove the leading semicolon separator if present
                                            method_content = method_content.strip()
                                            if method_content.startswith(';'):
                                                method_content = method_content[1:].strip()
                                            
                                            content_lines = method_content.split('\n')
                                            for line in content_lines:
                                                line = line.strip()
                                                if not line:
                                                    continue
                                                    
                                                # Apply formatting based on line content
                                                if line.startswith('📊'):
                                                    report.append(f"    {Fore.CYAN}{line}{Style.RESET_ALL}")
                                                elif line.startswith('⚠️'):
                                                    report.append(f"    {Fore.YELLOW}{Style.BRIGHT}{line}{Style.RESET_ALL}")
                                                elif line.startswith('🔍') or line.startswith('🤖'):
                                                    report.append(f"    {Fore.BLUE}{Style.BRIGHT}{line}{Style.RESET_ALL}")
                                                elif line.startswith('•'):
                                                    report.append(f"      {line}")
                                                else:
                                                    report.append(f"    {line}")
                                        i += 2
                                else:
                                    # Fallback to simple display
                                    report.append(f"  Reason: {dev.reason}")
                        else:
                            # Single-line or simple multi-line reason - use original logic
                            reason_lines = dev.reason.split('\n')
                            report.append(f"  Reason:")
                            for line in reason_lines:
                                # Maintain indentation and color coding
                                if line.startswith('📊'):
                                    report.append(f"    {Fore.CYAN}{line}{Style.RESET_ALL}")
                                elif line.startswith('⚠️'):
                                    report.append(f"    {Fore.YELLOW}{Style.BRIGHT}{line}{Style.RESET_ALL}")
                                elif line.startswith('🔍') or line.startswith('🤖'):
                                    report.append(f"    {Fore.BLUE}{Style.BRIGHT}{line}{Style.RESET_ALL}")
                                elif line.strip().startswith('•'):
                                    report.append(f"    {line}")
                                else:
                                    report.append(f"    {line}")
                        
                        # Add security warning for high confidence deviations
                        if dev.confidence > 0.8:
                            report.append(f"\n  {Fore.RED}{Style.BRIGHT}⚠️  HIGH RISK: Review this tool immediately{Style.RESET_ALL}")
                        
                        # Add recommendation
                        report.append(f"\n  {Fore.YELLOW}Recommendation: Investigate why this tool exists in the {dev.tool.server_name} server{Style.RESET_ALL}")
        else:
            report.append(f"\n{Fore.GREEN}✅ No deviations detected{Style.RESET_ALL}")
        
        return "\n".join(report)
    
    @staticmethod
    def generate_json_report(servers: List[MCPServer], deviations: List[DeviationResult]) -> Dict[str, Any]:
        """Generate a JSON report"""
        return {
            "scan_timestamp": datetime.now().isoformat(),
            "summary": {
                "total_servers": len(servers),
                "successful_scans": sum(1 for s in servers if s.status == "scanned"),
                "total_tools": sum(len(s.tools) for s in servers if s.status == "scanned"),
                "deviations_found": sum(1 for d in deviations if d.is_deviation)
            },
            "servers": [
                {
                    "name": s.name,
                    "status": s.status,
                    "error": s.error_message,
                    "tools_count": len(s.tools),
                    "tools": [
                        {
                            "name": t.name,
                            "description": t.description
                        }
                        for t in s.tools
                    ]
                }
                for s in servers
            ],
            "deviations": [
                {
                    "tool": {
                        "name": d.tool.name,
                        "description": d.tool.description,
                        "server": d.tool.server_name
                    },
                    "is_deviation": d.is_deviation,
                    "confidence": d.confidence,
                    "reason": d.reason
                }
                for d in deviations if d.is_deviation
            ]
        }