from .manage_files import get_file_manager, manage_files
from .manage_memories import get_memory_manager, manage_memories
from .open_url import open_url
from .run_python import run_python
from .web_search import web_search

__all__ = [
    "get_file_manager",
    "get_memory_manager",
    "manage_files",
    "manage_memories",
    "open_url",
    "run_python",
    "web_search",
]

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the internet for current or unknown information. Returns a list of search results with titles, snippets, and URLs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to use for the web search."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_url_by_index",
            "description": "Open a search result by index. Use this to open any URL that is in the search results list. This includes URLs that the user directly provided (they are automatically added to the search results). NEVER use this unless the URL is in the search results list.",
            "parameters": {
                "type": "object",
                "properties": {
                    "index": {
                        "type": "integer",
                        "description": "The index number (1-based) from the most recent search results."
                    }
                },
                "required": ["index"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Execute Python code locally for computation, data processing, or testing. Do NOT use this to read or write files - use manage_files instead. Choose an appropriate timeout.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute."
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Maximum execution time in seconds. (Default 10 seconds, max 300)"
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_memories",
            "description": """Manage persistent memories stored in SQLite3 database (memories.db). Memories persist across all conversations.

Operations:
- create: Store new memory. Requires content. Optional date (YYYY-MM-DD) and time (HH:MM).
- read: Retrieve memories. Can filter by memory_id, date, or keyword search.
- update: Modify existing memory. Requires memory_id and new content.
- delete: Remove a memory. Requires memory_id.
- list: Show all memories summary (most recent first, max 200).
- clear_all: Delete ALL memories - use with extreme caution!

Memory System Features:
- SQLite3 database for better performance and query capabilities
- Automatic indexing on date and created_at for fast searches
- Supports keyword search with LIKE queries
- All memories are stored locally in memories.db

Always query first before creating/updating to avoid duplicates.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "Operation to perform",
                        "enum": ["create", "read", "update", "delete", "list", "clear_all"]
                    },
                    "memory_id": {
                        "type": "integer",
                        "description": "Memory ID (required for update, delete; optional for read)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Memory content. REQUIRED for create and update. Put the full text here."
                    },
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (optional for create/read)"
                    },
                    "time": {
                        "type": "string",
                        "description": "Time in HH:MM format (optional for create)"
                    },
                    "keyword": {
                        "type": "string",
                        "description": "Search keyword for read operation. Searches within memory content using SQL LIKE."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results for list operation (default 20, max 200)"
                    }
                },
                "required": ["operation"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_files",
            "description": """Manage persistent files stored in the local filesystem.

**ALWAYS use this tool for ANY file operation (read, write, update, delete, list). Do NOT use run_python for file operations.**

By default, files are stored in the `agent_workspace/` directory. You can specify a different location by providing a `file_path`:
- Bare filename (e.g., "notes.txt") → placed in `agent_workspace/`
- Path with directory components (e.g., "subdir/notes.txt") → placed in `agent_workspace/subdir/`
- Absolute path (e.g., "C:\\Users\\Blackcat\\Documents\\test.txt") → used as-is

Operations:
- create: Create a new file. Requires content. Optional file_path (default: untitled_<timestamp>.txt in agent_workspace).
- read: Retrieve file contents. Requires file_path.
- update: Modify existing file contents. Requires file_path and content.
- delete: Remove a file. Requires file_path.
- list: Show all files in the specified directory. Optional file_path (default: agent_workspace). Optional limit (default 20, max 200).
- clear_all: Delete ALL files in the specified directory. Requires file_path (must not be the root agent_workspace).

Examples:
- Read a file in workspace: manage_files(operation="read", file_path="test.txt")
- Read a file outside workspace: manage_files(operation="read", file_path="C:\\\\Users\\\\Blackcat\\\\Documents\\\\test.txt")
- List workspace: manage_files(operation="list") (no file_path needed)
- List a specific directory: manage_files(operation="list", file_path="C:\\\\Users\\\\Blackcat\\\\Documents")
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "Operation to perform",
                        "enum": ["create", "read", "update", "delete", "list", "clear_all"]
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file or directory. If not provided, defaults to agent_workspace for create and list. For read/update/delete, this is required. Absolute paths (e.g., 'C:\\\\Users\\\\Blackcat\\\\Documents\\\\test.txt') are supported."
                    },
                    "content": {
                        "type": "string",
                        "description": "File content. REQUIRED for create and update. Put the full text here."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results for list operation (default 20, max 200)"
                    }
                },
                "required": ["operation"]
            }
        }
    }
]