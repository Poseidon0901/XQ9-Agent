import json
import re
import urllib.parse
from datetime import datetime

from bs4 import BeautifulSoup
from curl_cffi import requests
from rich.console import Console

from tools.common_funcs import get_domain
from tools.logs import get_log_manager

TRUSTED_DOMAINS = {
    "github.com", "gitlab.com", "bitbucket.org", "stackoverflow.com",
    "stackexchange.com", "reddit.com", "medium.com", "dev.to",
    "wikipedia.org", "wikimedia.org", "archive.org", "gov", "edu",
    "mozilla.org", "python.org", "pypi.org", "npmjs.com", "docker.com",
    "kubernetes.io", "cnn.com", "bbc.com", "reuters.com", "ap.org",
    "nytimes.com", "wsj.com", "bloomberg.com", "economist.com",
    "nature.com", "science.org", "arxiv.org", "ieee.org", "acm.org",
    "springer.com", "elsevier.com", "jstor.org", "google.com",
    "youtube.com", "amazon.com", "microsoft.com", "apple.com",
}

TITLE_SUSPICIOUS_PATTERNS = {
    r"(?i)domain\s*(for\s*sale|is\s*for\s*sale|parking|parked)": 15,
    r"(?i)buy\s*this\s*domain": 15,
    r"(?i)domain\s*name\s*(is\s*for\s*sale|for\s*sale)": 15,
    r"(?i)parked\s*domain": 12,
    r"(?i)coming\s*soon": 8,
    r"(?i)website\s*for\s*sale": 15,
    r"(?i)under\s*construction": 6,
    r"(?i)this\s*domain\s*may\s*be\s*for\s*sale": 15,
    r"(?i)parking\s*page": 12,
    r"(?i)sponsored\s*listings": 10,
    r"(?i)advertisement": 5,
    r"(?i)buy\s*now": 5,
    r"(?i)premium\s*domain": 10,
}

CONTENT_SUSPICIOUS_PATTERNS = {
    r"(?i)domain\s*(for\s*sale|is\s*for\s*sale|parking|parked)": 15,
    r"(?i)buy\s*this\s*domain": 15,
    r"(?i)this\s*domain\s*is\s*for\s*sale": 15,
    r"(?i)domain\s*name\s*is\s*for\s*sale": 15,
    r"(?i)parked\s*domain": 12,
    r"(?i)domain\s*parking": 10,
    r"(?i)this\s*web\s*page\s*is\s*parked": 12,
    r"(?i)the\s*domain\s*is\s*parked": 12,
    r"(?i)sponsored\s*listings": 10,
    r"(?i)click\s*here\s*to\s*purchase": 10,
    r"(?i)buy\s*now\s*domain": 15,
    r"(?i)check\s*availability": 6,
    r"(?i)search\s*for\s*other\s*domains": 5,
    r"(?i)ad\s*by": 5,
    r"(?i)advertisement": 5,
    r"(?i)this\s*website\s*is\s*for\s*sale": 12,
    r"(?i)make\s*an\s*offer": 10,
}

DOMAIN_SALE_PATTERNS = {
    "forsale.godaddy.com": 30,
    "forsale.namecheap.com": 30,
    "sedo.com": 30,
    "afternic.com": 30,
    "dan.com": 30,
}

HIGH_TRUST_TLDS = {".gov", ".edu", ".mil"}
REDIRECT_SALE_SCORE = 20

SUSPICIOUS_DOMAINS = {
    "sedoparking.com": 20, "parkingcrew.net": 20, "parklogic.com": 20,
    "domainparkingserver.com": 20, "parkingpage.com": 18,
    "godaddy.com": 15, "namecheap.com": 12, "afternic.com": 18,
    "dan.com": 18, "sedo.com": 18, "undeveloped.com": 18,
    "bodis.com": 20, "above.com": 18, "internettraffic.com": 18,
    "domainmarket.com": 18, "buydomains.com": 18, "hugedomains.com": 18,
    "namebright.com": 15, "epik.com": 15, "dynadot.com": 15,
    "googlesyndication.com": 10, "doubleclick.net": 10,
}

SUSPICIOUS_THRESHOLD = 25
TRUSTED_SUSPICIOUS_THRESHOLD = 50
SAFE_THRESHOLD = 8
MAX_REDIRECTS = 10

CHALLENGE_MARKERS = (
    "just a moment...",
    "cf-chl",
    "cf_chl_opt",
    "challenge-platform",
    "attention required! | cloudflare",
    "checking your browser before accessing",
    "enable javascript and cookies to continue",
)

JS_REDIRECT_PATTERNS = [
    r'window\.location(?:\.href)?\s*=\s*[\'"]([^\'"]+)[\'"]',
    r'location\.href\s*=\s*[\'"]([^\'"]+)[\'"]',
    r'location\.replace\(\s*[\'"]([^\'"]+)[\'"]',
    r'location\.assign\(\s*[\'"]([^\'"]+)[\'"]',
]

MODULE_NAME = "open_url"
DEFAULT_MAX_CHARS = 15000

log_manager = get_log_manager()


def detect_html_redirect(html: str, base_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")

    meta_refresh = soup.find(
        "meta", attrs={"http-equiv": re.compile(r"refresh", re.IGNORECASE)}
    )
    if meta_refresh:
        content = meta_refresh.get("content", "")
        match = re.search(r'url\s*=\s*[\'"]?([^\'";]+)', content, re.IGNORECASE)
        if match:
            return urllib.parse.urljoin(base_url, match.group(1).strip())

    for pattern in JS_REDIRECT_PATTERNS:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return urllib.parse.urljoin(base_url, match.group(1).strip())

    return None


def is_trusted_domain(domain: str) -> bool:
    if not domain:
        return False
    d = domain.lower()
    if d in TRUSTED_DOMAINS:
        return True
    for trusted in TRUSTED_DOMAINS:
        if d.endswith(f".{trusted}"):
            return True
    for tld in HIGH_TRUST_TLDS:
        if d.endswith(tld):
            return True
    return False


def calculate_suspicious_score(
    title: str,
    snippet: str,
    url: str,
    domain: str | None = None,
    original_url: str | None = None,
    domain_trusted: bool = False,
) -> tuple[int, list[str]]:
    if domain is None:
        domain = get_domain(url)
    if original_url is None:
        original_url = url

    total_score = 0
    details: list[str] = []

    domain_lower = domain.lower()
    url_lower = url.lower()
    original_domain = get_domain(original_url).lower()

    if domain_trusted:
        total_score -= 10
        details.append(f"Trusted domain '{domain}': -10")

    sale_provider = None
    for sale_domain, score in DOMAIN_SALE_PATTERNS.items():
        if domain_lower == sale_domain or domain_lower.endswith(f".{sale_domain}"):
            sale_provider = sale_domain
            total_score += score
            details.append(f"Domain sale provider '{sale_domain}': +{score}")
            break

    if sale_provider is None:
        for suspicious_domain, score in SUSPICIOUS_DOMAINS.items():
            if domain_lower == suspicious_domain or domain_lower.endswith(
                f".{suspicious_domain}"
            ):
                total_score += score
                details.append(
                    f"Suspicious domain '{domain}' matches '{suspicious_domain}': +{score}"
                )
                break

    if original_domain != domain_lower:
        redirected_to_sale = any(
            domain_lower == sd or domain_lower.endswith(f".{sd}")
            for sd in DOMAIN_SALE_PATTERNS
        )
        redirected_to_suspicious = (
            not redirected_to_sale
            and any(
                domain_lower == sd or domain_lower.endswith(f".{sd}")
                for sd in SUSPICIOUS_DOMAINS
            )
        )
        if redirected_to_sale:
            total_score += REDIRECT_SALE_SCORE
            details.append(
                f"Redirected from '{original_domain}' to domain-sale provider "
                f"'{domain_lower}': +{REDIRECT_SALE_SCORE}"
            )
        elif redirected_to_suspicious:
            total_score += REDIRECT_SALE_SCORE
            details.append(
                f"Redirected from '{original_domain}' to suspicious domain "
                f"'{domain_lower}': +{REDIRECT_SALE_SCORE}"
            )

    if title:
        for pattern, score in TITLE_SUSPICIOUS_PATTERNS.items():
            if re.search(pattern, title):
                total_score += score
                details.append(f"Title pattern '{pattern}': +{score}")
                break

    if snippet:
        preview = snippet[:5000]
        for pattern, score in CONTENT_SUSPICIOUS_PATTERNS.items():
            if re.search(pattern, preview):
                total_score += score
                details.append(f"Content pattern '{pattern}': +{score}")
                break

    for pattern, score in (
        (r"parking", 5), (r"forsale", 8), (r"buydomain", 8), (r"domainsale", 8),
    ):
        if re.search(pattern, url_lower):
            total_score += score
            details.append(f"URL pattern '{pattern}': +{score}")
            break

    if title:
        if len(title) < 10:
            total_score += 3
            details.append(f"Title too short ({len(title)} chars): +3")
        elif len(title) > 20:
            total_score -= 2
            details.append("Title has reasonable length: -2")

    if snippet and len(snippet) > 200:
        total_score -= 3
        details.append("Content has reasonable length: -3")

    return max(0, total_score), details


def _detect_challenge(html: str, status_code: int) -> bool:
    if status_code not in (403, 503):
        return False
    low = html[:8000].lower()
    return any(marker in low for marker in CHALLENGE_MARKERS)


def _log(url: str, result: dict) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "", "=" * 70,
        f"[{ts}] OPEN URL: {url}",
        "=" * 70,
        f"Status: {result.get('status', 'unknown')}",
    ]
    if result.get("final_url") and result["final_url"] != url:
        lines.append(f"Final URL: {result['final_url']}")
    if "suspicious_score" in result:
        lines.append(f"Suspicious Score: {result['suspicious_score']}")
    if result.get("error"):
        lines.append(f"ERROR: {result['error']}")

    body = result.get("content", "") or ""
    lines.append(f"Content Length: {len(body)} characters")
    if body:
        lines += ["", "-" * 50, "CONTENT:", "-" * 50, body]

    log_manager.write_log(MODULE_NAME, "\n".join(lines) + "\n")


def extract_text_from_html(html_content: str, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
        element.decompose()
    text = soup.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[:max_chars] + "...\n[Content truncated]"
    return text


def _fix_wikipedia_url(url: str, console: Console) -> str:
    if "zh.wikipedia.org" not in url and "en.wikipedia.org" not in url:
        return url
    try:
        parsed = urllib.parse.urlparse(url)
        match = re.search(r"^/wiki/(.+)$", parsed.path)
        if not match:
            return url
        title = match.group(1)
        if re.match(r"^[A-Za-z0-9_%\-]+$", title):
            return url
        encoded = urllib.parse.quote(title, safe="_()/")
        fixed = f"{parsed.scheme}://{parsed.netloc}/wiki/{encoded}"
        console.print(f"[dim]URL fixed:[/dim] {fixed}")
        return fixed
    except Exception as e:
        console.print(f"[dim]URL fix error: {e}[/dim]")
        return url


def open_url(
    url: str,
    console: Console,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> dict:
    console.print(f"[yellow]Opening URL:[/yellow] {url}")

    original_url = url
    url = _fix_wikipedia_url(url, console)
    if url != original_url:
        console.print(f"[dim]Original: {original_url}[/dim]")
        console.print(f"[dim]Fixed: {url}[/dim]")

    try:
        session = requests.Session(impersonate="chrome120")
        session.max_redirects = MAX_REDIRECTS

        try:
            response = session.get(url, timeout=15, allow_redirects=True)
        except requests.exceptions.TooManyRedirects:
            console.print("[red]Too many redirects[/red]")
            result = {
                "url": original_url,
                "error": "Too many redirects",
                "content": "",
                "status": "error",
            }
            _log(original_url, result)
            return result

        if response.status_code >= 400:
            if _detect_challenge(response.text, response.status_code):
                console.print(
                    f"[red]Blocked by anti-bot challenge[/red] "
                    f"(HTTP {response.status_code})"
                )
                result = {
                    "url": original_url,
                    "final_url": response.url,
                    "error": "Blocked by anti-bot JS challenge (Cloudflare-like). "
                             "Try an alternative source; retrying the same URL will not help.",
                    "content": "",
                    "status": "blocked",
                }
                _log(original_url, result)
                return result

            console.print(
                f"[red]HTTP {response.status_code}:[/red] {response.text[:100]}"
            )
            result = {
                "url": original_url,
                "final_url": response.url,
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
                "content": "",
                "status": "error",
            }
            _log(original_url, result)
            return result

        final_url = response.url
        if final_url != url:
            console.print(f"[dim]Redirected to:[/dim] {final_url}")

        redirect_chain = [original_url]
        if final_url != original_url:
            redirect_chain.append(final_url)

        for _ in range(MAX_REDIRECTS):
            ctype = response.headers.get("content-type", "").lower()
            if "text/html" not in ctype:
                break
            redirect_url = detect_html_redirect(response.text, response.url)
            if not redirect_url or redirect_url in redirect_chain:
                if redirect_url in redirect_chain:
                    console.print(f"[red]Redirect loop detected:[/red] {redirect_url}")
                break

            console.print(
                f"[dim]HTML redirect detected:[/dim] {response.url} → {redirect_url}"
            )
            redirect_chain.append(redirect_url)

            try:
                response = session.get(redirect_url, timeout=15, allow_redirects=True)
            except requests.exceptions.TooManyRedirects:
                console.print("[red]Too many redirects[/red]")
                break

            if response.status_code >= 400:
                if _detect_challenge(response.text, response.status_code):
                    console.print(
                        f"[red]Blocked by anti-bot challenge[/red] "
                        f"(HTTP {response.status_code})"
                    )
                    result = {
                        "url": original_url,
                        "final_url": response.url,
                        "error": "Blocked by anti-bot JS challenge (Cloudflare-like). "
                                 "Try an alternative source.",
                        "content": "",
                        "status": "blocked",
                    }
                    _log(original_url, result)
                    return result
                break

        final_url = response.url
        final_domain = get_domain(final_url)
        final_domain_trusted = is_trusted_domain(final_domain)
        if final_domain_trusted:
            console.print(f"[green]Domain is trusted:[/green] {final_domain}")

        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string if soup.title else ""
        clean_text = extract_text_from_html(response.text, max_chars=max_chars)

        suspicious_score, score_details = calculate_suspicious_score(
            title=title or "",
            snippet=clean_text,
            url=final_url,
            domain=final_domain,
            original_url=original_url,
            domain_trusted=final_domain_trusted,
        )

        console.print(f"[dim]Suspicious score: {suspicious_score}[/dim]")
        for detail in score_details:
            console.print(f"[dim]  {detail}[/dim]")

        threshold = (
            TRUSTED_SUSPICIOUS_THRESHOLD if final_domain_trusted
            else SUSPICIOUS_THRESHOLD
        )
        if suspicious_score >= threshold:
            console.print(
                f"[red]Domain parking detected:[/red] "
                f"Score {suspicious_score} >= {threshold}"
            )
            result = {
                "url": original_url,
                "final_url": final_url,
                "error": f"This appears to be a domain parking/sale page "
                         f"(score: {suspicious_score})",
                "content": "",
                "status": "parking",
                "suspicious_score": suspicious_score,
                "score_details": score_details,
            }
            _log(original_url, result)
            return result

        if suspicious_score >= SAFE_THRESHOLD and not final_domain_trusted:
            console.print(
                f"[yellow]Page has some suspicious indicators:[/yellow] "
                f"Score {suspicious_score}"
            )
        else:
            console.print(f"[green]Page appears safe:[/green] Score {suspicious_score}")

        ctype = response.headers.get("content-type", "").lower()
        if "text/html" in ctype:
            text = clean_text
        elif "application/json" in ctype:
            try:
                text = json.dumps(response.json(), ensure_ascii=False, indent=2)
            except Exception:
                text = response.text[:max_chars]
        else:
            text = response.text[:max_chars]

        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n... [Content truncated]"

        result = {
            "url": original_url,
            "final_url": final_url,
            "content": text,
            "status": "success",
            "suspicious_score": suspicious_score,
            "score_details": score_details,
        }
        _log(original_url, result)
        return result

    except requests.exceptions.Timeout:
        console.print("[red]Timeout[/red]")
        result = {"url": original_url, "error": "Timeout",
                  "content": "", "status": "timeout"}
        _log(original_url, result)
        return result
    except Exception as e:
        console.print(f"[red]Open URL failed:[/red] {e!s}")
        result = {"url": original_url, "error": str(e),
                  "content": "", "status": "error"}
        _log(original_url, result)
        return result