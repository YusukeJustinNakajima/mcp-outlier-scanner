# 🔍 MCP Outlier Scanner

**A robust security tool for detecting malicious tools in MCP servers using hybrid AI**

<img width="1899" height="680" alt="image" src="https://github.com/user-attachments/assets/e7aeb92d-2639-4858-9633-c7732483f6a9" />

## 🚨 Background
- During the analysis of existing MCP scanning tools, I discovered critical limitations that led to the failure in detecting a malicious tool. These tools suffered from:

### 1️⃣ Overlooking Semantic Inconsistency
- Existing scanners analyze each tool description in isolation using LLMs, without checking for inconsistencies between the tool's name and description.
- For example, a tool named "get_cve" should describe fetching CVE data, not performing unrelated tasks. This semantic alignment is rarely verified.

### 2️⃣ Lack of Multi-Server Context Awareness
- Malicious tools often exploit inter-server trust assumptions, camouflaging themselves among benign tools or mimicking tools from other servers. Current tools don't compare across servers.

## ✅ Our Solution:
- To overcome these limitations, I built MCP Outlier Scanner, a comprehensive and extensible tool designed to detect malicious MCP tools with higher robustness.

### ✨ Features
1. Consistency Checking
- Compares tool name, description, and associated server context for semantic alignment.
- Identifies tools whose behavior or purpose deviates from expected patterns within the same server.

2. Cross-Server Analysis
- Detects tools that appear to be maliciously placed in other servers to interfere with or manipulate their behavior.

3. Dual Detection Methods
- LLM-Based Reasoning: Leverages large language models to reason about potential anomalies.
- Embedding-Based Similarity: Uses vector representations of tool descriptions to detect semantic outliers, reducing susceptibility to prompt-based evasion.

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/YusukeJustinNakajima/mcp-outlier-scanner.git
cd mcp-outlier-scanner

# Install dependencies
pip install -r requirements.txt
```

### 📋 Requirements

- **Python 3.8+**
- **Claude Desktop** with configured MCP servers
- **Optional:** OpenAI API key for LLM-enhanced detection

## 📖 Usage

### 🎯 Basic Usage

```bash
# Scan with default methods (consistency + cross-server)
python mcp_scanner.py

# Enable LLM-enhanced detection
python mcp_scanner.py --use-ai

# Use specific detection method
python mcp_scanner.py --methods consistency
```

### 🚀 Advanced Usage

```bash
# Set API key via environment variable
export OPENAI_API_KEY=your-api-key
python mcp_scanner.py --use-ai

# Save results to JSON file
python mcp_scanner.py --output json --save results.json

# Debug mode with detailed output
python mcp_scanner.py --debug --use-ai

# Custom timeout for slow servers
python mcp_scanner.py --timeout 60
```

### ⚙️ Command Line Options

| Option | Description |
|--------|-------------|
| `--config PATH` | Path to Claude Desktop config file |
| `--timeout SEC` | Timeout for server scanning (default: 30) |
| `--use-ai` | Enable AI/LLM for enhanced detection |
| `--api-key KEY` | OpenAI API key for LLM detection |
| `--output {text,json}` | Output format (default: text) |
| `--save FILE` | Save report to specified file |
| `--debug` | Enable debug output |
| `--methods METHOD` | Detection methods: consistency, cross-server, multi, ai |


## 📊 Output Format

### 📝 Text Output (Default)
```
[DEVIATION] suspicious_tool (from mcp-server)
  Confidence: 85.00%
  Reason:
    📊 Detection Scores - Embedding: 0.60, LLM: 0.85 (Max: 0.85)
    🔍 Embedding Analysis:
      • Tool description has weak semantic alignment with its context
    🤖 LLM Analysis:
      • Poor alignment with server purpose (score: 0.25)
      • Much better fit with 'other-server' (LLM: 0.90 vs 0.25, diff: +0.65)
  ⚠️  HIGH RISK: Review this tool immediately
  Recommendation: Investigate why this tool exists in the mcp-server server
```

### 📋 JSON Output
```json
{
  "scan_timestamp": "2024-01-20T10:30:00",
  "summary": {
    "total_servers": 5,
    "successful_scans": 5,
    "total_tools": 47,
    "deviations_found": 2
  },
  "deviations": [...]
}
```

## 🏗️ Architecture

```
mcp-outlier-scanner/
├── mcp_scanner.py              # Main entry point
├── models.py                   # Data models
├── config_loader.py            # Configuration handling
├── server_scanner.py           # MCP server communication
├── detector_manager.py         # Detection orchestration
├── report_generator.py         # Output formatting
├── utils.py                    # Utilities
└── detectors/
    ├── base_detector.py        # Base detector class
    ├── consistency_detector.py # Consistency checking
    └── crossserver_detector.py # Cross-server analysis
```


## 🚀 Future Work
📱 Multi-Client Support
- Currently, MCP Outlier Scanner is designed specifically for Claude Desktop's configuration format. However, as the MCP ecosystem grows, I plan to extend support to other MCP clients:
### Planned Client Support
- Cursor: Add support for Cursor's MCP configuration format and installation paths
- VS Code MCP Extension: Integrate with VS Code's MCP extension configurations
- Other MCP-Compatible Clients: As new clients adopt the MCP standard, we'll add support for their configuration formats

## 📄 License

**MIT License** - see [LICENSE](LICENSE) file for details

## 🤝 Contributing

**Contributions are welcome! Please feel free to submit a Pull Request.**

---

**Note**: This tool is designed for defensive security purposes. Always ensure you have permission before scanning MCP servers.
