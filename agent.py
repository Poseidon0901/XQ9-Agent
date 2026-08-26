from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
import json
from datetime import datetime
import os
from tools import TOOLS, web_search, open_url, run_python, manage_memories
from tools.manage_memories import get_memory_manager
import glob
from enum import Enum, auto
import io
import sys
import re
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()

API_URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")
MODEL = os.getenv("MODEL")

print("API_URL =", repr(API_URL))
print("MODEL =", repr(MODEL))
print("API_KEY =", repr(API_KEY[:10] + "...") if API_KEY else None)

MAX_TOTAL_TOOL_CALLS = 30
MAX_SEARCH_CALLS = 5
MAX_OPEN_URL_CALLS = 10

MAX_SNIPPET_LENGTH = 150
MAX_SEARCH_RESULTS_KEPT = 5
MAX_FORMATTED_RESULTS_LENGTH = 2000

class CommandResult(Enum):
    BREAK = auto()
    CONTINUE = auto()
    PROCESS = auto()

class App():
    def __init__(self):
        self.console = Console()

        self.client = OpenAI(
            base_url=API_URL,
            api_key=API_KEY
        )
        self.launch_timestamp = datetime.now().strftime('%Y-%m-%d.%H.%M.%S')

        self.last_search_results = []
        self.last_search_query = ""
        
        self.commands = {
            "exit": self.cmd_exit,
            "quit": self.cmd_exit,
            "clear": self.cmd_clear,
            "erase": self.cmd_clear,
            "clearlogs": self.cmd_clearlogs,
            "deletelogs": self.cmd_clearlogs,
            "logs": self.cmd_logs,
            "showlogs": self.cmd_logs,
        }
        
        self.system_message_zh_tw = ""
        self.system_message_en_us = ""
        with open("system_prompt_zh_tw.txt", "r", encoding="utf-8") as f:
            self.system_message_zh_tw = f.read()
        with open("system_prompt_en_us.txt", "r", encoding="utf-8") as f:
                    self.system_message_en_us = f.read()

        self.messages = []

        self.init_log_files()
        self.memory_manager = get_memory_manager()
        self._init_commands()

    def _init_commands(self):
        pass

    def init_log_files(self):
        self.log_dir = "logs"
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        
        self.web_search_log = os.path.join(self.log_dir, f"web_search_{self.launch_timestamp}.log")
        if not os.path.exists(self.web_search_log):
            with open(self.web_search_log, "w", encoding="utf-8") as f:
                f.write("# Web Search Log\n")
                f.write(f"# Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("# " + "="*70 + "\n\n")
        
        self.open_url_log = os.path.join(self.log_dir, f"open_url_{self.launch_timestamp}.log")
        if not os.path.exists(self.open_url_log):
            with open(self.open_url_log, "w", encoding="utf-8") as f:
                f.write("# Open URL Log\n")
                f.write(f"# Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("# " + "="*70 + "\n\n")

    def cmd_exit(self):
        return CommandResult.BREAK

    def cmd_clear(self):
        self.messages = []
        self.last_search_results = []
        self.last_search_query = ""
        self.console.print("[yellow]Conversation history cleared.[/yellow]")
        return CommandResult.CONTINUE

    def cmd_clearlogs(self):
        self.console.print("[yellow]Warning: Deleting all log file(s)! [/yellow]")
        confirm = self.console.input("[bold red]Are you sure？(y/N): [/bold red]")
        
        if confirm.lower() != 'y':
            self.console.print("[dim]Cancelled[/dim]")
            return CommandResult.CONTINUE

        log_pattern = os.path.join("logs", "*.log")
        log_files = glob.glob(log_pattern)
        
        if not log_files:
            self.console.print("[dim]No log file found. [/dim]")
            return CommandResult.CONTINUE
        
        deleted_count = 0
        for log_file in log_files:
            try:
                os.remove(log_file)
                self.console.print(f"[dim]Deleted: {os.path.basename(log_file)}[/dim]")
                deleted_count += 1
            except Exception as e:
                self.console.print(f"[red]Failed to delete {os.path.basename(log_file)}: {e}[/red]")
        
        self.console.print(f"[green]Deleted {deleted_count} log file(s).[/green]")

        self.init_log_files()
        self.console.print("[dim]Successfully created new log files.[/dim]")
        return CommandResult.CONTINUE
    
    def cmd_logs(self):
        log_files = glob.glob(os.path.join("logs", "*.log"))
        if not log_files:
            self.console.print("[dim]No log files found.[/dim]")
        else:
            self.console.print("[bold]Recent log files:[/bold]")
            for f in sorted(log_files, reverse=True)[:10]:
                size = os.path.getsize(f) // 1024
                self.console.print(f"  {os.path.basename(f)} ({size} KB)")
        return CommandResult.CONTINUE

    def command_handler(self, command: str) -> CommandResult:
        command = command.lstrip('/').lower()
        if command in self.commands:
            return self.commands[command]()
        return CommandResult.PROCESS

    def _extract_url_from_input(self, text: str) -> str | None:
        pattern = r'https?://[^\s\'"]+'
        match = re.search(pattern, text)
        if match:
            return match.group(0)
        return None

    def _add_url_to_search_results(self, url: str, query: str = None):
        if query is None:
            query = f"URL: {url}"

        for result in self.last_search_results:
            if result.get("url") == url:
                return

        self.last_search_results.append({
            "title": f"URL: {url}",
            "snippet": f"User provided URL: {url}",
            "url": url
        })
        
        self.last_search_query = query
        self.console.print(f"[green]✓ Added URL to search results:[/green] {url}")
        self.console.print(f"[dim]Use index {len(self.last_search_results)} to open it.[/dim]")

    def _format_search_results(self, results: list, query: str) -> str:
        if not results:
            return f"No result for: '{query}'"

        results_to_show = results[:MAX_SEARCH_RESULTS_KEPT]

        formatted = f"## Search results: {query}\n\n"

        for i, result in enumerate(results_to_show, 1):
            title = result.get('title', 'untitled')[:80]
            snippet = result.get('snippet', 'no snippet')[:MAX_SNIPPET_LENGTH]
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

    def _execute_web_search(self, query: str):
        self.console.print(f"[yellow]Searching:[/yellow] {query}")
        
        search_result = web_search(query, console=self.console, launch_timestamp=self.launch_timestamp)
        
        if search_result.get("error"):
            self.console.print(f"[red]Search error:[/red] {search_result['error']}")
            return {
                "error": search_result['error'],
                "results": []
            }
        
        results = search_result.get("results", [])

        compressed_results = []
        for r in results[:MAX_SEARCH_RESULTS_KEPT]:
            compressed_results.append({
                "title": r.get("title", "")[:100],
                "snippet": r.get("snippet", "")[:MAX_SNIPPET_LENGTH],
                "url": r.get("url", "")
            })
        
        self.last_search_results = compressed_results
        self.last_search_query = query
        
        if results:
            self.console.print(f"[green]Found {len(results)} search results[/green]")
            for i, r in enumerate(results[:3], 1):

                short_title = r['title'][:60] + ("..." if len(r['title']) > 60 else "")
                self.console.print(f"[dim]  {i}. {short_title} - {r['url']}[/dim]")

        search_result["results"] = compressed_results
        return search_result

    def _execute_open_url_by_index(self, index: int) -> dict:
        if not self.last_search_results:
            return {
                "error": "No available result. Please run web_search first.",
                "content": ""
            }
        
        if index < 1 or index > len(self.last_search_results):
            return {
                "error": f"Index {index} out of range. Valid range: 1-{len(self.last_search_results)}",
                "content": "",
                "available_indices": list(range(1, len(self.last_search_results) + 1))
            }

        selected_result = self.last_search_results[index - 1]
        url = selected_result.get("url")
        title = selected_result.get("title", "untitled")
        
        self.console.print(f"[yellow]Opening result #{index}:[/yellow] {title}")
        self.console.print(f"[dim]URL: {url}[/dim]")

        result = open_url(url, console=self.console, launch_timestamp=self.launch_timestamp)

        result["selected_index"] = index
        result["selected_title"] = title
        
        return result

    def _cleanup_old_messages(self):
        if len(self.messages) > 20:
            new_messages = [self.messages[0]]

            new_messages.extend(self.messages[-10:])
            
            self.messages = new_messages
            self.console.print("[dim]Part of the conversation history was cleaned up to save memory.[/dim]")

    def main(self):
        while True:
            try:
                user_input = self.console.input(
                    "[bold cyan]You > [/bold cyan]"
                )

                if user_input.lower().startswith("/"):
                    result = self.command_handler(user_input)
                    
                    if result == CommandResult.BREAK:
                        break
                    elif result == CommandResult.CONTINUE:
                        continue

                extracted_url = self._extract_url_from_input(user_input)
                if extracted_url:
                    self._add_url_to_search_results(extracted_url)
                    self.console.print(f"[dim]Detected URL: {extracted_url}[/dim]")

                if len(self.messages) == 0:
                    has_chinese = bool(re.search(r'[\u4e00-\u9fff\u3100-\u312f]', user_input))
                    self.messages.append({
                        "role": "system",
                        "content": self.system_message_zh_tw if has_chinese else self.system_message_en_us
                    })
                
                self.messages.append({
                    "role": "user",
                    "content": user_input
                })

                if len(self.messages) > 30:
                    self._cleanup_old_messages()

                searched_queries = set()
                visited_urls = set()
                total_tool_calls = 0
                search_calls = 0
                open_url_calls = 0

                while True:
                    response = self.client.chat.completions.create(
                        model=MODEL,
                        messages=self.messages,
                        tools=TOOLS,
                        tool_choice="auto",
                        extra_body={
                            "reasoning": True,
                            "reasoning_effort": "medium"
                        }
                    )

                    message = response.choices[0].message

                    reasoning = getattr(message, 'reasoning_content', None) or getattr(message, 'reasoning', None)

                    if reasoning:
                        self.console.print("\n[dim]Thinking:[/dim]")
                        self.console.print(Markdown(f"> {reasoning}"))
                        self.console.print("")

                    if not message.tool_calls:
                        answer = message.content or ""

                        self.messages.append({
                            "role": "assistant",
                            "content": answer
                        })

                        self.console.print("\n[bold green]AI >[/bold green]")
                        self.console.print(Markdown(answer))
                        self.console.print("\n")

                        break

                    self.messages.append({
                        "role": "assistant",
                        "content": message.content or "",
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": tool_call.function.name,
                                    "arguments": tool_call.function.arguments
                                }
                            }
                            for tool_call in message.tool_calls
                        ]
                    })

                    for tool_call in message.tool_calls:
                        tool_id = tool_call.id
                        function_name = tool_call.function.name

                        if total_tool_calls >= MAX_TOTAL_TOOL_CALLS:
                            self.console.print("[red]Maximum tool calls reached.[/red]")
                            self.messages.append({
                                "role": "tool",
                                "tool_call_id": tool_id,
                                "content": json.dumps({
                                    "error": "Maximum tool call limit reached. Please answer using the information already available."
                                }, ensure_ascii=False)
                            })
                            continue
                        
                        total_tool_calls += 1

                        try:
                            arguments = json.loads(tool_call.function.arguments)

                            if function_name == "web_search":
                                query = arguments.get("query", "").strip()
                                
                                if query.lower() in searched_queries:
                                    result = {
                                        "error": "You have already executed this search query. "
                                                "Do not repeat searches. Please answer the user using existing search results."
                                    }
                                else:
                                    searched_queries.add(query.lower())
                                    
                                    if search_calls >= MAX_SEARCH_CALLS:
                                        result = {"error": "Search limit reached."}
                                    else:
                                        search_calls += 1
                                        search_result = self._execute_web_search(query)
                                        
                                        if search_result.get("error"):
                                            result = search_result
                                        else:
                                            formatted_results = self._format_search_results(
                                                search_result.get("results", []),
                                                query
                                            )
                                            result = {
                                                "query": query,
                                                "results": search_result.get("results", []),
                                                "formatted": formatted_results,
                                                "total": len(search_result.get("results", []))
                                            }
                                            result["results"] = search_result.get("results", [])[:MAX_SEARCH_RESULTS_KEPT]

                            elif function_name == "open_url_by_index":
                                index = arguments.get("index", 0)
                                try:
                                    index = int(index)
                                except (ValueError, TypeError):
                                    result = {
                                        "error": f"Invalid index: {index}. Please submit an integer."
                                    }
                                else:
                                    if open_url_calls >= MAX_OPEN_URL_CALLS:
                                        result = {"error": "open_url_by_index limit reached."}
                                    else:
                                        open_url_calls += 1
                                        result = self._execute_open_url_by_index(index)

                            elif function_name == "run_python":
                                code = arguments.get("code", "")

                                if not code.strip():
                                    result = {
                                        "error": "No Python code provided."
                                    }
                                else:
                                    result = run_python(code, console=self.console)

                            elif function_name == "manage_memories":
                                operation = arguments.get("operation", "")
                                content = arguments.get("content", None)
                                memory_id = arguments.get("memory_id", None)
                                date = arguments.get("date", None)
                                time = arguments.get("time", None)
                                keyword = arguments.get("keyword", None)
                                
                                result = manage_memories(
                                    operation=operation,
                                    content=content,
                                    memory_id=memory_id,
                                    date=date,
                                    time=time,
                                    keyword=keyword,
                                    console=self.console
                                )

                            else:
                                result = {
                                    "error": f"Unknown function: {function_name}"
                                }

                        except Exception as e:
                            result = {"error": str(e), "type": type(e).__name__}

                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": json.dumps(result, ensure_ascii=False)
                        })

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Bye![/yellow]")
                break
            except Exception as e:
                self.console.print(f"[red]Error:[/red] {str(e)}")

if __name__ == "__main__":
    app = App()
    app.main()