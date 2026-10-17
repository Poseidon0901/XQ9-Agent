import glob
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console

from tools.config import LogResult

class LogManager:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir).resolve()
        self.launch_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logs: dict[str, Path] = {}
        self._init_log_dir()

    def _init_log_dir(self) -> LogResult:
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            return LogResult.SUCCESS
        except Exception:
            return LogResult.FAILURE

    def _log_path(self, name: str) -> Path:
        return self.log_dir / f"{name}_{self.launch_timestamp}.log"

    def _write_header(self, path: Path, name: str) -> None:
        if path.exists():
            return
        path.write_text(
            f"# {name.replace('_', ' ').title()} Log\n"
            f"# Created: {datetime.now():%Y-%m-%d %H:%M:%S}\n"
            f"# {'=' * 70}\n\n",
            encoding="utf-8",
        )

    def init_log_files(self, name: str | None = None) -> LogResult:
        if name is None:
            return LogResult.SUCCESS

        try:
            path = self._log_path(name)
            self._write_header(path, name)
            self.logs[name] = path
            return LogResult.SUCCESS
        except Exception:
            return LogResult.FAILURE

    def list_logs(self, limit: int = 20) -> dict[str, Any]:
        limit = max(1, min(int(limit), 200))

        try:
            files = sorted(
                glob.glob(os.path.join(self.log_dir, "*.log")),
                key=os.path.getmtime,
                reverse=True,
            )
        except Exception as e:
            return {"success": False, "error": f"Failed to list logs: {e!s}"}

        entries = []
        for f in files[:limit]:
            try:
                stat = os.stat(f)
                entries.append({
                    "name": os.path.basename(f),
                    "path": f,
                    "size": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
            except Exception:
                continue

        return {
            "success": True,
            "message": f"Found {len(entries)} log file(s) (total: {len(files)})",
            "logs": entries,
            "total": len(files),
        }

    def clear_all_logs(self) -> dict[str, Any]:
        try:
            files = glob.glob(os.path.join(self.log_dir, "*.log"))
        except Exception as e:
            return {"success": False, "error": f"Failed to scan logs: {e!s}"}

        deleted = 0
        failed = []
        for f in files:
            try:
                os.remove(f)
                deleted += 1
            except Exception as e:
                failed.append({"file": os.path.basename(f), "error": str(e)})

        for name in list(self.logs.keys()):
            self.init_log_files(name)

        return {
            "success": True,
            "message": f"Deleted {deleted} log file(s)",
            "deleted_count": deleted,
            "failed": failed,
        }

    def write_log(self, name: str, message: str) -> LogResult:
        if name not in self.logs:
            result = self.init_log_files(name)
            if result == LogResult.FAILURE:
                return LogResult.FAILURE

        try:
            with open(self.logs[name], "a", encoding="utf-8") as f:
                f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}\n\n{message}\n")
            return LogResult.SUCCESS
        except Exception:
            return LogResult.FAILURE


_log_manager: LogManager | None = None


def get_log_manager() -> LogManager:
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager()
    return _log_manager