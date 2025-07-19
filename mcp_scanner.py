#!/usr/bin/env python3
"""
MCP Outlier Scanner
A tool to scan MCP servers from Claude Desktop configuration and detect tool deviations.
"""

import os
import json
import asyncio
import argparse
import sys
from pathlib import Path
from typing import List, Optional

from models import MCPServer
from config_loader import MCPConfigLoader
from server_scanner import MCPServerScanner
from detector_manager import DetectorManager
from report_generator import ReportGenerator
from utils import DetectionMethod, Fore, Style

# For AI-powered deviation detection
try:
    import openai
except ImportError:
    print(f"{Fore.YELLOW}Note: OpenAI library not found. Install with 'pip install openai' for AI-based detection.{Style.RESET_ALL}")
    openai = None


async def main():
    """Main entry point"""

    # Small ASCII art logo with better spacing
    logo = f"""{Fore.CYAN}{Style.BRIGHT}
 ╔╦╗╔═╗╔═╗   ╔═╗╦ ╦╔╦╗╦  ╦╔═╗╦═╗   ╔═╗╔═╗╔═╗╔╗╔╔╗╔╔═╗╦═╗
 ║║║║  ╠═╝   ║ ║║ ║ ║ ║  ║║╣ ╠╦╝   ╚═╗║  ╠═╣║║║║║║║╣ ╠╦╝
 ╩ ╩╚═╝╩     ╚═╝╚═╝ ╩ ╩═╝╩╚═╝╩╚═   ╚═╝╚═╝╩ ╩╝╚╝╝╚╝╚═╝╩╚═{Style.RESET_ALL}
                                                                
    {Fore.YELLOW}🔍 Detecting malicious tools in MCP servers with hybrid AI{Style.RESET_ALL}
    """

    parser = argparse.ArgumentParser(
        description=logo + "\n\nMCP Outlier Scanner - Detect tool deviations in MCP servers",
        epilog="""
        Examples:
        %(prog)s                              # Run with default methods (consistency, cross-server)
        %(prog)s --use-ai                     # Enable LLM-based detection (requires API key)
        %(prog)s --methods consistency        # Run only consistency check
        %(prog)s --methods multi --use-ai     # Run all methods with LLM support
        %(prog)s --output json --save out.json # Save results in JSON format
        
        Environment Variables:
        OPENAI_API_KEY                        # Set OpenAI API key for LLM detection
                """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--config", 
        metavar="PATH",
        help="Path to Claude Desktop config file (auto-detected if not provided)"
    )
    
    parser.add_argument(
        "--timeout", 
        type=int, 
        default=30, 
        metavar="SEC",
        help="Timeout for server scanning in seconds (default: 30)"
    )
    
    parser.add_argument(
        "--use-ai", 
        action="store_true", 
        help="Enable AI/LLM for enhanced deviation detection (requires OpenAI API key)"
    )
    
    parser.add_argument(
        "--api-key", 
        metavar="KEY",
        help="OpenAI API key for LLM detection (can also use OPENAI_API_KEY env var)"
    )
    
    parser.add_argument(
        "--output", 
        choices=["text", "json"], 
        default="text", 
        help="Output format for results (default: text)"
    )
    
    parser.add_argument(
        "--save", 
        metavar="FILE",
        help="Save report to specified file"
    )
    
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug output for troubleshooting"
    )
    
    parser.add_argument(
        "--methods", 
        nargs='+', 
        choices=['consistency', 'cross-server', 'multi', 'ai'],
        metavar="METHOD",
        help="""Detection methods to use. Available methods:
        consistency  - Check semantic consistency within server context
        cross-server - Analyze if tools belong to different servers  
        multi        - Use all available methods
        ai           - Use all methods with AI verification
        Default: consistency cross-server"""
    )
    
    args = parser.parse_args()

    # Show logo on normal execution (not just help)
    if not any(arg in sys.argv for arg in ['-h', '--help']):
        print(logo)
    
    # Set up logging if debug mode
    if args.debug:
        import logging
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        # Load configuration
        print(f"{Fore.CYAN}🔧 Loading Claude Desktop configuration...{Style.RESET_ALL}")
        if args.config:
            config_path = Path(args.config)
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            config = MCPConfigLoader.load_config()
        
        # Parse servers
        servers = MCPConfigLoader.parse_servers(config)
        print(f"{Fore.GREEN}✅ Found {len(servers)} MCP servers{Style.RESET_ALL}")
        
        if args.debug:
            for server in servers:
                print(f"  - {Fore.CYAN}{server.name}{Style.RESET_ALL}: {server.command} {' '.join(server.args)}")
        
        # Scan servers
        print(f"\n{Fore.CYAN}🔍 Scanning MCP servers for tools...{Style.RESET_ALL}")
        scanner = MCPServerScanner(timeout=args.timeout, debug=args.debug)
        servers = await scanner.scan_all_servers(servers)
        
        # Print scan results in debug mode
        if args.debug:
            for server in servers:
                if server.status == "scanned":
                    print(f"\n{Fore.GREEN}✅ [{server.name}] Status: {server.status}{Style.RESET_ALL}")
                else:
                    print(f"\n{Fore.RED}❌ [{server.name}] Status: {server.status}{Style.RESET_ALL}")
                if server.error_message:
                    print(f"  Error: {Fore.RED}{server.error_message}{Style.RESET_ALL}")
                if server.tools:
                    print(f"  Tools found: {Fore.BLUE}{len(server.tools)}{Style.RESET_ALL}")
                    for tool in server.tools:
                        print(f"    - {Fore.CYAN}{tool.name}{Style.RESET_ALL}")
        
        # Prepare detection methods
        method_map = {
            'consistency': DetectionMethod.CONSISTENCY_CHECK,
            'cross-server': DetectionMethod.CROSS_SERVER_ANALYSIS,
            'multi': DetectionMethod.MULTI_APPROACH,
            'ai': DetectionMethod.AI_ENHANCED,
        }
        
        if args.methods:
            methods = [method_map[m] for m in args.methods]
        else:
            methods = None  # Use default
        
        # Detect outliers
        print(f"\n{Fore.CYAN}🔍 Analyzing for tool deviations...{Style.RESET_ALL}")
        api_key = args.api_key or os.environ.get('OPENAI_API_KEY')
        
        # Check if LLM methods are requested without API key
        if methods and DetectionMethod.CROSS_SERVER_ANALYSIS in methods and args.use_ai:
            if not api_key:
                print(f"{Fore.RED}Error: --use-ai requires an API key.{Style.RESET_ALL}")
                print(f"Please provide an API key using --api-key or set OPENAI_API_KEY environment variable.")
                sys.exit(1)

        # Create detector manager
        detector_manager = DetectorManager(use_ai=args.use_ai, api_key=api_key, debug=args.debug)
        
        # Run detection
        deviations = await detector_manager.run_detection(servers, methods)
        
        # Generate report
        if args.output == "json":
            report = ReportGenerator.generate_json_report(servers, deviations)
            output = json.dumps(report, indent=2)
        else:
            output = ReportGenerator.generate_summary(servers, deviations, debug=args.debug)
        
        # Output results
        print("\n" + output)
        
        # Save if requested
        if args.save:
            with open(args.save, 'w') as f:
                # For JSON output or when saving to file, remove color codes
                if args.output == "json":
                    f.write(output)
                else:
                    # Strip color codes for file output
                    import re
                    clean_output = re.sub(r'\x1b\[[0-9;]*m', '', output)
                    f.write(clean_output)
            print(f"\n{Fore.GREEN}💾 Report saved to: {args.save}{Style.RESET_ALL}")
        
    except FileNotFoundError as e:
        print(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Make sure Claude Desktop is installed and configured with MCP servers.{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        print(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    finally:
        # Give async tasks time to clean up
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    # Use asyncio.run with proper cleanup
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⌛ Interrupted by user{Style.RESET_ALL}")
        sys.exit(0)
