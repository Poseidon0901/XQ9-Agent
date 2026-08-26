from .open_url import open_url
from .web_search import web_search
from .run_python import run_python
from .manage_memories import manage_memories, get_memory_manager

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
            "description": """Manage external memories that persist across all conversations.

Operations:
- create: Store new memory. Requires content. Optional date (YYYY-MM-DD) and time (HH:MM).
- read: Retrieve memories. Can filter by memory_id, date, or keyword search.
- update: Modify existing memory. Requires memory_id and new content.
- delete: Remove a memory. Requires memory_id.
- list: Show all memories summary (most recent first).
- clear_all: Delete ALL memories - use with extreme caution!

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
                        "description": "Search keyword for read operation. Searches within memory content."
                    }
                },
                "required": ["operation"]
            }
        }
    }
]