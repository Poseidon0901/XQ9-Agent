from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
import json
from datetime import datetime
import os
from pathlib import Path
from tools import TOOLS
from tools.manage_memories import get_memory_manager
from tools.handler import ToolHandler
import glob
from enum import Enum, auto
import sys
import re
from dotenv import load_dotenv

from tools.config import MAX_TOTAL_TOOL_CALLS

if sys.platform == "win32":
    try:
        import subprocess
        subprocess.run("chcp 65001 > nul", shell=True, capture_output=True)
    except Exception:
        pass
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

load_dotenv()

API_URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")
MODEL = os.getenv("MODEL")

if API_URL:
    print("API_URL =", repr(API_URL))
if MODEL:
    print("MODEL =", repr(MODEL))
if API_KEY:
    print(f"API_KEY = {f'{API_KEY[:10]}...' if len(API_KEY) > 10 else '***'}")


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

        self.use_system_prompt = True
        self.use_tools = True

        self.tool_handler = ToolHandler(self)

        self.system_message_zh_tw = Path("system_prompt_zh_tw.txt").read_text(encoding="utf-8")
        self.system_message_en_us = Path("system_prompt_en_us.txt").read_text(encoding="utf-8")

        self.messages = []

        self.init_log_files()
        self.memory_manager = get_memory_manager()

    def init_log_files(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        self.web_search_log = self.log_dir / f"web_search_{self.launch_timestamp}.log"
        if not self.web_search_log.exists():
            self.web_search_log.write_text(
                f"# Web Search Log\n# Created: {datetime.now():%Y-%m-%d %H:%M:%S}\n# {'='*70}\n\n",
                encoding="utf-8"
            )
        
        self.open_url_log = self.log_dir / f"open_url_{self.launch_timestamp}.log"
        if not self.open_url_log.exists():
            self.open_url_log.write_text(
                f"# Open URL Log\n# Created: {datetime.now():%Y-%m-%d %H:%M:%S}\n# {'='*70}\n\n",
                encoding="utf-8"
            )

    def cmd_exit(self):
        return CommandResult.BREAK

    def cmd_clear(self):
        self.messages = []
        self.last_search_results = []
        self.last_search_query = ""
        self.tool_handler.reset_counters()
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

    def cmd_togglesystemprompt(self):
        self.use_system_prompt = not self.use_system_prompt

        if self.use_system_prompt:
            if not self.messages or self.messages[0]["role"] != "system":
                self.messages.insert(0, {
                    "role": "system",
                    "status": "waiting for new system prompt",
                    "content": ""
                })
        else:
            if self.messages and self.messages[0]["role"] == "system":
                self.messages.pop(0)

        status = "enabled" if self.use_system_prompt else "disabled"
        self.console.print(f"[yellow]System prompt {status}.[/yellow]")
        return CommandResult.CONTINUE

    def cmd_toggletools(self):
        self.use_tools = not self.use_tools
        status = "enabled" if self.use_tools else "disabled"
        self.console.print(f"[yellow]Tools {status}.[/yellow]")
        return CommandResult.CONTINUE

    def command_handler(self, command: str) -> CommandResult:
        match command.lstrip('/').lower():
            case "exit" | "quit":
                return self.cmd_exit()
            case "clear" | "erase":
                return self.cmd_clear()
            case "clearlogs" | "deletelogs":
                return self.cmd_clearlogs()
            case "logs" | "showlogs":
                return self.cmd_logs()
            case "togglesystemprompt":
                return self.cmd_togglesystemprompt()
            case "toggletools":
                return self.cmd_toggletools()
            case _:
                return CommandResult.PROCESS

    def _extract_url_from_input(self, text: str) -> str | None:
        pattern = r'https?://[^\s\'"]+'
        match = re.search(pattern, text)
        if match:
            return match.group(0)
        return None

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
                    self.tool_handler.add_url_to_search_results(extracted_url)
                    self.console.print(f"[dim]Detected URL: {extracted_url}[/dim]")

                if self.use_system_prompt:
                    has_chinese = bool(re.search(r'[\u4e00-\u9fff\u3100-\u312f]', user_input))
                    system_prompt = self.system_message_zh_tw if has_chinese else self.system_message_en_us
                    system_prompt_changed = False
                    if len(self.messages) == 0:
                        self.messages.append({
                            "role": "system",
                            "content": system_prompt
                        })
                        system_prompt_changed = True
                    elif self.messages[0].get("status") == "waiting for new system prompt":
                        self.messages.pop(0)
                        self.messages.insert(0, {
                            "role": "system",
                            "content": system_prompt
                        })
                        system_prompt_changed = True

                    if system_prompt_changed:
                        self.console.print(
                            "[yellow]Using zh_tw system prompt[/yellow]"
                            if has_chinese
                            else "[yellow]Using en_us system prompt[/yellow]"
                        )

                self.messages.append({
                    "role": "user",
                    "content": user_input
                })

                if len(self.messages) > 30:
                    self._cleanup_old_messages()

                total_tool_calls = 0

                while True:
                    kwargs = {
                        "model": MODEL,
                        "messages": self.messages,
                        "extra_body": {
                            "reasoning": True,
                            "reasoning_effort": "medium"
                        }
                    }

                    if self.use_tools:
                        kwargs["tools"] = TOOLS
                        kwargs["tool_choice"] = "auto"


                    response = self.client.chat.completions.create(
                        **kwargs
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
                            result = {
                                "error": "Maximum tool call limit reached. Please answer using the information already available."
                            }
                            self.messages.append({
                                "role": "tool",
                                "tool_call_id": tool_id,
                                "content": json.dumps(result, ensure_ascii=False)
                            })
                            continue
                        
                        total_tool_calls += 1

                        try:
                            arguments = json.loads(tool_call.function.arguments)
                            result = self.tool_handler.execute(function_name, arguments)
                        except json.JSONDecodeError as e:
                            result = {
                                "error": f"Failed to parse tool arguments: {str(e)}",
                                "type": "JSONDecodeError"
                            }
                        except Exception as e:
                            result = {
                                "error": str(e),
                                "type": type(e).__name__
                            }

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