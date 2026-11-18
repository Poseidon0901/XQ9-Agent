# XQ9-Agent

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An AI-powered agent interface built with Python that leverages tool calling to perform web searches, read web pages, execute local Python code, manage persistent memory, and handle files across conversations.

### Prerequisites

- Python 3.12+ (tested and confirmed working)
- An API key for an OpenAI-compatible API endpoint (e.g., OpenAI, Azure OpenAI, or local LLMs such as Ollama / vLLM)

## ✨ Features

- **🌐 Resilient Web Search** – Search the internet using DuckDuckGo (`ddgs`) with multi-backend rotation (`bing`, `brave`, `duckduckgo`), automatic retries, language-aware region settings (`zh-tw` / `en-US`), and Wikipedia API fallback.
- **📖 URL Reading & Anti-Bot Protection** – Extract and clean text content from webpages using `curl_cffi` and `BeautifulSoup`, featuring heuristic scoring to detect domain parking, for-sale landers, and anti-bot challenges.
- **🔗 Automatic URL Detection** – Automatically identifies URLs inside user prompts and stages them into the current search results list for instant reading.
- **🐍 Local Python Execution** – Safely execute Python code directly via a local subprocess (`python -c "code"`) with configurable execution timeouts (1–300s).
- **🧠 Persistent Memory** – Store, retrieve, update, and delete memories across all conversations using a local SQLite database (`memories.db`).
- **📁 File Management** – Create, read, update, delete, and list files inside the dedicated workspace (`agent_workspace/`) or custom paths.
- **🌍 Multilingual Support** – Automatically detects language in user inputs and dynamically switches between Traditional Chinese (`zh_tw`) and English (`en_us`) system prompts (with tool and no-tool variants).
- **🛠️ Rich CLI Interface** – Beautiful terminal interface powered by Rich, featuring streaming Markdown rendering, live reasoning/thinking blocks, and colored execution logs.
- **📊 Comprehensive Logging** – All searches, URL fetches, and tool outputs are recorded in the `logs/` directory, managed via a singleton `LogManager` and interactive `/log` commands.

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

   Create a `.env` file in the project root (see `.env.example`):

   ```env
   OPENAI_API_KEY=your_api_key_here
   OPENAI_API_URL=https://api.openai.com/v1
   MODEL=gpt-6-luna
   ```

   > **Note**: If `OPENAI_API_KEY` is omitted or empty, it automatically defaults to `"placeholder"` (convenient for local LLM servers like Ollama or vLLM that do not require an API key). The API endpoint must support OpenAI-compatible tool calling (function calling).

## 🎮 Usage

### Basic Commands

Start the agent:

```bash
python agent.py
```

Upon launch, the application displays configured connection parameters (`API_URL`, `MODEL`, and masked `API_KEY`) and starts the interactive CLI session.

### Interactive CLI Commands

| Command | Description |
|---------|-------------|
| `/exit` or `/quit` | Exit the program |
| `/clear` | Clear conversation history, reset turn counters, search context, and query history |
| `/log list [limit]` | List recent log files (default: 10, max: 200) with file size and modification timestamps |
| `/log delete <filename>` | Delete a single specified log file |
| `/log clear_all` | Delete all log files (prompts for confirmation; automatically re-creates active session log files) |
| `/set system_prompt <enable\|disable>` | Enable or disable the system prompt (alias: `/set prompt ...`) |
| `/set tools <enable\|disable>` | Enable or disable tool calling (dynamically switches between tools and no-tools prompt variants) |

> **Tip**: `/set` also accepts `on` / `off` / `true` / `false` as values.

### Example Interactions

**Ask a general question:**
```
You > What is the capital of France?
AI > Paris is the capital of France...
```

**Perform a web search:**
```
You > What are the latest features in Python 3.13?
[AI performs web_search, reads relevant articles via open_url_by_index, and provides a summary]
```

**Direct URL inspection:**
```
You > Can you summarize this article: https://example.com/news
[AI detects URL, stages it to search results, opens it via open_url_by_index, and summarizes the content]
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

The agent has 5 built-in tools. Usage limits per turn prevent infinite loops and runaway API costs:

| Tool | Purpose | Max Calls (per turn) |
|------|---------|----------------------|
| `web_search(query, [strategy])` | Search the internet (`auto`, `_search_ddgs`, `_search_wikipedia_api`) | 5 |
| `open_url_by_index(index)` | Read full text from a search result by 1-based index | 10 |
| `run_python(code, [timeout])` | Execute Python code locally via subprocess (timeout: 1–300s, default: 10s) | 15 |
| `manage_memories(operation, ...)` | Manage persistent memory (`create`, `read`, `update`, `delete`, `list`, `clear_all`) | 10 |
| `manage_files(operation, ...)` | Manage files in workspace or custom paths (`create`, `read`, `update`, `delete`, `list`, `clear_all`) | 15 |

> **Note**: Total tool executions across all tools are capped at **30 calls per turn**. Exact duplicate search queries are rejected within the same session history to prevent loops.

## 📁 Project Structure

```
XQ9-Agent/
├── agent.py                            # Main application entry point & interactive loop
├── requirements.txt                    # Python dependencies
├── pyproject.toml                      # Linting, formatting, and type-check config
├── .env.example                        # Example environment variables
├── core/                               # Core application infrastructure
│   ├── __init__.py
│   ├── commands.py                     # CLI slash command handling (/clear, /log, /set, /exit)
│   ├── config.py                       # Core configuration & environment variables
│   ├── logs.py                         # LogManager singleton & session log file handling
│   └── text_utils.py                   # Language & Chinese character detection
├── prompts/                            # System prompt templates
│   ├── system_prompt_en_us.md          # English system prompt (with tools)
│   ├── system_prompt_en_us_no_tools.md # English system prompt (no tools)
│   ├── system_prompt_zh_tw.md          # Traditional Chinese system prompt (with tools)
│   └── system_prompt_zh_tw_no_tools.md # Traditional Chinese system prompt (no tools)
├── tools/                              # Agent tool definitions and implementations
│   ├── __init__.py                     # Tool registry and OpenAI function schemas
│   ├── config.py                       # Tool limits, enums, and operational constants
│   ├── console_utils.py                # Safe console printing utilities
│   ├── handler.py                      # Tool dispatching, turn limits, and deduplication
│   ├── manage_files.py                 # Local filesystem management
│   ├── manage_memories.py              # Persistent SQLite memory system
│   ├── open_url.py                     # Web page fetcher with anti-bot and parking detection
│   ├── run_python.py                   # Local Python execution with subprocess
│   ├── web_search.py                   # Multi-backend web search (DDGS & Wikipedia)
│   └── web_utils.py                    # Web & domain parsing helpers
├── agent_workspace/                    # Default workspace directory for files (auto-created)
├── logs/                               # Session log files (auto-created)
└── memories.db                         # Persistent SQLite memory database (auto-created)
```

## 🧠 Memory System

The `manage_memories` tool provides persistent storage across all sessions using SQLite (`memories.db`):

| Operation | Description | Example |
|-----------|-------------|---------|
| `create` | Store a new memory | `manage_memories(operation="create", content="User likes Python")` |
| `read` | Retrieve memories (by `keyword`, `date`, or `memory_id`) | `manage_memories(operation="read", keyword="Python")` |
| `update` | Modify an existing memory | `manage_memories(operation="update", memory_id=1, content="User loves Python")` |
| `delete` | Remove a memory | `manage_memories(operation="delete", memory_id=1)` |
| `list` | Show recent memories (newest first, optional `limit`) | `manage_memories(operation="list")` |
| `clear_all` | Delete ALL memories | `manage_memories(operation="clear_all")` |

## 📁 File System

The `manage_files` tool provides local file management. By default, files are stored in the `agent_workspace/` directory:

- **Relative paths** (e.g., `notes.txt` or `subdir/notes.txt`) are resolved inside `agent_workspace/`.
- **Absolute paths** (e.g., `C:\path\to\file.txt` or `/path/to/file.txt`) are accessed as-is.
- If `file_path` is omitted when creating a file, it defaults to `untitled_<timestamp>.txt` in `agent_workspace/`.

| Operation | Description | Example |
|-----------|-------------|---------|
| `create` | Create a new file (fails if file already exists) | `manage_files(operation="create", file_path="notes.txt", content="Hello")` |
| `read` | Read full text of a file | `manage_files(operation="read", file_path="notes.txt")` |
| `update` | Overwrite an existing file | `manage_files(operation="update", file_path="notes.txt", content="Updated")` |
| `delete` | Delete a file or directory | `manage_files(operation="delete", file_path="notes.txt")` |
| `list` | List directory contents | `manage_files(operation="list")` |
| `clear_all` | Delete all files in a subdirectory | `manage_files(operation="clear_all", file_path="temp")` |

> **Note**: `clear_all` refuses to clear the root `agent_workspace/` directory to prevent accidental total deletion. You must specify a subdirectory.

## 🛡️ Safety Features

- **Tool Call Quotas**: Limits both individual tool executions and overall turn count (max 30) to prevent infinite loops.
- **Search Deduplication**: Automatically blocks identical search queries within the active session.
- **Multi-Backend Search Resilience**: Rotates through DuckDuckGo search backends (`bing`, `brave`, `duckduckgo`) with automatic retries before falling back to Wikipedia API.
- **Domain Parking & Anti-Bot Detection**: Scores page content and titles against known domain parking, advertisement landers, and anti-bot challenge patterns to prevent reading low-quality or blocked sites.
- **Timeout Protection**: Enforces timeouts for Python execution (default 10s, max 300s) and network HTTP requests.
- **Workspace Boundary Safeguard**: `manage_files` requires targeting subdirectories when performing bulk deletion (`clear_all`) and will not delete the root workspace.

## 🔧 Configuration

### Environment Variables (`.env`)

| Variable | Description | Default / Example |
|----------|-------------|-------------------|
| `OPENAI_API_KEY` | API authentication key | `your_api_key_here` (defaults to `"placeholder"` if empty) |
| `OPENAI_API_URL` | API endpoint URL | `https://api.openai.com/v1` |
| `MODEL` | The model identifier | `gpt-6-luna` |

### Core Settings (`core/config.py`)

- `CONSOLE_REFRESH_RATE`: Refresh rate per second for Rich Live rendering (default: `100`).

### Tool & Operational Constants (`tools/config.py`)

```python
# Turn Call Limits
MAX_TOTAL_TOOL_CALLS = 30  # Max total tool calls per turn
MAX_SEARCH_CALLS = 5       # Max web searches per turn
MAX_OPEN_URL_CALLS = 10    # Max URL opens per turn
MAX_RUN_PYTHON_CALLS = 15  # Max Python executions per turn
MAX_MEMORY_CALLS = 10      # Max memory operations per turn
MAX_FILE_CALLS = 15        # Max file operations per turn

# Search & Content Limits
MAX_SNIPPET_LENGTH = 150              # Max characters in search snippet
MAX_SEARCH_RESULTS_KEPT = 5           # Max results kept in context
MAX_FORMATTED_RESULTS_LENGTH = 2000   # Max formatted string length

# Memory & File Storage
MAX_MEMORY_LIMIT = 200                # Max items returned by memory list
MEMORY_DB_PATH = "memories.db"        # SQLite database file path
MAX_FILE_LIMIT = 200                  # Max directory items returned by file list
FILE_ROOT_DIR = "agent_workspace"     # Default workspace directory
```

## 📝 Logging

All web search and URL operations are recorded in the `logs/` directory using the naming format `<module>_<timestamp>.log`, where `<timestamp>` reflects the agent launch time in `YYYYMMDD_HHMMSS` format:

- `web_search_<timestamp>.log` – All search queries, backend details, and search snippets
- `open_url_<timestamp>.log` – All URL requests, status codes, and extracted webpage content

Use `/log list` to view recent logs, `/log delete <filename>` to remove an individual log, and `/log clear_all` to safely wipe the log directory (active log files are automatically recreated).

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- [Rich](https://github.com/Textualize/rich) for beautiful terminal output and live rendering
- [DuckDuckGo Search (`ddgs`)](https://github.com/deedy5/duckduckgo_search) for web search capabilities
- [curl_cffi](https://github.com/lexiforest/curl_cffi) & [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) for robust web fetching and parsing

## ❓ FAQ

**Q: Can I use this with a local LLM (Ollama, vLLM, LM Studio)?**  
A: Yes! As long as the API endpoint supports OpenAI-compatible function calling. You can leave `OPENAI_API_KEY` blank or unset (it will fallback to `"placeholder"`) and point `OPENAI_API_URL` to your local endpoint (e.g., `http://localhost:11434/v1`).

**Q: Does this work across Windows, macOS, and Linux?**  
A: Yes! The agent includes UTF-8 stream reconfigurations for Windows consoles and cross-platform path handling for all operating systems.

**Q: Can the agent access my local files?**  
A: Yes, via `manage_files` and `run_python`, which operate with the privileges of the executing Python process. By default, relative file paths are isolated within `agent_workspace/`.

**Q: Where are memories stored?**  
A: Memories are stored locally in SQLite (`memories.db`) in the project root and persist across sessions.

**Q: Why do I see "Domain parking detected" or anti-bot messages?**  
A: The agent contains heuristic checks for parked domains, expired domain ads, and anti-bot verification walls to prevent feeding junk data into LLM context.
