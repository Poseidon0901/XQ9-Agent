import glob
import os

from tools.common_funcs import has_chinese
from tools.config import CommandResult


class CommandHandler:
    def __init__(self, app_instance, user_input: str = ""):
        self.app_instance = app_instance

    def cmd_exit(self):
        return CommandResult.BREAK

    def cmd_clear(self):
        self.app_instance.messages = []
        self.app_instance.last_search_results = []
        self.app_instance.last_search_query = ""
        self.app_instance.tool_handler.reset_counters()
        self.app_instance.console.print("[yellow]Conversation history cleared.[/yellow]")
        return CommandResult.CONTINUE

    def cmd_clearlogs(self):
        self.app_instance.console.print("[yellow]Warning: Deleting all log file(s)! [/yellow]")
        confirm = self.app_instance.console.input("[bold red]Are you sure？(y/N): [/bold red]")

        if confirm.lower() != 'y':
            self.app_instance.console.print("[dim]Cancelled[/dim]")
            return CommandResult.CONTINUE

        log_pattern = os.path.join("logs", "*.log")
        log_files = glob.glob(log_pattern)

        if not log_files:
            self.app_instance.console.print("[dim]No log file found. [/dim]")
            return CommandResult.CONTINUE

        deleted_count = 0
        for log_file in log_files:
            try:
                os.remove(log_file)
                self.app_instance.console.print(f"[dim]Deleted: {os.path.basename(log_file)}[/dim]")
                deleted_count += 1
            except Exception as e:
                self.app_instance.console.print(f"[red]Failed to delete {os.path.basename(log_file)}: {e}[/red]")

        self.app_instance.console.print(f"[green]Deleted {deleted_count} log file(s).[/green]")

        self.app_instance.init_log_files()
        self.app_instance.console.print("[dim]Successfully created new log files.[/dim]")
        return CommandResult.CONTINUE

    def cmd_logs(self):
        log_files = glob.glob(os.path.join("logs", "*.log"))
        if not log_files:
            self.app_instance.console.print("[dim]No log files found.[/dim]")
        else:
            self.app_instance.console.print("[bold]Recent log files:[/bold]")
            for f in sorted(log_files, reverse=True)[:10]:
                size = os.path.getsize(f) // 1024
                self.app_instance.console.print(f"  {os.path.basename(f)} ({size} KB)")
        return CommandResult.CONTINUE

    def cmd_togglesystemprompt(self):
        self.app_instance.use_system_prompt = not self.app_instance.use_system_prompt

        if self.app_instance.use_system_prompt:
            if not self.app_instance.messages or self.app_instance.messages[0]["role"] != "system":
                self.app_instance.messages.insert(0, {
                    "role": "system",
                    "status": "waiting for new system prompt",
                    "content": ""
                })
        else:
            if self.app_instance.messages and self.app_instance.messages[0]["role"] == "system":
                self.app_instance.messages.pop(0)

        status = "enabled" if self.app_instance.use_system_prompt else "disabled"
        self.app_instance.console.print(f"[yellow]System prompt {status}.[/yellow]")
        return CommandResult.CONTINUE

    def cmd_toggletools(self):
        self.app_instance.use_tools = not self.app_instance.use_tools
        status = "enabled" if self.app_instance.use_tools else "disabled"

        if self.app_instance.use_system_prompt:
            if self.app_instance.messages and self.app_instance.messages[0]["role"] == "system":
                self.app_instance.messages[0]["content"] = self.app_instance.get_system_prompt(has_chinese(self.app_instance.messages[0]["content"]))
            else:
                self.app_instance.messages.insert(0, {
                    "role": "system",
                    "content": self.app_instance.get_system_prompt(False)
                })

        self.app_instance.console.print(f"[yellow]Tools {status}.[/yellow]")
        return CommandResult.CONTINUE

    def execute(self, command: str) -> CommandResult:
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
