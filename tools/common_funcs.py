import re
from urllib.parse import urlparse, urlunparse


def get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def normalize_url(url: str) -> str:
    try:
        parsed = urlparse(url)

        if not parsed.netloc or "." not in parsed.netloc:
            raise ValueError("Invalid domain")

        if not parsed.scheme:
            url = "https://" + url
            parsed = urlparse(url)

        return urlunparse(
            (parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/"), "", "", "")
        )
    except Exception:
        return url


def has_chinese(text: str) -> bool:
    if not text:
        return False
    return bool(re.search(r"[\u4e00-\u9fff\u3100-\u312f]", text))


def format_as_blockquote(text: str) -> str:
    lines = text.split("\n")
    return "\n".join(f"> {line}" if line else ">" for line in lines)
