from enum import Enum, StrEnum, auto

MAX_TOTAL_TOOL_CALLS = 30
MAX_SEARCH_CALLS = 5
MAX_OPEN_URL_CALLS = 10
MAX_RUN_PYTHON_CALLS = 15
MAX_MEMORY_CALLS = 10
MAX_FILE_CALLS = 15

MAX_SNIPPET_LENGTH = 150
MAX_SEARCH_RESULTS_KEPT = 5
MAX_FORMATTED_RESULTS_LENGTH = 2000

MAX_MEMORY_LIMIT = 200
MEMORY_DB_PATH = "memories.db"

MAX_FILE_LIMIT = 200
FILE_ROOT_DIR = "agent_workspace"


class CommandResult(Enum):
    BREAK = auto()
    CONTINUE = auto()
    PROCESS = auto()


class LogResult(Enum):
    SUCCESS = auto()
    FAILURE = auto()


class MemoryOperation(StrEnum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"
    CLEAR_ALL = "clear_all"


class FileOperation(StrEnum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"
    CLEAR_ALL = "clear_all"
