import json
import re
import time
from datetime import datetime
from typing import Any
from urllib.parse import quote

from bs4 import BeautifulSoup
from curl_cffi import requests
from ddgs import DDGS
from rich.console import Console

from tools.common_funcs import get_domain, normalize_url
from tools.config import SearchStrategy
from tools.logs import get_log_manager

SUSPICIOUS_KEYWORDS = {
    "domain for sale",
    "buy this domain",
    "domain parking",
    "parked domain",
    "this domain is for sale",
    "domain name is for sale",
    "coming soon",
}

MODULE_NAME = "web_search"

log_manager = get_log_manager()


def log(
    query: str,
    results: list,
    method: str | None = None,
    error: str | None = None,
    raw_data: Any | None = None,
):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = f"\n{'=' * 70}\n[{timestamp}] SEARCH: {query}\n{'=' * 70}\n"
    if error:
        content += f"ERROR: {error}\n\n"
        log_manager.write_log(MODULE_NAME, content)
        return

    content += f"Method: {method if method else 'Unknown'}\n"
    content += f"Total Results: {len(results) if results else 0}\n\n"

    if raw_data:
        content += "-" * 50 + "\n"
        content += "RAW RESPONSE (first 2000 chars):\n"
        content += "-" * 50 + "\n"
        raw_str = json.dumps(raw_data, ensure_ascii=False, indent=2)[:2000]
        content += raw_str
        if len(json.dumps(raw_data, ensure_ascii=False)) > 2000:
            content += "\n... [truncated]"
        content += "\n" + "-" * 50 + "\n\n"

    if results:
        for i, result in enumerate(results, 1):
            content += f"Result {i}:\n"
            content += f"  Title: {result.get('title', 'N/A')}\n"
            content += f"  URL: {result.get('url', 'N/A')}\n"
            content += f"  Snippet: {result.get('snippet', 'N/A')[:200]}{'...' if len(result.get('snippet', '')) > 200 else ''}\n"
            content += "-" * 50 + "\n"
    else:
        content += "No results found.\n"

    content += "\n"
    log_manager.write_log(MODULE_NAME, content)


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


def _search_ddgs(query: str, console: Console):
    results = []
    try:
        with DDGS() as ddgs:
            raw_results = ddgs.text(query, region="tw-tz", max_results=10)

            for item in raw_results:
                results.append(
                    {
                        "title": item.get("title", ""),
                        "snippet": item.get("body", "No description available"),
                        "url": item.get("href", ""),
                    }
                )
    except Exception as e:
        raise ValueError(f"DuckDuckGo search failed: {e!s}")

    if not results:
        raise ValueError(f"No results returned from DuckDuckGo for query: {query}")

    return {
        "query": query,
        "results": results,
        "_raw_data": {"source": "duckduckgo_official_package"},
    }


def _search_wikipedia_api(query: str, console: Console, lang: str | None = None):
    has_chinese = bool(re.search(r"[\u4e00-\u9fff]", query))
    if not lang:
        lang = "zh" if has_chinese else "en"
    has_traditional = bool(re.search(r"[\u3400-\u4dbf\ufa0e-\ufa2f]", query))

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
            **({"variant": "zh-tw"} if has_traditional else {}),
        }

        response = None
        for _attempt in range(2):
            response = requests.get(API_URL, params=search_params, headers=headers, timeout=10)
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
            "variant": "zh-tw",
        }

        ext_response = requests.get(API_URL, params=extract_params, headers=headers, timeout=10)
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

            if any(
                title.startswith(prefix)
                for prefix in ["Wikipedia:", "Special:", "Help:", "Template:", "Category:"]
            ):
                continue

            page_url = (
                f"https://{lang}.wikipedia.org/wiki/{quote(title.replace(' ', '_'), safe='_()')}"
            )

            snippet = pages.get(pid, {}).get("extract", "").strip()
            if not snippet:
                raw_snippet = item.get("snippet", "")
                if raw_snippet:
                    snippet = BeautifulSoup(raw_snippet, "html.parser").get_text()

            results.append(
                {"title": title, "snippet": snippet or "Wikipedia article", "url": page_url}
            )

        if results:
            console.print(f"[green]✓ Found {len(results)} Wikipedia articles[/green]")
            return {"query": query, "results": results}
        else:
            raise ValueError("No valid Wikipedia results found")

    except requests.exceptions.RequestException as e:
        console.print(f"[dim]Wikipedia API request failed: {e!s}[/dim]")
        raise ValueError(f"Wikipedia API error: {e!s}")
    except json.JSONDecodeError as e:
        console.print(f"[dim]Wikipedia API JSON decode error: {e!s}[/dim]")
        raise ValueError(f"Wikipedia API parse error: {e!s}")
    except Exception as e:
        console.print(f"[dim]Wikipedia API error: {e!s}[/dim]")
        raise ValueError(f"Wikipedia API error: {e!s}")


SEARCH_STRATEGIES = {
    SearchStrategy.DUCKDUCKGO_SEARCH: _search_ddgs,
    SearchStrategy.WIKIPEDIA_API: _search_wikipedia_api,
}


def web_search(
    query: str,
    console: Console,
    strategy: SearchStrategy = SearchStrategy.AUTO,
) -> dict[str, Any]:
    console.print(f"[yellow]Searching the internet for:[/yellow] {query}")

    search_methods = (
        list(SEARCH_STRATEGIES.values())
        if strategy == SearchStrategy.AUTO
        else [SEARCH_STRATEGIES[strategy]]
    )

    results = []
    last_error = None
    successful_method = None
    raw_data = None

    for method in search_methods:
        try:
            console.print(f"[dim]Trying {method.__name__}...[/dim]")
            result = method(query, console=console)

            if not result or not result.get("results"):
                console.print(f"[dim]{method.__name__} returned no results[/dim]")
                continue

            results = result["results"]
            raw_data = result.get("_raw_data")
            successful_method = method.__name__

            console.print(f"[green]✓ Search successful using: {successful_method}[/green]")
            break

        except Exception as e:
            last_error = str(e)
            console.print(f"[dim]✗ {method.__name__} failed: {e!s}[/dim]")

    if not results:
        error_msg = f"All search methods failed. Last error: {last_error}"
        console.print(f"[red]{error_msg}[/red]")
        log(query, [], error=error_msg, raw_data=raw_data)
        return {"query": query, "error": error_msg, "results": []}

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

        snippet = r["snippet"]

        filtered_results.append(
            {
                "title": r["title"],
                "snippet": snippet[:500],
                "url": url,
            }
        )

        if len(filtered_results) >= 10:
            break

    final_result = {
        "query": query,
        "results": filtered_results,
        "method": successful_method,
    }

    log(
        query=query,
        results=filtered_results,
        method=successful_method,
        raw_data=raw_data,
    )
    return final_result
