from rich.console import Console
import urllib
from .get_domain import get_domain
import re
from curl_cffi import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json

TRUSTED_DOMAINS = {
    "github.com",
    "gitlab.com",
    "bitbucket.org",
    "stackoverflow.com",
    "stackexchange.com",
    "reddit.com",
    "medium.com",
    "dev.to",
    "wikipedia.org",
    "wikimedia.org",
    "archive.org",
    "gov",
    "edu",
    "mozilla.org",
    "python.org",
    "pypi.org",
    "npmjs.com",
    "docker.com",
    "kubernetes.io",
    "cnn.com",
    "bbc.com",
    "reuters.com",
    "ap.org",
    "nytimes.com",
    "wsj.com",
    "bloomberg.com",
    "economist.com",
    "nature.com",
    "science.org",
    "arxiv.org",
    "ieee.org",
    "acm.org",
    "springer.com",
    "elsevier.com",
    "jstor.org",
    "google.com",
    "youtube.com",
    "amazon.com",
    "microsoft.com",
    "apple.com",
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
    "sedoparking.com": 20,
    "parkingcrew.net": 20,
    "parklogic.com": 20,
    "domainparkingserver.com": 20,
    "parkingpage.com": 18,
    "godaddy.com": 15,
    "namecheap.com": 12,
    "afternic.com": 18,
    "dan.com": 18,
    "sedo.com": 18,
    "undeveloped.com": 18,
    "bodis.com": 20,
    "above.com": 18,
    "internettraffic.com": 18,
    "domainmarket.com": 18,
    "buydomains.com": 18,
    "hugedomains.com": 18,
    "namebright.com": 15,
    "epik.com": 15,
    "dynadot.com": 15,
    "googlesyndication.com": 10,
    "doubleclick.net": 10,
}

SUSPICIOUS_THRESHOLD = 25
TRUSTED_SUSPICIOUS_THRESHOLD = 50

SAFE_THRESHOLD = 8

MAX_REDIRECTS = 10

JS_REDIRECT_PATTERNS = [
    r'window\.location(?:\.href)?\s*=\s*[\'"]([^\'"]+)[\'"]',
    r'location\.href\s*=\s*[\'"]([^\'"]+)[\'"]',
    r'location\.replace\(\s*[\'"]([^\'"]+)[\'"]',
    r'location\.assign\(\s*[\'"]([^\'"]+)[\'"]',
]

def detect_html_redirect(html: str, base_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")

    meta_refresh = soup.find(
        "meta",
        attrs={"http-equiv": re.compile(r"refresh", re.I)}
    )

    if meta_refresh:
        content = meta_refresh.get("content", "")
        match = re.search(
            r'url\s*=\s*[\'"]?([^\'";]+)',
            content,
            re.I
        )

        if match:
            target = match.group(1).strip()
            return urllib.parse.urljoin(base_url, target)

    for pattern in JS_REDIRECT_PATTERNS:
        match = re.search(pattern, html, re.I)

        if match:
            target = match.group(1).strip()
            return urllib.parse.urljoin(base_url, target)

    return None

def is_trusted_domain(domain: str) -> bool:
    if not domain:
        return False
    
    domain_lower = domain.lower()

    if domain_lower in TRUSTED_DOMAINS:
        return True

    for trusted in TRUSTED_DOMAINS:
        if domain_lower.endswith(f".{trusted}"):
            return True

    for tld in HIGH_TRUST_TLDS:
        if domain_lower.endswith(tld):
            return True
    
    return False


def calculate_suspicious_score(
    title: str,
    snippet: str,
    url: str,
    domain: str = None,
    original_url: str = None,
    domain_trusted: bool = False
) -> tuple:

    if domain is None:
        domain = get_domain(url)

    if original_url is None:
        original_url = url

    total_score = 0
    details = []

    domain_lower = domain.lower()
    url_lower = url.lower()
    original_domain = get_domain(original_url).lower()

    if domain_trusted:
        total_score -= 10
        details.append(
            f"Trusted domain '{domain}': -10"
        )

    sale_provider = None

    for sale_domain, score in DOMAIN_SALE_PATTERNS.items():
        if (
            domain_lower == sale_domain
            or domain_lower.endswith(f".{sale_domain}")
        ):
            sale_provider = sale_domain
            total_score += score
            details.append(
                f"Domain sale provider '{sale_domain}': +{score}"
            )
            break

    if sale_provider is None:
        for suspicious_domain, score in SUSPICIOUS_DOMAINS.items():
            if (
                domain_lower == suspicious_domain
                or domain_lower.endswith(f".{suspicious_domain}")
            ):
                total_score += score
                details.append(
                    f"Suspicious domain '{domain}' "
                    f"matches '{suspicious_domain}': +{score}"
                )
                break

    if original_domain != domain_lower:

        redirected_to_sale = False

        for sale_domain in DOMAIN_SALE_PATTERNS:
            if (
                domain_lower == sale_domain
                or domain_lower.endswith(f".{sale_domain}")
            ):
                redirected_to_sale = True
                break

        redirected_to_suspicious = False

        if not redirected_to_sale:
            for suspicious_domain in SUSPICIOUS_DOMAINS:
                if (
                    domain_lower == suspicious_domain
                    or domain_lower.endswith(f".{suspicious_domain}")
                ):
                    redirected_to_suspicious = True
                    break

        if redirected_to_sale:
            total_score += REDIRECT_SALE_SCORE

            details.append(
                f"Redirected from '{original_domain}' "
                f"to domain-sale provider '{domain_lower}': "
                f"+{REDIRECT_SALE_SCORE}"
            )

        elif redirected_to_suspicious:
            total_score += REDIRECT_SALE_SCORE

            details.append(
                f"Redirected from '{original_domain}' "
                f"to suspicious domain '{domain_lower}': "
                f"+{REDIRECT_SALE_SCORE}"
            )

    if title:
        for pattern, score in TITLE_SUSPICIOUS_PATTERNS.items():
            if re.search(pattern, title):
                total_score += score
                details.append(
                    f"Title pattern '{pattern}': +{score}"
                )
                break

    if snippet:
        snippet_preview = snippet[:5000]

        for pattern, score in CONTENT_SUSPICIOUS_PATTERNS.items():
            if re.search(pattern, snippet_preview):
                total_score += score
                details.append(
                    f"Content pattern '{pattern}': +{score}"
                )
                break

    url_suspicious_patterns = [
        (r"parking", 5),
        (r"forsale", 8),
        (r"buydomain", 8),
        (r"domainsale", 8),
    ]

    for pattern, score in url_suspicious_patterns:
        if re.search(pattern, url_lower):
            total_score += score
            details.append(
                f"URL pattern '{pattern}': +{score}"
            )
            break

    if title:
        if len(title) < 10:
            total_score += 3
            details.append(
                f"Title too short ({len(title)} chars): +3"
            )

        elif len(title) > 20:
            total_score -= 2
            details.append(
                "Title has reasonable length: -2"
            )

    if snippet and len(snippet) > 200:
        total_score -= 3
        details.append(
            "Content has reasonable length: -3"
        )

    total_score = max(0, total_score)

    return total_score, details


def log_open_url(url: str, result: dict, launch_timestamp: str):
    log_file = f"logs/open_url_{launch_timestamp}.log"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*70}\n")
        f.write(f"[{timestamp}] OPEN URL: {url}\n")
        f.write(f"{'='*70}\n")
        
        f.write(f"Status: {result.get('status', 'unknown')}\n")
        if 'final_url' in result and result['final_url'] != url:
            f.write(f"Final URL: {result['final_url']}\n")
        
        if 'suspicious_score' in result:
            f.write(f"Suspicious Score: {result['suspicious_score']}\n")
        
        if result.get('error'):
            f.write(f"ERROR: {result['error']}\n\n")
            return
        
        content = result.get('content', '')
        if content:
            f.write(f"Content Length: {len(content)} characters\n")
            f.write("\n" + "-"*50 + "\n")
            f.write("CONTENT:\n")
            f.write("-"*50 + "\n")
            f.write(content)
            f.write("\n" + "-"*50 + "\n")
        else:
            f.write("No content retrieved.\n")
        
        f.write("\n")


def extract_text_from_html(html_content: str, url: str = ""):
    soup = BeautifulSoup(html_content, "html.parser")
    
    for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
        element.decompose()
    
    text = soup.get_text(separator="\n", strip=True)
    
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    text = "\n".join(lines)

    if len(text) > 4000:
        text = text[:4000] + "...\n[Content truncated]"
    
    return text


def open_url(url: str, console: Console, launch_timestamp: str):
    console.print(f"[yellow]Opening URL:[/yellow] {url}")
    
    def fix_wikipedia_url(url: str) -> str:
        if 'zh.wikipedia.org' not in url and 'en.wikipedia.org' not in url:
            return url
        
        try:
            parsed = urllib.parse.urlparse(url)
            path = parsed.path
            
            match = re.search(r'^/wiki/(.+)$', path)
            if not match:
                return url
            
            title = match.group(1)
            
            if re.match(r'^[A-Za-z0-9_%\-]+$', title):
                return url
            
            if any(ord(c) > 127 for c in title) or any(c in title for c in '【】（）（）『』「」'):
                encoded_title = urllib.parse.quote(title, safe='_()')
                fixed_url = f"{parsed.scheme}://{parsed.netloc}/wiki/{encoded_title}"
                console.print(f"[dim]URL fixed:[/dim] {fixed_url}")
                return fixed_url
            
            return url
            
        except Exception as e:
            console.print(f"[dim]URL fix error: {e}[/dim]")
            return url
    
    original_url = url
    url = fix_wikipedia_url(url)
    
    if url != original_url:
        console.print(f"[dim]Original: {original_url}[/dim]")
        console.print(f"[dim]Fixed: {url}[/dim]")
    
    try:
        session = requests.Session(impersonate="chrome120")
        session.max_redirects = MAX_REDIRECTS

        response = session.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/151.0.0.0 Safari/537.36"
            },
            timeout=15,
            allow_redirects=True
        )

        if response.status_code >= 400:
            console.print(f"[red]HTTP {response.status_code}:[/red] {response.text[:100]}")
            result = {
                "url": original_url,
                "final_url": response.url,
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
                "content": "",
                "status": "error"
            }
            log_open_url(original_url, result, launch_timestamp=launch_timestamp)
            return result
        
        final_url = response.url

        if final_url != url:
            console.print(f"[dim]Redirected to:[/dim] {final_url}")

        redirect_chain = [original_url]

        if final_url != original_url:
            redirect_chain.append(final_url)

        for redirect_count in range(MAX_REDIRECTS):
            content_type = response.headers.get("content-type", "").lower()

            if "text/html" not in content_type:
                break

            redirect_url = detect_html_redirect(
                response.text,
                response.url
            )

            if not redirect_url:
                break

            if redirect_url in redirect_chain:
                console.print(
                    f"[red]Redirect loop detected:[/red] {redirect_url}"
                )
                break

            console.print(
                f"[dim]HTML redirect detected:[/dim] "
                f"{response.url} → {redirect_url}"
            )

            redirect_chain.append(redirect_url)

            try:
                response = session.get(
                    redirect_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                                    "Chrome/91.0.4472.124 Safari/537.36"
                    },
                    timeout=15,
                    allow_redirects=True
                )

            except requests.exceptions.TooManyRedirects:
                console.print("[red]Too many redirects[/red]")
                break

            if response.status_code >= 400:
                break

        final_url = response.url
        final_domain = get_domain(final_url)
        final_domain_trusted = is_trusted_domain(final_domain)

        if final_domain_trusted:
            console.print(f"[green]Domain is trusted:[/green] {final_domain}")

        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string if soup.title else ""
        body_text = soup.get_text()
        
        suspicious_score, score_details = calculate_suspicious_score(
            title=title or "",
            snippet=body_text[:5000],
            url=final_url,
            domain=final_domain,
            original_url=original_url,
            domain_trusted=final_domain_trusted
        )
        
        console.print(f"[dim]Suspicious score: {suspicious_score}[/dim]")
        for detail in score_details:
            console.print(f"[dim]  {detail}[/dim]")

        suspicious_threshold = TRUSTED_SUSPICIOUS_THRESHOLD if final_domain_trusted else SUSPICIOUS_THRESHOLD
        
        if suspicious_score >= suspicious_threshold :
            console.print(f"[red]Domain parking detected:[/red] Score {suspicious_score} >= {suspicious_threshold}")
            result = {
                "url": original_url,
                "final_url": final_url,
                "error": f"This appears to be a domain parking/sale page (score: {suspicious_score})",
                "content": "",
                "status": "parking",
                "suspicious_score": suspicious_score,
                "score_details": score_details
            }
            log_open_url(original_url, result, launch_timestamp=launch_timestamp)
            return result
        
        if suspicious_score >= SAFE_THRESHOLD and not final_domain_trusted:
            console.print(f"[yellow]Page has some suspicious indicators:[/yellow] Score {suspicious_score}")
        else:
            console.print(f"[green]Page appears safe:[/green] Score {suspicious_score}")

        content_type = response.headers.get('content-type', '').lower()
        
        if 'text/html' in content_type:
            text = extract_text_from_html(response.text, final_url)
        elif 'application/json' in content_type:
            try:
                data = response.json()
                text = json.dumps(data, ensure_ascii=False, indent=2)
            except Exception:
                text = response.text[:2000]
        else:
            text = response.text[:4000]

        if len(text) > 5000:
            text = text[:5000] + "\n\n... [Content truncated]"
        
        result = {
            "url": original_url,
            "final_url": final_url,
            "content": text,
            "status": "success",
            "suspicious_score": suspicious_score,
            "score_details": score_details
        }
        
        log_open_url(original_url, result, launch_timestamp=launch_timestamp)
        return result
        
    except requests.exceptions.Timeout:
        console.print("[red]Timeout[/red]")
        result = {
            "url": original_url,
            "error": "Timeout",
            "content": "",
            "status": "timeout"
        }
        log_open_url(original_url, result, launch_timestamp=launch_timestamp)
        return result
        
    except Exception as e:
        console.print(f"[red]Open URL failed:[/red] {str(e)}")
        result = {
            "url": original_url,
            "error": str(e),
            "content": "",
            "status": "error"
        }
        log_open_url(original_url, result, launch_timestamp=launch_timestamp)
        return result