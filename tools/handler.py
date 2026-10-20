from collections import deque
from typing import Any

from tools import manage_files, manage_memories, open_url, run_python, web_search
from tools.config import (
    MAX_FILE_CALLS,
    MAX_FORMATTED_RESULTS_LENGTH,
    MAX_MEMORY_CALLS,
    MAX_OPEN_URL_CALLS,
    MAX_RUN_PYTHON_CALLS,
    MAX_SEARCH_CALLS,
    MAX_SEARCH_RESULTS_KEPT,
    MAX_SNIPPET_LENGTH,
    MAX_TOTAL_TOOL_CALLS,
)

SEARCHED_QUERIES_MAXLEN = 50


class ToolHandler:
    def __init__(self, app_instance):
        self.app = app_instance
        self.handlers = {
            "web_search": self.handle_web_search,
            "open_url_by_index": self.handle_open_url_by_index,
            "run_python": self.handle_run_python,
            "manage_memories": self.handle_manage_memories,
            "manage_files": self.handle_manage_files,
        }

        self.tool_limits = {
            "web_search": MAX_SEARCH_CALLS,
            "open_url_by_index": MAX_OPEN_URL_CALLS,
            "run_python": MAX_RUN_PYTHON_CALLS,
            "manage_memories": MAX_MEMORY_CALLS,
            "manage_files": MAX_FILE_CALLS,
        }

        self.searched_queries: deque[str] = deque(maxlen=SEARCHED_QUERIES_MAXLEN)
        self.reset_turn_counters()

    def reset_turn_counters(self):
        self.total_tool_calls = 0
        self.tool_counts = {name: 0 for name in self.tool_limits}

    def reset_counters(self):
        self.reset_turn_counters()
        self.searched_queries.clear()

    def execute(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        handler = self.handlers.get(name)
        if not handler:
            return {"error": f"Unknown function: {name}"}

        limit = self.tool_limits.get(name)
        if limit is not None and self.tool_counts[name] >= limit:
            return {
                "error": f"{name} limit reached for this turn ({limit}). "
                "Use the information you already have."
            }

        if self.total_tool_calls >= MAX_TOTAL_TOOL_CALLS:
            return {
                "error": f"Maximum total tool calls reached for this turn "
                f"({MAX_TOTAL_TOOL_CALLS}). Answer using existing information."
            }

        self.tool_counts[name] += 1
        self.total_tool_calls += 1

        try:
            return handler(args)
        except Exception as e:
            return {"error": f"Tool execution failed: {e!s}", "type": type(e).__name__}

    def handle_web_search(self, args: dict[str, Any]) -> dict[str, Any]:
        query = args.get("query", "").strip()
        if not query:
            return {"error": "Search query cannot be empty"}

        query_key = query.lower()
        if query_key in self.searched_queries:
            return {
                "error": "You have already executed this search query. "
                "Do not repeat searches."
            }

        self.searched_queries.append(query_key)

        self.app.console.print(f"[yellow]Searching:[/yellow] {query}")
        search_result = web_search(
            query, console=self.app.console, launch_timestamp=self.app.launch_timestamp
        )

        if search_result.get("error"):
            return search_result

        results = search_result.get("results", [])
        compressed_results = self._compress_results(results)

        self.app.last_search_results = compressed_results
        self.app.last_search_query = query

        if results:
            self.app.console.print(f"[green]Found {len(results)} search results[/green]")
            for i, r in enumerate(results[:3], 1):
                short_title = r.get("title", "")[:60]
                if len(r.get("title", "")) > 60:
                    short_title += "..."
                self.app.console.print(
                    f"[dim]  {i}. {short_title} - {r.get('url', '')}[/dim]"
                )

        formatted_results = self._format_search_results(compressed_results, query)

        return {
            "query": query,
            "results": compressed_results,
            "formatted": formatted_results,
            "total": len(compressed_results),
        }

    def handle_open_url_by_index(self, args: dict[str, Any]) -> dict[str, Any]:
        index = args.get("index")

        try:
            index = int(index)
        except (ValueError, TypeError):
            return {"error": f"Invalid index: {index}. Please submit an integer."}

        if not self.app.last_search_results:
            return {
                "error": "No available results. Please run web_search first.",
                "content": "",
            }

        if index < 1 or index > len(self.app.last_search_results):
            return {
                "error": (
                    f"Index {index} out of range. "
                    f"Valid range: 1-{len(self.app.last_search_results)}"
                ),
                "content": "",
                "available_indices": list(range(1, len(self.app.last_search_results) + 1)),
            }

        selected_result = self.app.last_search_results[index - 1]
        url = selected_result.get("url")
        title = selected_result.get("title", "Untitled")

        self.app.console.print(f"[yellow]Opening result #{index}:[/yellow] {title}")
        self.app.console.print(f"[dim]URL: {url}[/dim]")

        result = open_url(url, console=self.app.console)

        result["selected_index"] = index
        result["selected_title"] = title

        return result

    def handle_run_python(self, args: dict[str, Any]) -> dict[str, Any]:
        code = args.get("code", "")
        timeout = args.get("timeout", 10)

        if not code or not code.strip():
            return {"error": "No Python code provided."}

        return run_python(code=code, timeout=timeout, console=self.app.console)

    def handle_manage_memories(self, args: dict[str, Any]) -> dict[str, Any]:
        operation = args.get("operation", "")
        limit = args.get("limit", 20)

        return manage_memories(
            operation=operation,
            content=args.get("content"),
            memory_id=args.get("memory_id"),
            date=args.get("date"),
            time=args.get("time"),
            keyword=args.get("keyword"),
            console=self.app.console,
            limit=limit,
        )

    def handle_manage_files(self, args: dict[str, Any]) -> dict[str, Any]:
        operation = args.get("operation", "")
        limit = args.get("limit", 20)

        return manage_files(
            operation=operation,
            file_path=args.get("file_path"),
            content=args.get("content"),
            date=args.get("date"),
            time=args.get("time"),
            keyword=args.get("keyword"),
            console=self.app.console,
            limit=limit,
        )
    
    def _compress_results(self, results: list) -> list:
        compressed = []
        for r in results[:MAX_SEARCH_RESULTS_KEPT]:
            compressed.append(
                {
                    "title": r.get("title", "")[:100],
                    "snippet": r.get("snippet", "")[:MAX_SNIPPET_LENGTH],
                    "url": r.get("url", ""),
                }
            )
        return compressed

    def _format_search_results(self, results: list, query: str) -> str:
        if not results:
            return f"No result for: '{query}'"

        results_to_show = results[:MAX_SEARCH_RESULTS_KEPT]

        formatted = f"## Search results: {query}\n\n"

        for i, result in enumerate(results_to_show, 1):
            title = result.get("title", "Untitled")[:80]
            snippet = result.get("snippet", "No snippet")[:MAX_SNIPPET_LENGTH]
            if len(result.get("snippet", "")) > MAX_SNIPPET_LENGTH:
                snippet += "..."

            formatted += f"**[{i}] {title}**\n"
            formatted += f"{snippet}\n"
            formatted += f"Index: {i}\n\n"

        if len(results) > MAX_SEARCH_RESULTS_KEPT:
            formatted += (
                f"\n*({len(results) - MAX_SEARCH_RESULTS_KEPT} more results "
                "are available via index lookup.)*\n"
            )

        formatted += "\n**Use open_url_by_index(index) to retrieve full content.**\n"
        formatted += f"**Valid index range: 1-{len(results)}**"

        if len(formatted) > MAX_FORMATTED_RESULTS_LENGTH:
            formatted = formatted[:MAX_FORMATTED_RESULTS_LENGTH] + "\n... (content truncated)"

        return formatted

    def add_url_to_search_results(self, url: str, query: str | None = None) -> None:
        if query is None:
            query = f"URL: {url}"

        for result in self.app.last_search_results:
            if result.get("url") == url:
                return

        self.app.last_search_results.append(
            {"title": f"URL: {url}", "snippet": f"User provided URL: {url}", "url": url}
        )

        self.app.last_search_query = query
        self.app.console.print(f"[green]✓ Added URL to search results:[/green] {url}")
        self.app.console.print(
            f"[dim]Use index {len(self.app.last_search_results)} to open it.[/dim]"
        )