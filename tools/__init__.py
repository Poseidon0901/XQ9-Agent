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
                        "type": "string"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Maximum execution time in seconds. (Default 10 seconds)"
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
            "description": "Manage external memories that persist across all conversations. Use this to store, retrieve, update, delete, or list important information. Operations: create (add new memory with content, optional date/time), read (retrieve memories by ID, date, or keyword search), update (modify existing memory by ID), delete (remove memory by ID), list (show all memories summary), clear_all (delete ALL memories - use with caution!).",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "Operation to perform: 'create', 'read', 'update', 'delete', 'list', or 'clear_all'",
                        "enum": ["create", "read", "update", "delete", "list", "clear_all"]
                    },
                    "memory_id": {
                        "type": "integer",
                        "description": "Memory ID (required for update and delete; optional for read to get specific memory)"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date filter in YYYY-MM-DD format (optional for read, or for create to set date)"
                    },
                    "time": {
                        "type": "string",
                        "description": "Time in HH:MM format (optional for create)"
                    },
                    "content": {
                        "type": "string",
                        "description": "IMPORTANT: For operation='create' or operation='update', put the COMPLETE MEMORY TEXT HERE. When updating a memory, the NEW TEXT MUST be placed in this field. NEVER put new memory content in 'keyword'."
                    },
                    "keyword": {
                        "type": "string",
                        "description": "IMPORTANT: ONLY use this field when operation='read' to SEARCH existing memories. NEVER use this field for create or update."
                    }
                },
                "required": ["operation"]
            }
        }
    }
]