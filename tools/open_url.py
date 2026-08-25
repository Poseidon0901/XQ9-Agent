from rich.console import Console
import urllib
from .get_domain import get_domain
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json

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
        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
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
        
        final_domain = get_domain(final_url)
        
        parking_domains = {
            "sedoparking.com", "parkingcrew.net", "parklogic.com",
            "domainparkingserver.com", "parkingpage.com", "godaddy.com",
            "namecheap.com", "afternic.com", "dan.com", "sedo.com",
            "undeveloped.com", "bodis.com", "above.com", "internettraffic.com",
            "domainmarket.com", "buydomains.com", "hugedomains.com",
            "namebright.com", "epik.com", "dynadot.com",
        }
        
        is_parking = False
        parking_reason = ""
        
        if final_domain in parking_domains:
            is_parking = True
            parking_reason = f"Domain parking service: {final_domain}"
        
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string if soup.title else ""
        
        suspicious_title_keywords = [
            "domain for sale", "buy this domain", "parking", "coming soon",
            "this domain is for sale", "domain name is for sale",
            "website for sale", "domain parked", "parked domain", "buy domain",
        ]
        
        if title:
            title_lower = title.lower()
            for keyword in suspicious_title_keywords:
                if keyword in title_lower:
                    is_parking = True
                    parking_reason = f"Suspicious title: '{title}'"
                    break
        
        if not is_parking:
            body_text = soup.get_text().lower()
            suspicious_content_keywords = [
                "domain for sale", "buy this domain", "this domain is for sale",
                "domain parking", "parked domain", "domain name is for sale",
                "this web page is parked", "the domain is parked",
                "sponsored listings", "click here to purchase",
            ]
            
            body_preview = body_text[:5000]
            for keyword in suspicious_content_keywords:
                if keyword in body_preview:
                    is_parking = True
                    parking_reason = f"Suspicious content detected: '{keyword}'"
                    break
        
        if is_parking:
            console.print(f"[red]Domain parking detected:[/red] {parking_reason}")
            result = {
                "url": original_url,
                "final_url": final_url,
                "error": f"This appears to be a domain parking/sale page: {parking_reason}",
                "content": "",
                "status": "parking"
            }
            log_open_url(original_url, result, launch_timestamp=launch_timestamp)
            return result
        
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
            text = text[:5000] + "\n\n... [內容已截斷]"
        
        result = {
            "url": original_url,
            "final_url": final_url,
            "content": text,
            "status": "success"
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