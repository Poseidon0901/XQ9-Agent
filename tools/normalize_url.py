from urllib.parse import urlparse, urlunparse

def normalize_url(url: str) -> str:
    try:
        parsed = urlparse(url)

        if not parsed.netloc or '.' not in parsed.netloc:
            raise ValueError("Invalid domain")

        if not parsed.scheme:
            url = "https://" + url
            parsed = urlparse(url)
        
        return urlunparse((
            parsed.scheme,
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            "",
            "",
            ""
        ))
    except Exception:
        return url