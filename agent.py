import io
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

from tools import TOOLS
from tools.commands import CommandHandler
from tools.common_funcs import format_as_blockquote, has_chinese
from tools.config import CommandResult
from tools.handler import ToolHandler
from tools.logs import get_log_manager
from tools.manage_memories import get_memory_manager

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    try:
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")
    except Exception:
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


class App:
    def __init__(self):
        self.console = Console()

        self.client = OpenAI(base_url=API_URL, api_key=API_KEY)
        self.launch_timestamp = datetime.now().strftime("%Y-%m-%d.%H.%M.%S")

        self.last_search_results = []
        self.last_search_query = ""

        self.use_system_prompt = True
        self.use_tools = True

        self.tool_handler = ToolHandler(self)
        self.command_handler = CommandHandler(self)

        self.system_message_zh_tw = Path("system_prompt_zh_tw.txt").read_text(encoding="utf-8")
        self.system_message_en_us = Path("system_prompt_en_us.txt").read_text(encoding="utf-8")
        self.system_message_zh_tw_no_tools = Path("system_prompt_zh_tw_no_tools.txt").read_text(
            encoding="utf-8"
        )
        self.system_message_en_us_no_tools = Path("system_prompt_en_us_no_tools.txt").read_text(
            encoding="utf-8"
        )
        self.system_message_pending = False

        self.messages = []

        self.log_manager = get_log_manager()
        self.memory_manager = get_memory_manager()

    def _extract_url_from_input(self, text: str) -> str | None:
        pattern = (
            r'(?:https?://|www\.)[^\s\'"]+|[\w-]+\.(?:com|org|net|tw|jp|io|dev|ai|app)[^\s\'"]*'
        )
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            url = match.group(0)
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            return url
        return None

    def get_system_prompt(self, is_chinese_present: bool):
        if self.use_tools:
            return self.system_message_zh_tw if is_chinese_present else self.system_message_en_us
        else:
            return (
                self.system_message_zh_tw_no_tools
                if is_chinese_present
                else self.system_message_en_us_no_tools
            )

    def update_system_prompt(self, is_chinese_present: bool):
        system_prompt = self.get_system_prompt(is_chinese_present)

        if not self.messages:
            self.messages.append({"role": "system", "content": system_prompt})
        else:
            self.messages[0] = {"role": "system", "content": system_prompt}

        self.system_message_pending = False

    def is_system_prompt_existing(self):
        return bool(self.messages and self.messages[0]["role"] == "system")

    def _cleanup_old_messages(self):
        if len(self.messages) <= 20:
            return

        new_messages = []
        if self.messages and self.messages[0]["role"] == "system":
            new_messages.append(self.messages[0])

        recent = self.messages[-10:]

        while recent and recent[0]["role"] == "tool":
            idx = len(self.messages) - len(recent) - 1
            if idx >= 0:
                recent.insert(0, self.messages[idx])
            else:
                break

        new_messages.extend(recent)
        self.messages = new_messages
        self.console.print(
            "[dim]Part of the conversation history was cleaned up to save memory.[/dim]"
        )

    def main(self):
        while True:
            try:
                user_input = self.console.input("[bold cyan]You > [/bold cyan]")

                if user_input.lower().startswith("/"):
                    result = self.command_handler.execute(user_input)
                    if result == CommandResult.BREAK:
                        break
                    elif result == CommandResult.CONTINUE:
                        continue

                self.tool_handler.reset_turn_counters()

                extracted_url = self._extract_url_from_input(user_input)
                if extracted_url:
                    self.tool_handler.add_url_to_search_results(extracted_url)
                    self.console.print(f"[dim]Detected URL: {extracted_url}[/dim]")

                if self.use_system_prompt:
                    is_chinese_present = has_chinese(user_input)

                    system_prompt_changed = False

                    if not self.messages or self.system_message_pending:
                        self.update_system_prompt(is_chinese_present)
                        system_prompt_changed = True

                    if system_prompt_changed:
                        self.console.print(
                            "[yellow]Using zh_tw system prompt[/yellow]"
                            if is_chinese_present
                            else "[yellow]Using en_us system prompt[/yellow]"
                        )

                self.messages.append({"role": "user", "content": user_input})

                if len(self.messages) > 30:
                    self._cleanup_old_messages()

                while True:
                    kwargs = {
                        "model": MODEL,
                        "messages": self.messages,
                        "extra_body": {"reasoning": True, "reasoning_effort": "medium"},
                    }

                    if self.use_tools:
                        kwargs["tools"] = TOOLS
                        kwargs["tool_choice"] = "auto"

                    kwargs["stream"] = True

                    try:
                        stream = self.client.chat.completions.create(**kwargs)
                    except Exception as api_err:
                        self.console.print(f"[red]LLM API call failed: {api_err}[/red]")
                        break

                    self.console.print("\n[bold green]AI >[/bold green]")

                    full_content = ""
                    reasoning_content = ""
                    tool_calls_dict = {}

                    try:
                        with Live(
                            Markdown(""), console=self.console, refresh_per_second=10
                        ) as live:
                            for chunk in stream:
                                if not chunk.choices:
                                    continue

                                delta = chunk.choices[0].delta

                                reasoning = getattr(delta, "reasoning_content", None) or getattr(
                                    delta, "reasoning", None
                                )
                                if reasoning:
                                    reasoning_content += reasoning
                                    live.update(
                                        Markdown(
                                            f"*Thinking...*\n\n{format_as_blockquote(reasoning_content)}"
                                        )
                                    )
                                if delta.content:
                                    full_content += delta.content
                                    if reasoning_content:
                                        live.update(
                                            Markdown(
                                                f"*Thinking...*\n\n{format_as_blockquote(reasoning_content)}\n\n{full_content}"
                                            )
                                        )
                                    else:
                                        live.update(Markdown(full_content))
                                if delta.tool_calls:
                                    for tc in delta.tool_calls:
                                        index = tc.index
                                        if index not in tool_calls_dict:
                                            tool_calls_dict[index] = {
                                                "id": tc.id or "",
                                                "name": tc.function.name
                                                if tc.function and tc.function.name
                                                else "",
                                                "arguments": "",
                                            }
                                        if tc.id:
                                            tool_calls_dict[index]["id"] = tc.id
                                        if tc.function:
                                            if tc.function.name:
                                                tool_calls_dict[index]["name"] = tc.function.name
                                            if tc.function.arguments:
                                                tool_calls_dict[index]["arguments"] += (
                                                    tc.function.arguments
                                                )

                    except KeyboardInterrupt:
                        try:
                            stream.response.close()
                        except Exception:
                            pass

                        self.client.close()

                        self.client = OpenAI(base_url=API_URL, api_key=API_KEY)

                        self.console.print("\n[yellow]Generation interrupted.[/yellow]")
                        break

                    self.console.print("\n")

                    if not tool_calls_dict:
                        self.messages.append(
                            {
                                "role": "assistant",
                                "content": full_content,
                            }
                        )
                        break

                    formatted_tool_calls = [
                        {
                            "id": tool_data["id"],
                            "type": "function",
                            "function": {
                                "name": tool_data["name"],
                                "arguments": tool_data["arguments"],
                            },
                        }
                        for tool_data in tool_calls_dict.values()
                    ]

                    self.messages.append(
                        {
                            "role": "assistant",
                            "content": full_content or "",
                            "tool_calls": formatted_tool_calls,
                        }
                    )

                    for tool_call in formatted_tool_calls:
                        tool_id = tool_call["id"]
                        function_name = tool_call["function"]["name"]
                        raw_args = tool_call["function"]["arguments"]
                        try:
                            arguments = json.loads(raw_args)
                            result = self.tool_handler.execute(function_name, arguments)
                        except json.JSONDecodeError as e:
                            result = {
                                "error": f"Failed to parse tool arguments: {e!s}",
                                "type": "JSONDecodeError",
                            }
                        except Exception as e:
                            result = {"error": str(e), "type": type(e).__name__}

                        self.messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_id,
                                "content": json.dumps(result, ensure_ascii=False),
                            }
                        )

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Bye![/yellow]")
                break
            except Exception as e:
                self.console.print(f"[red]Error:[/red] {e!s}")


if __name__ == "__main__":
    app = App()
    app.main()
