import re


def has_chinese(text: str) -> bool:
    if not text:
        return False
    return bool(re.search(r"[\u4e00-\u9fff\u3100-\u312f]", text))
