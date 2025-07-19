# 🔍 MCP Outlier Scanner

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg?style=for-the-badge&logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)
[![Security](https://img.shields.io/badge/Security-Tool-red.svg?style=for-the-badge&logo=security)](https://github.com/YusukeJustinNakajima/mcp-outlier-scanner)

**A robust security tool for detecting malicious or misplaced tools in MCP servers using hybrid AI**

## 🚨 Why This Tool is Necessary

### ❌ The Problem with Existing Approaches

#### 1️⃣ Single-Server Analysis Limitations
- Most scanners only analyze within single server context
- Attackers easily craft legitimate-looking descriptions
- No cross-server validation
- Malicious tools hide by mimicking patterns

#### 2️⃣ LLM-Only Detection Vulnerabilities
- Vulnerable to adversarial prompt engineering
- Attackers can deceive LLMs with crafted descriptions
- Lacks mathematical rigor of embeddings
- No fallback when LLMs are fooled

### ✅ Our Solution: Hybrid Detection Approach

| Feature | Description |
|---------|-------------|
| **Embedding-based** | Mathematical similarity detection that's hard to fool |
| **LLM-based** | Semantic understanding for nuanced detection |
| **Cross-server** | Detects tools that appear to be maliciously placed in other servers to interfere with or manipulate their behavior |
| **Maximum score** | Takes the highest detection score from all methods |

## ✨ Features

- **Dual Detection Methods**: Combines embedding and LLM analysis for each check
- **Cross-Server Analysis**: Detects tools that appear to be maliciously placed in other servers to interfere with or manipulate their behavior
- **Consistency Checking**: Validates tool descriptions against server context
- **Async Scanning**: Fast, concurrent scanning of multiple MCP servers
- **False Positive Warnings**: Alerts when detection methods disagree significantly
- **Multiple Output Formats**: Text and JSON output options
- **Flexible Configuration**: Works with or without LLM support

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

## 🔬 Detection Methods

### 1️⃣ Consistency Check
- **Embedding Analysis**: Measures semantic alignment between tool name, description, and server context
- **LLM Analysis**: Evaluates tool consistency with server purpose and patterns
- **Hybrid Scoring**: Takes maximum of both methods to catch evasion attempts

### 2️⃣ Cross-Server Analysis
- **Embedding Analysis**: Compares tool similarity across all servers using vector embeddings
- **LLM Analysis**: Determines best-fitting server using semantic understanding
- **Detects**: Tools accidentally or maliciously placed in wrong servers
- **Critical Feature**: Identifies tools that might manipulate or modify tools in other servers
- **Hybrid Scoring**: Maximum score from embedding and LLM ensures robust detection even if one method is bypassed

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

## 🤝 Contributing

**Contributions are welcome! Please feel free to submit a Pull Request.**

### 👨‍💻 Development Setup

```bash
# Clone repository
git clone https://github.com/YusukeJustinNakajima/mcp-outlier-scanner.git
cd mcp-outlier-scanner

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## 📄 License

**MIT License** - see [LICENSE](LICENSE) file for details

---

**Note**: This tool is designed for defensive security purposes. Always ensure you have permission before scanning MCP servers.

Made with ❤️ for MCP Security