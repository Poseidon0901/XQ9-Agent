from .open_url import open_url
from .web_search import web_search
from .run_python import run_python
from .manage_memories import manage_memories, get_memory_manager
from .manage_files import manage_files, get_file_manager

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
            "description": "Execute Python code locally. Choose an appropriate timeout.",
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

Operations:
- create: Create a new file. Requires content.
- read: Retrieve file contents.
- update: Modify existing file contents. Requires file path and new content.
- delete: Remove a file. Requires file path.
- list: Show all files in the specified directory.
- clear_all: Delete ALL files in the specified directory - use with extreme caution!
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
                        "description": "Path to the file (required for update, delete, read; optional for create)"
                    },
                    "content": {
                        "type": "string",
                        "description": "File content. REQUIRED for create and update. Put the full text here."
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
                        "description": "Search keyword for read operation."
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
]