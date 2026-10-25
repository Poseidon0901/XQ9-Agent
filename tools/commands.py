import shlex

from tools.common_funcs import has_chinese
from tools.config import CommandResult


class CommandHandler:
    def __init__(self, app_instance):
        self.app_instance = app_instance

    def cmd_exit(self):
        return CommandResult.BREAK

    def cmd_clear(self):
        self.app_instance.messages = []
        self.app_instance.last_search_results = []
        self.app_instance.last_search_query = ""
        self.app_instance.system_message_pending = False
        self.app_instance.tool_handler.reset_counters()
        self.app_instance.console.print("[yellow]Conversation history cleared.[/yellow]")
        return CommandResult.CONTINUE

    def _clear_all_logs(self) -> CommandResult:
        app = self.app_instance
        console = app.console

        console.print("[yellow]Warning: This will delete ALL log files![/yellow]")
        confirm = console.input("[bold red]Are you sure? (y/N): [/bold red]")

        if confirm.strip().lower() not in ("y", "yes"):
            console.print("[dim]Cancelled[/dim]")
            return CommandResult.CONTINUE

        result = app.log_manager.clear_all_logs()

        if not result.get("success"):
            console.print(f"[red]{result.get('error')}[/red]")
            return CommandResult.CONTINUE

        console.print(f"[green]{result.get('message')}[/green]")
        for failure in result.get("failed", []):
            console.print(f"[red]Failed to delete {failure['file']}: {failure['error']}[/red]")
        console.print("[dim]Active log files re-created.[/dim]")
        return CommandResult.CONTINUE

    def cmd_log(self, args: list[str]) -> CommandResult:
        log_manager = self.app_instance.log_manager
        console = self.app_instance.console
        usage = "/log <list [limit] | delete <filename> | clear_all>"

        if not args:
            console.print(f"[red]Missing operation. Usage: {usage}[/red]")
            return CommandResult.CONTINUE

        operation = args[0].lower()

        if operation == "list":
            limit = 10
            if len(args) > 1:
                try:
                    limit = int(args[1])
                except ValueError:
                    console.print(f"[red]Invalid limit: '{args[1]}'. Must be an integer.[/red]")
                    return CommandResult.CONTINUE

            result = log_manager.list_logs(limit)
            if not result.get("success"):
                console.print(f"[red]{result.get('error')}[/red]")
                return CommandResult.CONTINUE

            logs = result.get("logs", [])
            if not logs:
                console.print("[dim]No log files found.[/dim]")
                return CommandResult.CONTINUE

            console.print(
                f"[bold]Recent log files:[/bold] "
                f"[dim]({len(logs)}/{result.get('total', len(logs))})[/dim]"
            )
            for entry in logs:
                size_kb = entry["size"] / 1024
                modified = entry["modified_at"].replace("T", " ")[:19]
                console.print(
                    f"  [cyan]{entry['name']}[/cyan] [dim]({size_kb:.1f} KB, {modified})[/dim]"
                )
            return CommandResult.CONTINUE

        if operation == "delete":
            if len(args) < 2:
                console.print("[red]Usage: /log delete <filename>[/red]")
                return CommandResult.CONTINUE

            result = log_manager.delete_log(args[1])
            if result.get("success"):
                console.print(f"[green]{result.get('message')}[/green]")
            else:
                console.print(f"[red]{result.get('error')}[/red]")
            return CommandResult.CONTINUE

        if operation == "clear_all":
            return self._clear_all_logs()

        console.print(
            f"[red]Unknown log operation: '{operation}'. Available: list, delete, clear_all[/red]"
        )
        return CommandResult.CONTINUE

    def _infer_is_chinese(self) -> bool:
        app = self.app_instance

        for message in reversed(app.messages):
            if message.get("role") == "user":
                return has_chinese(message.get("content") or "")

        if app.is_system_prompt_existing():
            return has_chinese(app.messages[0].get("content") or "")

        return False

    def _set_system_prompt(self, is_enable: bool) -> None:
        app = self.app_instance
        app.use_system_prompt = is_enable

        if is_enable:
            if not app.is_system_prompt_existing():
                app.system_message_pending = True
        else:
            if app.is_system_prompt_existing():
                app.messages.pop(0)
            app.system_message_pending = False

        status = "enabled" if is_enable else "disabled"
        app.console.print(f"[yellow]System prompt {status}.[/yellow]")

    def _set_tools(self, is_enable: bool) -> None:
        app = self.app_instance
        app.use_tools = is_enable

        if app.use_system_prompt:
            is_chinese = self._infer_is_chinese()
            if app.is_system_prompt_existing():
                app.update_system_prompt(is_chinese)
            else:
                app.system_message_pending = True

        status = "enabled" if is_enable else "disabled"
        app.console.print(f"[yellow]Tools {status}.[/yellow]")

    def cmd_set(self, args: list[str]) -> CommandResult:
        console = self.app_instance.console
        usage = "/set <system_prompt|tools> <enable|disable>"

        if not args:
            console.print(f"[red]Nothing to set. Usage: {usage}[/red]")
            return CommandResult.CONTINUE

        target_aliases = {
            "system_prompt": "system_prompt",
            "prompt": "system_prompt",
            "tools": "tools",
        }
        target = target_aliases.get(args[0].lower())
        if target is None:
            console.print(
                f"[red]Unknown setting: '{args[0]}'. "
                "Available: system_prompt (alias: prompt), tools[/red]"
            )
            return CommandResult.CONTINUE

        if len(args) < 2:
            console.print(f"[red]Missing value for '{args[0]}'. Usage: {usage}[/red]")
            return CommandResult.CONTINUE

        status_aliases = {
            "enable": True,
            "on": True,
            "true": True,
            "disable": False,
            "off": False,
            "false": False,
        }
        is_enable = status_aliases.get(args[1].lower())
        if is_enable is None:
            console.print(f"[red]Invalid status: '{args[1]}'. Use 'enable' or 'disable'.[/red]")
            return CommandResult.CONTINUE

        if target == "system_prompt":
            self._set_system_prompt(is_enable)
        else:
            self._set_tools(is_enable)

        return CommandResult.CONTINUE

    def execute(self, raw_input: str) -> CommandResult:
        try:
            parts = shlex.split(raw_input.lstrip("/"))
        except ValueError as e:
            self.app_instance.console.print(f"[red]Wrong command syntax: {e}[/red]")
            return CommandResult.CONTINUE

        if not parts:
            return CommandResult.CONTINUE

        command = parts[0].lower()
        args = parts[1:]

        match command:
            case "exit" | "quit":
                return self.cmd_exit()
            case "clear":
                return self.cmd_clear()
            case "log":
                return self.cmd_log(args)
            case "set":
                return self.cmd_set(args)
            case _:
                self.app_instance.console.print(f"[red]Unknown command: /{command}[/red]")
                return CommandResult.CONTINUE
