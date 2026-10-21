import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console

from tools.config import FILE_ROOT_DIR, MAX_FILE_LIMIT, FileOperation


def _safe_print(console: Console | None, *args, **kwargs) -> None:
    if not console:
        return
    try:
        console.print(*args, **kwargs)
    except Exception:
        pass


class FileManager:
    def __init__(self, root_dir: str = FILE_ROOT_DIR):
        self.root_dir = Path(root_dir).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, file_path: str) -> Path:
        if not file_path or not str(file_path).strip():
            raise ValueError("file_path cannot be empty")

        p = Path(file_path)
        if p.is_absolute():
            return p.resolve()

        return (self.root_dir / p).resolve()

    def create_file(self, content: str, file_path: str | None = None) -> dict[str, Any]:
        if content is None:
            return {"success": False, "error": "Content is required for create"}

        if not file_path:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = f"untitled_{ts}.txt"

        try:
            target = self._resolve(file_path)
        except ValueError as e:
            return {"success": False, "error": str(e)}

        if target.exists():
            return {
                "success": False,
                "error": f"File already exists: {target}. Use update instead.",
            }

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            stat = target.stat()
            return {
                "success": True,
                "message": f"File created: {target}",
                "file": {
                    "path": str(target),
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                },
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to create file: {e}"}

    def read_file(self, file_path: str) -> dict[str, Any]:
        try:
            target = self._resolve(file_path)
        except ValueError as e:
            return {"success": False, "error": str(e)}

        if not target.exists():
            return {"success": False, "error": f"File not found: {target}"}
        if not target.is_file():
            return {"success": False, "error": f"Not a file: {target}"}

        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            stat = target.stat()
            return {
                "success": True,
                "message": f"File read: {target}",
                "file": {
                    "path": str(target),
                    "content": content,
                    "size": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                },
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to read file: {e}"}

    def update_file(self, file_path: str, content: str) -> dict[str, Any]:
        if content is None:
            return {"success": False, "error": "Content is required for update"}

        try:
            target = self._resolve(file_path)
        except ValueError as e:
            return {"success": False, "error": str(e)}

        if not target.exists():
            return {"success": False, "error": f"File not found: {target}"}
        if not target.is_file():
            return {"success": False, "error": f"Not a file: {target}"}

        try:
            target.write_text(content, encoding="utf-8")
            stat = target.stat()
            return {
                "success": True,
                "message": f"File updated: {target}",
                "file": {
                    "path": str(target),
                    "size": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                },
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to update file: {e}"}

    def delete_file(self, file_path: str) -> dict[str, Any]:
        try:
            target = self._resolve(file_path)
        except ValueError as e:
            return {"success": False, "error": str(e)}

        if not target.exists():
            return {"success": False, "error": f"File not found: {target}"}

        try:
            if target.is_file():
                target.unlink()
            else:
                shutil.rmtree(target)
            return {
                "success": True,
                "message": f"Deleted: {target}",
                "path": str(target),
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to delete: {e}"}

    def list_files(self, directory: str | None = None, limit: int = 20) -> dict[str, Any]:
        limit = max(1, min(int(limit), MAX_FILE_LIMIT))

        if directory is None or str(directory).strip() == "":
            base = self.root_dir
        else:
            try:
                base = self._resolve(directory)
            except ValueError as e:
                return {"success": False, "error": str(e)}

        if not base.exists():
            return {"success": False, "error": f"Directory not found: {base}"}
        if not base.is_dir():
            return {"success": False, "error": f"Not a directory: {base}"}

        entries = []
        for entry in sorted(base.iterdir(), key=lambda p: p.name.lower()):
            try:
                stat = entry.stat()
                entries.append(
                    {
                        "name": entry.name,
                        "path": str(entry),
                        "type": "dir" if entry.is_dir() else "file",
                        "size": stat.st_size if entry.is_file() else None,
                        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    }
                )
            except Exception:
                continue

            if len(entries) >= limit:
                break

        return {
            "success": True,
            "message": f"Found {len(entries)} entries in {base}",
            "directory": str(base),
            "entries": entries,
            "total_shown": len(entries),
        }

    def clear_all(self, directory: str | None = None) -> dict[str, Any]:
        if directory is None or str(directory).strip() == "":
            return {
                "success": False,
                "error": "Refusing to clear without a directory. Specify a subdirectory (e.g. 'temp').",
            }

        try:
            base = self._resolve(directory)
        except ValueError as e:
            return {"success": False, "error": str(e)}

        if not base.exists() or not base.is_dir():
            return {"success": False, "error": f"Directory not found: {base}"}

        if base == self.root_dir:
            return {
                "success": False,
                "error": "Refusing to clear the root directory. Specify a subdirectory (e.g. 'temp').",
            }

        deleted = 0
        for entry in base.iterdir():
            try:
                if entry.is_file() or entry.is_symlink():
                    entry.unlink()
                else:
                    shutil.rmtree(entry)
                deleted += 1
            except Exception:
                continue

        return {
            "success": True,
            "message": f"Cleared {deleted} entries in {base}",
            "deleted_count": deleted,
        }


_file_manager: FileManager | None = None


def get_file_manager() -> FileManager:
    global _file_manager
    if _file_manager is None:
        _file_manager = FileManager()
    return _file_manager


def manage_files(
    operation: FileOperation | str,
    file_path: str | None = None,
    content: str | None = None,
    console: Console | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    manager = get_file_manager()

    try:
        op = FileOperation(str(operation).strip().lower())
    except (ValueError, AttributeError):
        supported = ", ".join(o.value for o in FileOperation)
        err_msg = f"Unknown operation: '{operation}'. Supported operations: {supported}"
        _safe_print(console, f"[red]✗ {err_msg}[/red]")
        return {"success": False, "error": err_msg}

    _safe_print(
        console,
        "\n[bold cyan]╔══════════════════════════════════════════════════════════════╗[/bold cyan]",
    )
    _safe_print(
        console,
        "[bold cyan]║           📁 FILE OPERATION - PARAMETERS                     ║[/bold cyan]",
    )
    _safe_print(
        console,
        "[bold cyan]╚══════════════════════════════════════════════════════════════╝[/bold cyan]",
    )
    _safe_print(console, f"[bold yellow]Operation:[/bold yellow] {op.value}")
    _safe_print(
        console,
        f"[bold yellow]File path:[/bold yellow] {file_path if file_path else '(None)'}",
    )
    _safe_print(
        console,
        f"[bold yellow]Content:[/bold yellow] "
        f"{repr(content[:80]) + '...' if content and len(content) > 80 else repr(content)}",
    )
    _safe_print(console, f"[bold yellow]Limit:[/bold yellow] {limit}")
    _safe_print(console, "[dim]─" * 60 + "[/dim]\n")

    try:
        match op:
            case FileOperation.CREATE:
                result = manager.create_file(content=content, file_path=file_path)

            case FileOperation.READ:
                if not file_path:
                    return {
                        "success": False,
                        "error": "file_path is required for read operation",
                    }
                result = manager.read_file(file_path)

            case FileOperation.UPDATE:
                if not file_path:
                    return {
                        "success": False,
                        "error": "file_path is required for update operation",
                    }
                result = manager.update_file(file_path, content)

            case FileOperation.DELETE:
                if not file_path:
                    return {
                        "success": False,
                        "error": "file_path is required for delete operation",
                    }
                result = manager.delete_file(file_path)

            case FileOperation.LIST:
                result = manager.list_files(directory=file_path, limit=limit)

            case FileOperation.CLEAR_ALL:
                result = manager.clear_all(directory=file_path)

    except Exception as e:
        _safe_print(console, f"[red]✗ File operation failed:[/red] {e}")
        return {"success": False, "error": f"File operation failed: {e}"}

    if result.get("success"):
        _safe_print(console, f"[green]✓ {result.get('message', 'OK')}[/green]")
        if "file" in result and "content" in result["file"]:
            preview = result["file"]["content"][:200]
            _safe_print(console, f"[dim]  Content preview: {preview}[/dim]")
        elif "entries" in result:
            for e in result["entries"]:
                _safe_print(console, f"[dim]  [{e['type']}] {e['name']} ({e['size']} bytes)[/dim]")
    else:
        _safe_print(console, f"[red]✗ {result.get('error')}[/red]")

    return result
