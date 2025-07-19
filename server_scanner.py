#!/usr/bin/env python3
"""
MCP Server Scanner - Scans MCP servers to discover their tools
"""

import os
import json
import asyncio
import platform
from typing import List, Optional

from models import MCPServer, MCPTool


class MCPServerScanner:
    """Scan MCP servers to discover their tools"""
    
    def __init__(self, timeout: int = 10, debug: bool = False):
        self.timeout = timeout
        self.debug = debug
    
    async def read_json_messages(self, reader, max_messages=10, total_timeout=5.0):
        """Read JSON messages from stream, handling partial messages"""
        messages = []
        buffer = ""
        start_time = asyncio.get_event_loop().time()
        
        try:
            while len(messages) < max_messages:
                # Check total timeout
                if asyncio.get_event_loop().time() - start_time > total_timeout:
                    break
                
                # Read available data with short timeout
                try:
                    chunk = await asyncio.wait_for(reader.read(1024), timeout=0.5)
                except asyncio.TimeoutError:
                    # No data available, but continue if we haven't reached total timeout
                    if buffer and messages:
                        # We have some data, might be enough
                        break
                    continue
                
                if not chunk:
                    break
                    
                buffer += chunk.decode('utf-8', errors='replace')
                
                # Try to parse complete JSON messages
                while True:
                    try:
                        # Find complete JSON object
                        decoder = json.JSONDecoder()
                        obj, idx = decoder.raw_decode(buffer)
                        messages.append(obj)
                        buffer = buffer[idx:].lstrip()
                    except json.JSONDecodeError:
                        # No complete JSON message yet
                        break
                        
        except Exception as e:
            # Log but don't fail completely
            if messages:
                return messages
            raise
            
        return messages
    
    async def scan_server(self, server: MCPServer, retry_count: int = 2) -> MCPServer:
        """Scan a single MCP server to discover its tools with retry logic"""
        last_error = None
        
        for attempt in range(retry_count + 1):
            if attempt > 0:
                if self.debug:
                    print(f"[DEBUG] Retrying {server.name} (attempt {attempt + 1}/{retry_count + 1})")
                # Wait before retry
                await asyncio.sleep(2.0)
            
            try:
                # Wrap the entire scanning process in a timeout
                result = await asyncio.wait_for(
                    self._scan_server_internal(server),
                    timeout=self.timeout
                )
                
                # If successful, return immediately
                if result.status == "scanned":
                    return result
                
                # Save error for potential retry
                last_error = result.error_message
                
            except asyncio.TimeoutError:
                last_error = f"Server scan timed out after {self.timeout} seconds"
            except Exception as e:
                last_error = str(e)
        
        # All retries failed
        server.status = "error"
        server.error_message = f"{last_error} (after {retry_count + 1} attempts)"
        return server
    
    async def _scan_server_internal(self, server: MCPServer) -> MCPServer:
        """Internal method to scan a server"""
        process = None
        try:
            # Create the command to run
            cmd = [server.command] + server.args
            
            # Fix for Windows: use npx.cmd instead of npx
            if server.command == "npx" and platform.system() == "Windows":
                import shutil
                
                # Find npx.cmd specifically
                npx_cmd_path = shutil.which("npx.cmd")
                if not npx_cmd_path:
                    # Try common locations
                    possible_paths = [
                        r"C:\Program Files\nodejs\npx.cmd",
                        r"C:\Program Files (x86)\nodejs\npx.cmd",
                        os.path.join(os.environ.get("APPDATA", ""), "npm", "npx.cmd"),
                    ]
                    
                    for path in possible_paths:
                        if os.path.exists(path):
                            npx_cmd_path = path
                            break
                
                if npx_cmd_path:
                    cmd[0] = npx_cmd_path
                else:
                    server.status = "error"
                    server.error_message = "npx.cmd not found. Please ensure Node.js is properly installed."
                    return server
            
            # Set up environment
            env = os.environ.copy()
            env.update(server.env)
            
            # Run the server process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            # Give server more time to start (especially for npx servers)
            startup_delay = 3.0 if server.command == "npx" else 1.5
            await asyncio.sleep(startup_delay)
            
            # MCP initialization handshake
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "mcp-outlier-scanner",
                        "version": "1.0.0"
                    }
                },
                "id": 1
            }
            
            # Send initialization
            process.stdin.write((json.dumps(init_request) + "\n").encode())
            await process.stdin.drain()
            
            # Read responses with longer timeout for slow servers
            messages = await self.read_json_messages(process.stdout, max_messages=20)
            
            # Look for initialization response
            init_success = False
            for msg in messages:
                if msg.get('id') == 1 and 'result' in msg:
                    init_success = True
                    break
                elif msg.get('id') == 1 and 'error' in msg:
                    server.status = "error"
                    server.error_message = f"Initialization error: {msg['error']}"
                    return server
            
            if not init_success:
                server.status = "error"
                server.error_message = "No initialization response received"
                return server
            
            # Send initialized notification
            initialized_notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            
            process.stdin.write((json.dumps(initialized_notification) + "\n").encode())
            await process.stdin.drain()
            
            # Request tools list
            list_tools_request = {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 2
            }
            
            process.stdin.write((json.dumps(list_tools_request) + "\n").encode())
            await process.stdin.drain()
            
            # Give more time between messages for slow servers
            await asyncio.sleep(0.5)
            
            # Read tools response with longer timeout
            messages = await self.read_json_messages(process.stdout, max_messages=20, total_timeout=5.0)
            
            # Parse tools response
            for msg in messages:
                if msg.get('id') == 2 and 'result' in msg and 'tools' in msg['result']:
                    tools_data = msg['result']['tools']
                    server.tools = [
                        MCPTool(
                            name=tool['name'],
                            description=tool.get('description', ''),
                            server_name=server.name,
                            input_schema=tool.get('inputSchema')
                        )
                        for tool in tools_data
                    ]
                    server.status = "scanned"
                    break
                elif msg.get('id') == 2 and 'error' in msg:
                    server.status = "error"
                    server.error_message = f"Tools list error: {msg['error']}"
                    break
            
            if server.status == "unknown":
                server.status = "error"
                server.error_message = "No tools response received"
                
        except Exception as e:
            server.status = "error"
            server.error_message = str(e)
        finally:
            # Clean up process
            if process and process.returncode is None:
                try:
                    # Close stdin first to signal we're done
                    process.stdin.close()
                    # Then terminate
                    process.terminate()
                    await asyncio.wait_for(process.wait(), timeout=2)
                except:
                    try:
                        process.kill()
                        await process.wait()
                    except:
                        pass
            
            # Ensure streams are closed
            if process:
                try:
                    if process.stdin and not process.stdin.is_closing():
                        process.stdin.close()
                    if process.stdout:
                        process.stdout._transport.close()
                    if process.stderr:
                        process.stderr._transport.close()
                except:
                    pass
        
        return server
    
    async def scan_all_servers(self, servers: List[MCPServer]) -> List[MCPServer]:
        """Scan all MCP servers concurrently"""
        tasks = [self.scan_server(server) for server in servers]
        return await asyncio.gather(*tasks)
