# MCP Outlier Scanner

A tool to scan MCP (Model Context Protocol) servers from Claude Desktop configuration and detect tool deviations that might indicate malicious or misplaced tools.

## Structure

- `mcp_scanner.py` - Main entry point and command-line interface
- `models.py` - Data models (MCPTool, MCPServer, DeviationResult)
- `config_loader.py` - Claude Desktop configuration loader
- `server_scanner.py` - MCP server scanning and communication
- `detector_manager.py` - Manages and combines multiple detection methods
- `report_generator.py` - Report generation in text and JSON formats
- `utils.py` - Common utilities (text processing, colors, enums)
- `detectors/` - Detection method implementations
  - `base_detector.py` - Base class for all detectors
  - `pattern_detector.py` - Pattern analysis detection
  - `consistency_detector.py` - Semantic consistency checking
  - `crossserver_detector.py` - Cross-server analysis
  - `llm_detector.py` - LLM-based detection

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Basic scan:
```bash
python mcp_scanner.py
```

With AI-enhanced detection:
```bash
python mcp_scanner.py --use-ai --api-key YOUR_OPENAI_KEY
```

Select specific detection methods:
```bash
python mcp_scanner.py --methods pattern consistency cross-server
```

Save report:
```bash
python mcp_scanner.py --output json --save report.json
```

Debug mode:
```bash
python mcp_scanner.py --debug
```
