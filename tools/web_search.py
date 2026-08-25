from urllib.parse import quote
from .get_domain import get_domain
from ddgs import DDGS
import requests
import json
from bs4 import BeautifulSoup
from rich.console import Console
import time
from datetime import datetime
from .normalize_url import normalize_url

SUSPICIOUS_KEYWORDS = {
    "domain for sale",
    "buy this domain",
    "domain parking",
    "parked domain",
    "this domain is for sale",
    "domain name is for sale",
    "coming soon",
}

def log_web_search(query: str, results: list, launch_timestamp: str, method: str = None, error: str = None, raw_data: any = None):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_file = f"logs/web_search_{launch_timestamp}.log"
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*70}\n")
        f.write(f"[{timestamp}] SEARCH: {query}\n")
        f.write(f"{'='*70}\n")
        
        if error:
            f.write(f"ERROR: {error}\n\n")
            return
        
        f.write(f"Method: {method if method else 'Unknown'}\n")
        f.write(f"Total Results: {len(results) if results else 0}\n\n")
        
        if raw_data:
            f.write("-" * 50 + "\n")
            f.write("RAW RESPONSE (first 2000 chars):\n")
            f.write("-" * 50 + "\n")
            raw_str = json.dumps(raw_data, ensure_ascii=False, indent=2)[:2000]
            f.write(raw_str)
            if len(json.dumps(raw_data, ensure_ascii=False)) > 2000:
                f.write("\n... [truncated]")
            f.write("\n" + "-" * 50 + "\n\n")
        
        if results:
            for i, result in enumerate(results, 1):
                f.write(f"Result {i}:\n")
                f.write(f"  Title: {result.get('title', 'N/A')}\n")
                f.write(f"  URL: {result.get('url', 'N/A')}\n")
                f.write(f"  Snippet: {result.get('snippet', 'N/A')[:200]}{'...' if len(result.get('snippet', '')) > 200 else ''}\n")
                f.write("-" * 50 + "\n")
        else:
            f.write("No results found.\n")
        
        f.write("\n")

def is_suspicious_result(title: str, snippet: str, url: str) -> bool:
    text = f"{title} {snippet}".lower()

    for keyword in SUSPICIOUS_KEYWORDS:
        if keyword in text:
            return True

    if not url or not url.startswith(("http://", "https://")):
        return True

    domain = get_domain(url)

    if domain in {
        "duckduckgo.com",
        "html.duckduckgo.com",
    }:
        return True
    
    parking_domains = {
        "sedoparking.com",
        "parkingcrew.net",
        "parklogic.com",
        "domainparkingserver.com",
        "parkingpage.com",
        "godaddy.com",
        "namecheap.com",
        "afternic.com",
        "dan.com",
        "sedo.com",
        "undeveloped.com",
        "bodis.com",
        "above.com",
        "internettraffic.com",
        "domainmarket.com",
        "buydomains.com",
        "hugedomains.com",
        "namebright.com",
        "epik.com",
        "dynadot.com",
    }
    
    if domain in parking_domains:
        return True

    return False

def _search_duckduckgo_html(query: str):
    results = []
    try:
        with DDGS() as ddgs:
            raw_results = ddgs.text(query, region="tw-tz", max_results=10)
            
            for item in raw_results:
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("body", "No description available"),
                    "url": item.get("href", "")
                })
    except Exception as e:
        raise ValueError(f"DuckDuckGo search failed: {str(e)}")

    if not results:
        raise ValueError(f"No results returned from DuckDuckGo for query: {query}")

    return {
        "query": query,
        "results": results,
        "_raw_data": {
            "source": "duckduckgo_official_package"
        }
    }

def _search_duckduckgo_api(query: str):
    api_url = "https://api.duckduckgo.com/"
    params = {
        "q": query,
        "format": "json",
        "no_html": 1,
        "skip_disambig": 1,
        "t": "llama_search"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(api_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        raise ValueError(f"DuckDuckGo API request failed: {str(e)}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON response from DuckDuckGo API: {str(e)}")

    if not data:
        raise ValueError("Empty API response")

    raw_data = data.copy()
    
    if 'raw' in raw_data:
        del raw_data['raw']

    results = []
    seen_urls = set()

    if data.get("Abstract", ""):
        url = data.get("AbstractURL", "")
        if url and url.startswith(("http://", "https://")):
            results.append({
                "title": data.get("Heading", query),
                "snippet": data["Abstract"][:500],
                "url": url
            })

    for topic in data.get("RelatedTopics", []):
        if "Result" not in topic:
            continue
            
        result_text = topic.get("Result", "")
        soup = BeautifulSoup(result_text, "html.parser")
        
        link_elem = soup.find("a")
        if not link_elem:
            continue
            
        url = link_elem.get("href", "")
        if not url or not url.startswith(("http://", "https://")):
            continue
            
        title = link_elem.get_text(strip=True)
        if not title:
            title = "No title"
            
        snippet = soup.get_text(separator=" ", strip=True)
        if snippet:
            snippet = snippet.replace(title, "", 1).strip()
        
        url = normalize_url(url)
        
        if url in seen_urls:
            continue
        seen_urls.add(url)
        
        if is_suspicious_result(title, snippet or "", url):
            continue
        
        results.append({
            "title": title,
            "snippet": snippet or "No description available",
            "url": url
        })
        
        if len(results) >= 10:
            break
    
    if not results:
        raise ValueError(f"No relevant results from DuckDuckGo API. Raw data keys: {list(data.keys())}")
    
    return {
        "query": query,
        "results": results,
        "_raw_data": raw_data
    }

def _search_wikipedia_api(query: str, lang: str = None, console: Console = None):
    """Wikipedia 搜索，自動檢測語言"""
    import re
    
    if lang is None:
        if re.search(r'[\u4e00-\u9fff]', query):
            lang = "zh"
        else:
            lang = "en"
    
    console.print(f"[dim]Wikipedia API search ({lang}):[/dim] {query}")
    
    API_URL = f"https://{lang}.wikipedia.org/w/api.php"
    
    headers = {
        "User-Agent": "llama-search/1.0 (https://github.com/Poseidon0901; xq9.0901@gmail.com)"
    }
    
    try:
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "utf8": 1,
            "srlimit": 5,
            "variant": "zh-tw"
        }
        
        response = None
        for attempt in range(2):
            response = requests.get(
                API_URL,
                params=search_params,
                headers=headers,
                timeout=10
            )
            if response.status_code == 429:
                time.sleep(1.5)
                continue
            break

        response.raise_for_status()
        data = response.json()

        if "query" not in data or "search" not in data["query"]:
            raise ValueError("No search results from Wikipedia API")
        
        search_results = data["query"]["search"]
        
        if not search_results:
            raise ValueError("No Wikipedia articles found")

        page_ids = [str(item["pageid"]) for item in search_results]

        extract_params = {
            "action": "query",
            "pageids": "|".join(page_ids),
            "prop": "extracts",
            "exintro": 1,
            "explaintext": 1,
            "exchars": 400,
            "format": "json",
            "utf8": 1,
            "variant": "zh-tw"
        }

        ext_response = requests.get(
            API_URL,
            params=extract_params,
            headers=headers,
            timeout=10
        )
        ext_response.raise_for_status()
        ext_data = ext_response.json()
        pages = ext_data.get("query", {}).get("pages", {})

        results = []
        seen_titles = set()
        
        for item in search_results:
            title = item.get("title", "")
            pid = str(item.get("pageid"))
            
            if title in seen_titles:
                continue
            seen_titles.add(title)

            if any(title.startswith(prefix) for prefix in ["Wikipedia:", "Special:", "Help:", "Template:", "Category:"]):
                continue

            page_url = f"https://{lang}.wikipedia.org/wiki/{quote(title.replace(' ', '_'), safe='_()')}"
            
            snippet = pages.get(pid, {}).get("extract", "").strip()
            if not snippet:
                raw_snippet = item.get("snippet", "")
                if raw_snippet:
                    snippet = BeautifulSoup(raw_snippet, "html.parser").get_text()

            results.append({
                "title": title,
                "snippet": snippet or "Wikipedia article",
                "url": page_url
            })
        
        if results:
            console.print(f"[green]✓ Found {len(results)} Wikipedia articles[/green]")
            return {
                "query": query,
                "results": results
            }
        else:
            raise ValueError("No valid Wikipedia results found")
            
    except requests.exceptions.RequestException as e:
        console.print(f"[dim]Wikipedia API request failed: {str(e)}[/dim]")
        raise ValueError(f"Wikipedia API error: {str(e)}")
    except json.JSONDecodeError as e:
        console.print(f"[dim]Wikipedia API JSON decode error: {str(e)}[/dim]")
        raise ValueError(f"Wikipedia API parse error: {str(e)}")
    except Exception as e:
        console.print(f"[dim]Wikipedia API error: {str(e)}[/dim]")
        raise ValueError(f"Wikipedia API error: {str(e)}")

def web_search(query: str, console: Console, launch_timestamp: str):
    console.print(f"[yellow]Searching the internet for:[/yellow] {query}")

    import re
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', query))
    
    if has_chinese:
        search_methods = [
            _search_duckduckgo_html,
            _search_wikipedia_api,
        ]
    else:
        search_methods = [
            _search_duckduckgo_html,
            _search_wikipedia_api,
            _search_duckduckgo_api,
        ]
    
    results = []
    last_error = None
    successful_method = None
    raw_data = None
    
    for method in search_methods:
        try:
            console.print(f"[dim]Trying {method.__name__}...[/dim]")
            if method.__name__ == "_search_wikipedia_api":
                result = method(query, console=console)
            else:
                result = method(query)
            
            if result and "_raw_data" in result:
                raw_data = result["_raw_data"]
            
            if result and result.get("results") and len(result["results"]) > 0:
                results = result["results"]
                successful_method = method.__name__
                console.print(f"[green]✓ Search successful using:[/green] {successful_method}")
                break
            else:
                console.print(f"[dim]{method.__name__} returned no results[/dim]")
        except Exception as e:
            last_error = str(e)
            console.print(f"[dim]✗ {method.__name__} failed:[/dim] {str(e)}")
            continue

    if not results:
        error_msg = f"All search methods failed. Last error: {last_error}"
        console.print(f"[red]{error_msg}[/red]")
        log_web_search(query, [], error=error_msg, raw_data=raw_data, launch_timestamp=launch_timestamp)
        return {
            "query": query,
            "error": error_msg,
            "results": []
        }

    filtered_results = []
    seen_urls = set()
    for r in results:
        url = normalize_url(r["url"])
        if url in seen_urls:
            continue
        seen_urls.add(url)
        
        if is_suspicious_result(r["title"], r["snippet"], url):
            console.print(f"[dim]Skipping suspicious:[/dim] {url}")
            continue
        
        filtered_results.append({
            "title": r["title"],
            "snippet": r["snippet"][:500] if len(r["snippet"]) > 500 else r["snippet"],
            "url": url
        })
        
        if len(filtered_results) >= 10:
            break
    
    final_result = {
        "query": query,
        "results": filtered_results,
        "method": successful_method
    }
    
    log_web_search(query=query, results=filtered_results, method=successful_method, raw_data=raw_data, launch_timestamp=launch_timestamp)
    
    return final_result