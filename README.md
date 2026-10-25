# XQ9-Agent

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An AI-powered agent interface built with Python that leverages tool calling to perform web searches, read web pages, execute local Python code, manage persistent memory, and handle files across conversations.

### Prerequisites

- Python 3.12 (tested and confirmed working)
- An API key for an OpenAI-compatible API endpoint (e.g., OpenAI, Azure OpenAI, or local LLM)

## ✨ Features

- **🌐 Web Search** – Search the internet with automatic fallback mechanisms (DuckDuckGo, Wikipedia API)
- **📖 URL Reading** – Extract and clean text content from any webpage, with built-in detection for domain parking pages
- **🐍 Local Python Execution** – Run Python code directly on your local machine (equivalent to `python -c "code"`)
- **🧠 Persistent Memory** – Store, retrieve, update, and delete memories across all conversations using a local SQLite database
- **📁 File Management** – Create, read, update, delete, and list files inside `agent_workspace/` or custom paths
- **🌍 Multilingual Support** – Automatically switches between Traditional Chinese and English system prompts based on user input
- **🛠️ Rich CLI Interface** – Beautiful terminal output with Rich library, Markdown rendering, and colored logging
- **📊 Comprehensive Logging** – All searches and URL opens are logged to the `logs/` directory, with `/log list | delete | clear_all` subcommands for inspection and cleanup

## 🚀 Quick Start

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
   OPENAI_API_KEY=your_api_key_here
   OPENAI_API_URL=https://api.openai.com/v1
   MODEL=gpt-6-luna
   ```

   > **Note**: The API must support tool calling (function calling).

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
| `/clear` | Clear the current conversation history |
| `/log list [limit]` | Show recent log files (default: 10) |
| `/log delete <filename>` | Delete a single log file |
| `/log clear_all` | Delete all log files (requires confirmation) |
| `/set system_prompt <enable\|disable>` | Enable or disable the system prompt (alias: `prompt`) |
| `/set tools <enable\|disable>` | Enable or disable tool calling |

> **Note**: `/set` also accepts `on` / `off` / `true` / `false` in place of `enable` / `disable`.

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

The agent has 5 tools available. Each has usage limits per turn to prevent infinite loops:

| Tool | Purpose | Max Calls (per turn) |
|------|---------|----------------------|
| `web_search(query)` | Search the internet for information | 5 |
| `open_url_by_index(index)` | Read a search result by its index | 10 |
| `run_python(code)` | Execute Python code locally | 15 |
| `manage_memories(operation, ...)` | Manage persistent memory (create, read, update, delete, list, clear_all) | 10 |
| `manage_files(operation, ...)` | Manage files in workspace or custom paths (create, read, update, delete, list, clear_all) | 15 |

> **Note**: The total number of tool calls across all tools is limited to 30 per turn.

## 📁 Project Structure

```
XQ9-Agent/
├── agent.py                            # Main application entry point
├── requirements.txt                    # Python dependencies
├── pyproject.toml                      # Linting and formatting config
├── .env.example                        # Example environment variables
├── system_prompt_en_us.md              # English system prompt (with tools)
├── system_prompt_en_us_no_tools.md     # English system prompt (no tools)
├── system_prompt_zh_tw.md              # Traditional Chinese system prompt (with tools)
├── system_prompt_zh_tw_no_tools.md     # Traditional Chinese system prompt (no tools)
├── tools/
│   ├── __init__.py                     # Tool registry and function definitions
│   ├── commands.py                     # CLI slash command handling
│   ├── common_funcs.py                 # Shared helpers (domain parsing, text formatting)
│   ├── config.py                       # Configuration constants and tool limits
│   ├── handler.py                      # Tool dispatching and turn limits
│   ├── logs.py                         # Logging manager
│   ├── manage_files.py                 # Workspace file management
│   ├── manage_memories.py              # Persistent SQLite memory system
│   ├── open_url.py                     # Web page fetcher with anti-bot and cleaning
│   ├── run_python.py                   # Local Python execution
│   └── web_search.py                   # Multi-engine search implementation
├── agent_workspace/                    # Default workspace directory for files (auto-created)
├── logs/                               # Log files (auto-created)
└── memories.db                         # Persistent SQLite memory database (auto-created)
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

The `manage_files` tool provides persistent file storage. By default, files are stored in the `agent_workspace/` directory:

- Relative paths (e.g., `notes.txt` or `subdir/notes.txt`) are resolved inside `agent_workspace/`.
- Absolute paths (e.g., `C:\path\to\file.txt` or `/path/to/file.txt`) are used as-is.
- If `file_path` is omitted when creating a file, it defaults to `untitled_<timestamp>.txt` in `agent_workspace/`.

| Operation | Description | Example |
|-----------|-------------|---------|
| `create` | Create a new file | `manage_files(operation="create", file_path="notes.txt", content="Hello")` |
| `read` | Read a file | `manage_files(operation="read", file_path="notes.txt")` |
| `update` | Update an existing file | `manage_files(operation="update", file_path="notes.txt", content="Updated")` |
| `delete` | Delete a file | `manage_files(operation="delete", file_path="notes.txt")` |
| `list` | List files in a directory | `manage_files(operation="list")` |
| `clear_all` | Delete all files in a subdirectory | `manage_files(operation="clear_all", file_path="temp")` |

> **Note**: `clear_all` refuses to clear the root `agent_workspace/` directory. You must specify a subdirectory.

## 🛡️ Safety Features

- **Tool call limits**: Prevents infinite loops and excessive API usage
- **Duplicate search prevention**: Automatically blocks repeated search queries
- **Timeout protection**: Python execution and network requests have timeouts
- **Domain parking detection**: Avoids reading empty or advertisement pages
- **Automatic conversation cleanup**: Trims old messages when history exceeds 30 messages to save memory and tokens
- **Comprehensive error handling**: Graceful recovery from failures
- **File access**: `manage_files` and `run_python` run with local permissions. Use responsibly.

## 🔧 Configuration

All configuration is managed through environment variables in `.env`:

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your API authentication key | `sk-...` |
| `OPENAI_API_URL` | The API endpoint URL | `https://api.openai.com/v1` |
| `MODEL` | The model name to use | `gpt-6-luna` |

### Customization Constants

You can modify these in `tools/config.py`:

```python
MAX_TOTAL_TOOL_CALLS = 30  # Max total tool calls per turn
MAX_SEARCH_CALLS = 5  # Max web searches per turn
MAX_OPEN_URL_CALLS = 10  # Max URL opens per turn
MAX_RUN_PYTHON_CALLS = 15  # Max Python executions per turn
MAX_MEMORY_CALLS = 10  # Max memory operations per turn
MAX_FILE_CALLS = 15  # Max file operations per turn

MAX_SNIPPET_LENGTH = 150  # Search snippet length
MAX_SEARCH_RESULTS_KEPT = 5  # Results to keep in context
```

## 📝 Logging

All activities are logged to the `logs/` directory. Log files follow the naming pattern `<module>_<timestamp>.log`, where `<timestamp>` is the agent launch time in `YYYYMMDD_HHMMSS` format:

- `web_search_<timestamp>.log` – All search queries and results
- `open_url_<timestamp>.log` – All URL fetches with content

Use `/log list` to view recent log files, `/log delete <filename>` to remove a single file, and `/log clear_all` to remove all log files. All log operations go through the shared `LogManager` singleton (`app.log_manager`), which automatically re-creates active log files after a clear or delete.

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
A: Yes, through `manage_files` and `run_python`, which have the same permissions as the running Python process. Use responsibly.

**Q: Where are my memories stored?**  
A: All memories are stored locally in `memories.db`, a SQLite database in the project root. They persist across sessions.

**Q: Why am I getting "Domain parking detected" errors?**  
A: The agent automatically skips pages that appear to be domain parking or for-sale pages. This is intentional to avoid wasting tool calls on irrelevant content.

**Q: Where are my files stored?**  
A: By default, files managed by `manage_files` are stored in the `agent_workspace/` directory. You can specify a different location by providing a `file_path`. Files persist across sessions.
