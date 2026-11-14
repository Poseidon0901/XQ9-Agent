from rich.console import Console


def safe_print(console: Console | None, *args, **kwargs) -> None:
    if not console:
        return
    try:
        console.print(*args, **kwargs)
    except Exception:
        pass
