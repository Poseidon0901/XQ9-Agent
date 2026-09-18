import os
import shutil
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from rich.console import Console

from .config import MAX_FILE_LIMIT, FILE_ROOT_DIR


class FileManager:
    def __init__(self, root_dir: str = FILE_ROOT_DIR):
        self.root_dir = Path(root_dir).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, file_path: str) -> Path:
        if not file_path or not str(file_path).strip():
            raise ValueError("file_path cannot be empty")

        p = Path(file_path)
        if not p.is_absolute():
            p = self.root_dir / p

        resolved = p.resolve()

        if self.root_dir != resolved and self.root_dir not in resolved.parents:
            raise ValueError(
                f"Access denied: '{file_path}' is outside the allowed root "
                f"directory ({self.root_dir})"
            )
        return resolved

    def create_file(
        self,
        content: str,
        file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
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

    def read_file(self, file_path: str) -> Dict[str, Any]:
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
                    "modified_at": datetime.fromtimestamp(
                        stat.st_mtime
                    ).isoformat(),
                },
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to read file: {e}"}

    def update_file(self, file_path: str, content: str) -> Dict[str, Any]:
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
                    "modified_at": datetime.fromtimestamp(
                        stat.st_mtime
                    ).isoformat(),
                },
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to update file: {e}"}

    def delete_file(self, file_path: str) -> Dict[str, Any]:
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

    def list_files(
        self,
        directory: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        limit = max(1, min(int(limit), MAX_FILE_LIMIT))

        try:
            base = self._resolve(directory) if directory else self.root_dir
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
                        "modified_at": datetime.fromtimestamp(
                            stat.st_mtime
                        ).isoformat(),
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

    def clear_all(self, directory: Optional[str] = None) -> Dict[str, Any]:
        try:
            base = self._resolve(directory) if directory else self.root_dir
        except ValueError as e:
            return {"success": False, "error": str(e)}

        if not base.exists() or not base.is_dir():
            return {"success": False, "error": f"Directory not found: {base}"}

        if base == self.root_dir:
            return {
                "success": False,
                "error": (
                    "Refusing to clear the root directory. "
                    "Specify a subdirectory (e.g. 'temp')."
                ),
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


_file_manager: Optional[FileManager] = None


def get_file_manager() -> FileManager:
    global _file_manager
    if _file_manager is None:
        _file_manager = FileManager()
    return _file_manager


def manage_files(
    operation: str,
    file_path: Optional[str] = None,
    content: Optional[str] = None,
    date: Optional[str] = None,
    time: Optional[str] = None,
    keyword: Optional[str] = None,
    console: Optional[Console] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    manager = get_file_manager()
    operation = operation.lower().strip()

    if console:
        console.print("\n[bold cyan]╔══════════════════════════════════════════════════════════════╗[/bold cyan]")
        console.print("[bold cyan]║           📁 FILE OPERATION - PARAMETERS                     ║[/bold cyan]")
        console.print("[bold cyan]╚══════════════════════════════════════════════════════════════╝[/bold cyan]")
        console.print(f"[bold yellow]Operation:[/bold yellow] {operation}")
        console.print(f"[bold yellow]File path:[/bold yellow] {file_path if file_path else '(None)'}")
        console.print(
            f"[bold yellow]Content:[/bold yellow] "
            f"{repr(content[:80]) + '...' if content and len(content) > 80 else repr(content)}"
        )
        console.print(f"[bold yellow]Limit:[/bold yellow] {limit}")
        console.print("[dim]─" * 60 + "[/dim]\n")

    try:
        if operation == "create":
            result = manager.create_file(content=content, file_path=file_path)

        elif operation == "read":
            if not file_path:
                return {
                    "success": False,
                    "error": "file_path is required for read operation",
                }
            result = manager.read_file(file_path)

        elif operation == "update":
            if not file_path:
                return {
                    "success": False,
                    "error": "file_path is required for update operation",
                }
            result = manager.update_file(file_path, content)

        elif operation == "delete":
            if not file_path:
                return {
                    "success": False,
                    "error": "file_path is required for delete operation",
                }
            result = manager.delete_file(file_path)

        elif operation == "list":
            result = manager.list_files(directory=file_path, limit=limit)

        elif operation == "clear_all":
            result = manager.clear_all(directory=file_path)

        else:
            return {
                "success": False,
                "error": (
                    f"Unknown operation: {operation}. "
                    "Supported: create, read, update, delete, list, clear_all"
                ),
            }

    except Exception as e:
        if console:
            console.print(f"[red]✗ File operation failed:[/red] {e}")
        return {"success": False, "error": f"File operation failed: {e}"}

    if console:
        if result.get("success"):
            console.print(f"[green]✓ {result.get('message', 'OK')}[/green]")
            if "file" in result and "content" in result["file"]:
                preview = result["file"]["content"][:200]
                console.print(f"[dim]  Content preview: {preview}[/dim]")
            elif "entries" in result:
                for e in result["entries"]:
                    console.print(
                        f"[dim]  [{e['type']}] {e['name']} "
                        f"({e['size']} bytes)[/dim]"
                    )
        else:
            console.print(f"[red]✗ {result.get('error')}[/red]")

    return result