from .config import FileOperation, MemoryOperation, SearchStrategy
from .manage_files import get_file_manager, manage_files
from .manage_memories import get_memory_manager, manage_memories
from .open_url import open_url
from .run_python import run_python
from .web_search import web_search

__all__ = [
    "TOOLS",
    "FileOperation",
    "MemoryOperation",
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
            "description": (
                "Search the internet for up-to-date information, current events, "
                "technical documentation, or unknown facts. "
                "Returns an indexed list of search results containing 1-based "
                "index numbers, titles, URLs, and brief snippets.\n\n"
                "Usage Rules:\n"
                "- Formulate queries targeting the direct answer concisely — "
                "do NOT search for intermediate info (e.g. today's date).\n"
                "- Use the 'auto' strategy for general web searches. "
                "Use '_search_ddgs' for web search and '_search_wikipedia_api' "
                "for encyclopedia-style information.\n"
                "- Search results provide only brief snippets. After calling "
                "web_search, you MUST call open_url_by_index using the result "
                "index number to read the full page content before providing "
                "the final answer to the user.\n"
                "- Avoid repeated or duplicate searches."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "The search query targeting the answer directly. "
                            "Use concise keywords without filler words."
                        ),
                    },
                    "strategy": {
                        "type": "string",
                        "enum": [strategy.value for strategy in SearchStrategy],
                        "description": (
                            "Search strategy. Use 'auto' for general searches, "
                            "'_search_ddgs' for web searches, or "
                            "'_search_wikipedia_api' for encyclopedia information. "
                            "Defaults to 'auto' when omitted."
                        ),
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_url_by_index",
            "description": (
                "Open and extract the cleaned full-text content of a webpage by its 1-based index from the current search results list.\n\n"
                "Usage Rules:\n"
                "- Only use index numbers present in the most recent search results list (or user-provided URLs automatically added to the list).\n"
                "- NEVER invent or guess an index outside the valid range (1 to total results).\n"
                "- Prioritize opening results whose titles match the user's inquiry most directly. For time-sensitive queries, "
                "prefer titles with 'current', 'today', 'live', or 'now'.\n"
                "- Features built-in anti-bot challenge detection and domain parking / advertisement page filtering."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "index": {
                        "type": "integer",
                        "description": "The 1-based index integer of the target result from the most recent search results list (e.g., 1, 2, 3).",
                    }
                },
                "required": ["index"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": (
                "Execute Python code locally in the current execution environment for mathematical calculations, data processing, "
                "algorithm testing, or querying system datetime (via the datetime module).\n\n"
                "Restrictions & Rules:\n"
                "- Do NOT use this tool for reading, writing, updating, listing, or deleting files — use manage_files instead.\n"
                "- Standard output (print) and error streams are captured and returned in 'stdout', 'stderr', and 'returncode'.\n"
                "- Choose an appropriate execution timeout (default 10s, max 300s)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Valid Python code snippet to execute. Use print() to output results.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Maximum execution time in seconds (allowed range: 1 to 300, default: 10).",
                        "minimum": 1,
                        "maximum": 300,
                        "default": 10,
                    },
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_memories",
            "description": (
                "Manage persistent memories stored in a local SQLite3 database (memories.db). Memories persist across all conversations.\n\n"
                "Supported Operations:\n"
                "- 'create': Store a new memory. Requires 'content'. Optional 'date' (YYYY-MM-DD) and 'time' (HH:MM), defaults to current.\n"
                "- 'read': Retrieve memories. Can filter by 'memory_id' (exact ID), 'date' (exact date), or 'keyword' (content LIKE search).\n"
                "- 'update': Modify an existing memory. Requires 'memory_id' and new 'content'.\n"
                "- 'delete': Remove a memory. Requires 'memory_id'.\n"
                "- 'list': Show recent memories ordered by creation time (newest first). Optional 'limit' (default 20, max 200).\n"
                "- 'clear_all': Delete ALL memories from the database. Use with extreme caution and only on explicit user request.\n\n"
                "Best Practice: Always query first ('read') before creating or updating to prevent duplicates."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "The memory management operation to execute.",
                        "enum": [op.value for op in MemoryOperation],
                    },
                    "memory_id": {
                        "type": "integer",
                        "description": "The unique memory ID. Required for 'update' and 'delete'; optional filter for 'read'.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The text content of the memory. REQUIRED for 'create' and 'update'. Note: this stores full text, distinct from 'keyword'.",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (e.g., '2026-10-21'). Optional for 'create' or filter for 'read'.",
                    },
                    "time": {
                        "type": "string",
                        "description": "Time in HH:MM format (e.g., '14:30'). Optional for 'create'.",
                    },
                    "keyword": {
                        "type": "string",
                        "description": "Search keyword for 'read' operation. Performs a case-insensitive LIKE search within memory content.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return for 'list' operation (default: 20, max: 200).",
                        "minimum": 1,
                        "maximum": 200,
                        "default": 20,
                    },
                },
                "required": ["operation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_files",
            "description": (
                "Manage persistent files stored in the local filesystem. ALWAYS use this tool for ANY file operation "
                "(reading, writing, updating, deleting, listing) instead of run_python.\n\n"
                "Path Resolution Rules:\n"
                "- Bare filename (e.g., 'notes.txt') → resolved inside 'agent_workspace/'\n"
                "- Relative path with directories (e.g., 'subdir/notes.txt') → resolved inside 'agent_workspace/subdir/'\n"
                "- Absolute path (e.g., 'C:\\Users\\...\\file.txt' or '/home/.../file.txt') → accessed as-is\n\n"
                "Supported Operations:\n"
                "- 'create': Create a new file with 'content'. Optional 'file_path' (defaults to 'untitled_<timestamp>.txt' in agent_workspace). Fails if file already exists.\n"
                "- 'read': Retrieve full text content of a file. Requires 'file_path'.\n"
                "- 'update': Overwrite existing file with new 'content'. Requires 'file_path' and 'content'. Fails if file does not exist.\n"
                "- 'delete': Remove a file or directory. Requires 'file_path'.\n"
                "- 'list': Show entries (name, type, size, modified_at) in a directory. Optional 'file_path' (defaults to agent_workspace). Optional 'limit'.\n"
                "- 'clear_all': Delete all files in a specified directory. Requires 'file_path' (must be a subdirectory; refuses to clear root agent_workspace)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "The file operation to perform.",
                        "enum": [op.value for op in FileOperation],
                    },
                    "file_path": {
                        "type": "string",
                        "description": (
                            "Path to the target file or directory. Defaults to 'agent_workspace' for 'create' and 'list'. "
                            "Required for 'read', 'update', 'delete', and 'clear_all'. Both relative and absolute paths are supported."
                        ),
                    },
                    "content": {
                        "type": "string",
                        "description": "The text content to write into the file. REQUIRED for 'create' and 'update'.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of directory entries to return for 'list' operation (default: 20, max: 200).",
                        "minimum": 1,
                        "maximum": 200,
                        "default": 20,
                    },
                },
                "required": ["operation"],
            },
        },
    },
]
