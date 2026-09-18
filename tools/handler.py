from typing import Dict, Any
from tools import web_search, open_url, run_python, manage_memories, manage_files
from tools.config import (
    MAX_TOTAL_TOOL_CALLS,
    MAX_SEARCH_CALLS,
    MAX_OPEN_URL_CALLS,
    MAX_SNIPPET_LENGTH,
    MAX_SEARCH_RESULTS_KEPT,
    MAX_FORMATTED_RESULTS_LENGTH
)

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

        self.max_search_calls = MAX_SEARCH_CALLS
        self.max_open_url_calls = MAX_OPEN_URL_CALLS
        self.max_total_tool_calls = MAX_TOTAL_TOOL_CALLS

        self.search_calls = 0
        self.open_url_calls = 0
        self.total_tool_calls = 0

        self.searched_queries = set()

    def execute(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if self.total_tool_calls >= self.max_total_tool_calls:
            return {
                "error": "Maximum total tool calls reached. Please answer using the information already available."
            }
        
        handler = self.handlers.get(name)
        if not handler:
            return {
                "error": f"Unknown function: {name}"
            }

        self.total_tool_calls += 1
        
        try:
            return handler(args)
        except Exception as e:
            return {
                "error": f"Tool execution failed: {str(e)}",
                "type": type(e).__name__
            }

    def handle_web_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = args.get("query", "").strip()
        
        if not query:
            return {"error": "Search query cannot be empty"}

        query_key = query.lower()
        if query_key in self.searched_queries:
            return {
                "error": "You have already executed this search query. "
                        "Do not repeat searches. Please answer the user using existing search results."
            }

        if self.search_calls >= self.max_search_calls:
            return {"error": "Search limit reached."}

        self.searched_queries.add(query_key)
        self.search_calls += 1

        self.app.console.print(f"[yellow]Searching:[/yellow] {query}")
        search_result = web_search(
            query, 
            console=self.app.console, 
            launch_timestamp=self.app.launch_timestamp
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
                short_title = r.get('title', '')[:60]
                if len(r.get('title', '')) > 60:
                    short_title += "..."
                self.app.console.print(f"[dim]  {i}. {short_title} - {r.get('url', '')}[/dim]")

        formatted_results = self._format_search_results(compressed_results, query)
        
        return {
            "query": query,
            "results": compressed_results,
            "formatted": formatted_results,
            "total": len(compressed_results)
        }

    def handle_open_url_by_index(self, args: Dict[str, Any]) -> Dict[str, Any]:
        index = args.get("index")

        try:
            index = int(index)
        except (ValueError, TypeError):
            return {
                "error": f"Invalid index: {index}. Please submit an integer."
            }

        if self.open_url_calls >= self.max_open_url_calls:
            return {"error": "open_url_by_index limit reached."}

        if not self.app.last_search_results:
            return {
                "error": "No available results. Please run web_search first.",
                "content": ""
            }
        
        if index < 1 or index > len(self.app.last_search_results):
            return {
                "error": f"Index {index} out of range. Valid range: 1-{len(self.app.last_search_results)}",
                "content": "",
                "available_indices": list(range(1, len(self.app.last_search_results) + 1))
            }

        self.open_url_calls += 1

        selected_result = self.app.last_search_results[index - 1]
        url = selected_result.get("url")
        title = selected_result.get("title", "Untitled")
        
        self.app.console.print(f"[yellow]Opening result #{index}:[/yellow] {title}")
        self.app.console.print(f"[dim]URL: {url}[/dim]")

        result = open_url(
            url, 
            console=self.app.console, 
            launch_timestamp=self.app.launch_timestamp
        )
        
        result["selected_index"] = index
        result["selected_title"] = title
        
        return result

    def handle_run_python(self, args: Dict[str, Any]) -> Dict[str, Any]:
        code = args.get("code", "")
        timeout = args.get("timeout", 10)
        
        if not code or not code.strip():
            return {"error": "No Python code provided."}
        
        return run_python(
            code=code,
            timeout=timeout,
            console=self.app.console
        )

    def handle_manage_memories(self, args: Dict[str, Any]) -> Dict[str, Any]:
        operation = args.get("operation", "")
        limit = args.get("limit", 20)
        
        result = manage_memories(
            operation=operation,
            content=args.get("content"),
            memory_id=args.get("memory_id"),
            date=args.get("date"),
            time=args.get("time"),
            keyword=args.get("keyword"),
            console=self.app.console,
            limit=limit
        )
        
        return result

    def handle_manage_files(self, args: Dict[str, Any]) -> Dict[str, Any]:
        operation = args.get("operation", "")
        limit = args.get("limit", 20)

        result = manage_files(
            operation=operation,
            file_path=args.get("file_path"),
            content=args.get("content"),
            date=args.get("date"),
            time=args.get("time"),
            keyword=args.get("keyword"),
            console=self.app.console,
            limit=limit,
        )

        return result

    def _compress_results(self, results: list) -> list:
        compressed = []
        for r in results[:MAX_SEARCH_RESULTS_KEPT]:
            compressed.append({
                "title": r.get("title", "")[:100],
                "snippet": r.get("snippet", "")[:MAX_SNIPPET_LENGTH],
                "url": r.get("url", "")
            })
        return compressed

    def _format_search_results(self, results: list, query: str) -> str:
        if not results:
            return f"No result for: '{query}'"
        
        results_to_show = results[:MAX_SEARCH_RESULTS_KEPT]
        
        formatted = f"## Search results: {query}\n\n"
        
        for i, result in enumerate(results_to_show, 1):
            title = result.get('title', 'Untitled')[:80]
            snippet = result.get('snippet', 'No snippet')[:MAX_SNIPPET_LENGTH]
            if len(result.get('snippet', '')) > MAX_SNIPPET_LENGTH:
                snippet += "..."
            
            formatted += f"**[{i}] {title}**\n"
            formatted += f"{snippet}\n"
            formatted += f"Index: {i}\n\n"
        
        if len(results) > MAX_SEARCH_RESULTS_KEPT:
            formatted += f"\n*({len(results) - MAX_SEARCH_RESULTS_KEPT} more results are available via index lookup.)*\n"
        
        formatted += f"\n**Use open_url_by_index(index) to retrieve full content.**\n"
        formatted += f"**Valid index range: 1-{len(results)}**"
        
        if len(formatted) > MAX_FORMATTED_RESULTS_LENGTH:
            formatted = formatted[:MAX_FORMATTED_RESULTS_LENGTH] + "\n... (content truncated)"
        
        return formatted

    def add_url_to_search_results(self, url: str, query: str = None) -> None:
        if query is None:
            query = f"URL: {url}"

        for result in self.app.last_search_results:
            if result.get("url") == url:
                return

        self.app.last_search_results.append({
            "title": f"URL: {url}",
            "snippet": f"User provided URL: {url}",
            "url": url
        })
        
        self.app.last_search_query = query
        self.app.console.print(f"[green]✓ Added URL to search results:[/green] {url}")
        self.app.console.print(f"[dim]Use index {len(self.app.last_search_results)} to open it.[/dim]")

    def reset_counters(self):
        self.search_calls = 0
        self.open_url_calls = 0
        self.total_tool_calls = 0
        self.searched_queries.clear()