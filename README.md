# XQ9-Agent

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An AI-powered agent interface built with Python that leverages tool calling to perform web searches, read web pages, execute local Python code, and manage persistent memory across conversations.

### Prerequisites

- Python 3.12 (tested and confirmed working)
- An API key for an OpenAI-compatible API endpoint (e.g., OpenAI, Azure OpenAI, or local LLM)

## ✨ Features

- **🌐 Web Search** – Search the internet with automatic fallback mechanisms (DuckDuckGo, Wikipedia API)
- **📖 URL Reading** – Extract and clean text content from any webpage, with built-in detection for domain parking pages
- **🐍 Local Python Execution** – Run Python code directly on your local machine (equivalent to `python -c "code"`)
- **🧠 Persistent Memory** – Store, retrieve, update, and delete memories across all conversations using a local SQLite database
- **🌍 Multilingual Support** – Automatically switches between Traditional Chinese and English system prompts based on user input
- **🛠️ Rich CLI Interface** – Beautiful terminal output with Rich library, Markdown rendering, and colored logging
- **📊 Comprehensive Logging** – All searches and URL opens are logged to the `logs/` directory for debugging

## 🚀 Quick Start

### Prerequisites

- Python 3.12 or higher
- An API key for an OpenAI-compatible API endpoint (e.g., OpenAI, Azure OpenAI, or local LLM)

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/Poseidon0901/XQ9-Agent.git
   cd XQ9-Agent
   ```

2. **Create and activate a virtual environment**

   ```bash
   # On Windows
   python -m venv venv
   venv\Scripts\activate

   # On macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**

   Create a `.env` file in the project root with the following:

   ```env
   API_KEY=your_api_key_here
   API_URL=https://api.openai.com/v1
   MODEL=gpt-4
   ```

   > **Note**: The API must support tool calling (function calling) and the `reasoning` parameter.

## 🎮 Usage

### Basic Commands

Start the agent:

```bash
python agent.py
```

### Interactive CLI Commands

| Command | Description |
|---------|-------------|
| `/exit` or `/quit` | Exit the program |
| `/clear` or `/erase` | Clear the current conversation history |
| `/logs` or `/showlogs` | Show recent log files |
| `/clearlogs` or `/deletelogs` | Delete all log files (requires confirmation) |
| `/togglesystemprompt` | Toggle whether to use system prompt |
| `/toggletools` | Toggle whether to use tools |

### Example Interactions

**Ask a general question:**
```
You > What is the capital of France?
AI > Paris is the capital of France...
```

**Perform a web search:**
```
You > What are the latest features in Python 3.13?
[AI performs web_search, reads relevant articles, and provides a summary]
```

**Remember information:**
```
You > Please remember that I prefer to use PyCharm as my IDE.
AI > Memory stored successfully!
You > What's my preferred IDE?
AI > You prefer to use PyCharm as your IDE.
```

**Execute Python code locally:**
```
You > Calculate the average of [1, 2, 3, 4, 5]
[AI uses run_python to compute and display the result]
```

## 🔧 Tool Reference

The agent has 4 tools available. Each has usage limits to prevent infinite loops:

| Tool | Purpose | Max Calls |
|------|---------|-----------|
| `web_search(query)` | Search the internet for information | 5 |
| `open_url_by_index(index)` | Read a search result by its index | 10 |
| `run_python(code)` | Execute Python code locally | 30 (total) |
| `manage_memories(operation, ...)` | Manage persistent memory (create, read, update, delete, list, clear_all) | 30 (total) |

> **Note**: The total number of tool calls across all tools is limited to 30 per conversation.

## 📁 Project Structure

```
XQ9-Agent/
├── agent.py                  # Main application entry point
├── requirements.txt          # Python dependencies
├── .env.example              # Example environment variables
├── system_prompt_en_us.txt   # English system prompt
├── system_prompt_zh_tw.txt   # Traditional Chinese system prompt
├── tools/
│   ├── __init__.py           # Tool registry
│   ├── config.py             # Configs
│   ├── handler.py            # Tool handling
│   ├── web_search.py         # Search engine implementation
│   ├── open_url.py           # Web page fetcher with cleaning
│   ├── run_python.py         # Local Python execution
│   ├── manage_memories.py    # Persistent memory system
│   ├── get_domain.py         # Domain extraction helper
│   └── normalize_url.py      # URL normalization helper
├── logs/                     # Log files (auto-created)
└── memories.db               # Persistent SQLite memory database (auto-created)
```

## 🧠 Memory System

The `manage_memories` tool provides persistent storage across all sessions:

| Operation | Description | Example |
|-----------|-------------|---------|
| `create` | Store a new memory | `manage_memories(operation="create", content="User likes Python")` |
| `read` | Retrieve memories | `manage_memories(operation="read", keyword="Python")` |
| `update` | Modify a memory | `manage_memories(operation="update", memory_id=1, content="User loves Python")` |
| `delete` | Remove a memory | `manage_memories(operation="delete", memory_id=1)` |
| `list` | Show all memories | `manage_memories(operation="list")` |
| `clear_all` | Delete ALL memories | `manage_memories(operation="clear_all")` |

## 📁 File System

The `manage_files` tool provides persistent file storage. By default, files are stored in the `agent_workspace/` directory. You can specify a custom location by providing a `file_path`:

- A bare filename (e.g., `notes.txt`) is placed in `agent_workspace/`.
- A path with directory components (e.g., `subdir/notes.txt` or an absolute path) is used as-is (relative paths are resolved from the current working directory).

| Operation | Description | Example |
|-----------|-------------|---------|
| `create` | Create a new file | `manage_files(operation="create", file_path="notes.txt", content="Hello")` |
| `read` | Read a file | `manage_files(operation="read", file_path="notes.txt")` |
| `update` | Update an existing file | `manage_files(operation="update", file_path="notes.txt", content="Updated")` |
| `delete` | Delete a file | `manage_files(operation="delete", file_path="notes.txt")` |
| `list` | List files in a directory | `manage_files(operation="list")` |
| `clear_all` | Delete all files in a subdirectory | `manage_files(operation="clear_all", file_path="temp")` |

**Note**: `clear_all` refuses to clear the root `agent_workspace/` directory. You must specify a subdirectory.

## 🛡️ Safety Features

- **Tool call limits**: Prevents infinite loops and excessive API usage
- **Duplicate search prevention**: Automatically blocks repeated search queries
- **Timeout protection**: All operations have configurable timeouts
- **Domain parking detection**: Avoids reading empty or advertisement pages
- **Automatic conversation cleanup**: Trims old messages to save memory and tokens
- **Comprehensive error handling**: Graceful recovery from failures
- **File access**: `manage_files` can access the local filesystem (same permissions as `run_python`). Use responsibly.

## 🔧 Configuration

All configuration is managed through environment variables in `.env`:

| Variable | Description | Example |
|----------|-------------|---------|
| `API_KEY` | Your API authentication key | `sk-...` |
| `API_URL` | The API endpoint URL | `https://api.openai.com/v1/chat/completions` |
| `MODEL` | The model name to use | `gpt-4`, `gpt-3.5-turbo`, or custom model |

### Customization Constants

You can modify these in `agent.py`:

```python
MAX_TOTAL_TOOL_CALLS = 30   # Max tool calls per conversation
MAX_SEARCH_CALLS = 5        # Max web searches per conversation
MAX_OPEN_URL_CALLS = 10     # Max URL opens per conversation
MAX_SNIPPET_LENGTH = 150    # Search snippet length
MAX_SEARCH_RESULTS_KEPT = 5 # Results to keep in context
```

## 📝 Logging

All activities are logged to the `logs/` directory:

- `web_search_YYYY-MM-DD.HH.MM.SS.log` – All search queries and results
- `open_url_YYYY-MM-DD.HH.MM.SS.log` – All URL fetches with content

Use `/logs` to view recent log files and `/clearlogs` to clean them up.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- [Rich](https://github.com/Textualize/rich) for beautiful terminal output
- [DuckDuckGo Search](https://duckduckgo.com/) for web search capabilities
- [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) for HTML parsing

## ❓ FAQ

**Q: Can I use this with a local LLM?**  
A: Yes, as long as the API supports the OpenAI-compatible tool calling format and the `reasoning` parameter (or you can modify the code to disable it).

**Q: Does this work on Windows/macOS/Linux?**  
A: Yes! The agent is cross-platform and has been tested on all three operating systems.

**Q: Can the agent access my files?**  
A: Yes, through the `run_python` tool, which has the same permissions as the Python process. Use responsibly.

**Q: Where are my memories stored?**  
A: All memories are stored locally in `memories.db`, a SQLite database in the project root. They persist across sessions.

**Q: Why am I getting "Domain parking detected" errors?**  
A: The agent automatically skips pages that appear to be domain parking or for-sale pages. This is intentional to avoid wasting tool calls on irrelevant content.

**Q: Where are my files stored?**  
A: By default, files managed by `manage_files` are stored in the `agent_workspace/` directory. You can specify a different location by providing a `file_path`. Files persist across sessions.