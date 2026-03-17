# ============================================================
# core/web_intelligence.py — Web Search & Scraping
# Adapted from faculty-llm-iiitd/scripts/web_search.py
# ============================================================

import logging
import requests
from typing import List, Dict
from bs4 import BeautifulSoup
from skills.logger import log_audit, log_app

try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False

logger = logging.getLogger(__name__)


def scrape_url(url: str, timeout: int = 10) -> str:
    """
    Fetch and extract text content from a URL.
    Returns extracted text or empty string on failure.
    """
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return ""

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove non-content elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 20]
        return "\n".join(lines[:100])

    except Exception as e:
        logger.error(f"Scraping failed for {url}: {e}")
        return ""


def web_search(query: str, max_results: int = 5) -> List[Dict]:
    """
    Multi-engine web search with 3-tier fallback:
      1. DuckDuckGo HTML scraping (most reliable)
      2. SearXNG public instances
      3. DDG Python API

    Returns list of dicts with 'title', 'href', 'body' keys.
    """
    log_audit("WEB_SEARCH", f"Searching for: {query}")

    # Method 1: DuckDuckGo HTML
    try:
        ddg_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        resp = requests.get(ddg_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            results = []

            for item in soup.select(".result"):
                title_elem = item.select_one(".result__title a")
                snippet_elem = item.select_one(".result__snippet")

                if title_elem:
                    href = title_elem.get("href", "")
                    if "uddg=" in href:
                        import urllib.parse
                        parsed = urllib.parse.parse_qs(
                            urllib.parse.urlparse(href).query
                        )
                        href = parsed.get("uddg", [href])[0]

                    if href.startswith("http"):
                        results.append({
                            "title": title_elem.get_text(strip=True),
                            "href": href,
                            "body": (
                                snippet_elem.get_text(strip=True)
                                if snippet_elem
                                else ""
                            ),
                        })
                        if len(results) >= max_results:
                            break

            if results:
                log_audit("WEB_SEARCH", f"DDG HTML returned {len(results)} results")
                return results
    except Exception as e:
        logger.debug(f"DDG HTML scraping failed: {e}")

    # Method 2: SearXNG
    searxng_instances = [
        "https://search.bus-hit.me",
        "https://search.ononoki.org",
        "https://searx.be",
    ]

    for instance in searxng_instances:
        try:
            url = f"{instance}/search"
            params = {
                "q": query,
                "format": "json",
                "categories": "general",
                "language": "en",
            }
            resp = requests.get(
                url,
                params=params,
                timeout=5,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])[:max_results]
                if results:
                    normalized = [
                        {
                            "title": r.get("title", ""),
                            "href": r.get("url", ""),
                            "body": r.get("content", ""),
                        }
                        for r in results
                    ]
                    log_audit("WEB_SEARCH", f"SearXNG ({instance}) returned {len(normalized)} results")
                    return normalized
        except Exception as e:
            logger.debug(f"SearXNG {instance} failed: {e}")
            continue

    # Method 3: DDG API fallback
    if DDGS_AVAILABLE:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results, region="wt-wt"))
                log_audit("WEB_SEARCH", f"DDG API returned {len(results)} results")
                return results
        except Exception as e:
            logger.debug(f"DDG search failed: {e}")

    log_audit("WEB_SEARCH", f"All search engines failed for: {query}")
    return []


def research_topic(topic: str, max_results: int = 3) -> str:
    """
    Search for a topic and scrape top results.
    Returns combined content from search results.
    Used by the self-updater to research new features.
    """
    log_audit("WEB_RESEARCH", f"Researching topic: {topic}")
    results = web_search(topic, max_results)

    if not results:
        return ""

    contents = []
    for i, result in enumerate(results[:max_results]):
        url = result.get("href") or result.get("url", "")
        title = result.get("title", "No title")

        if url:
            content = scrape_url(url)
            if content:
                contents.append(f"### Source {i + 1}: {title}\n{content[:1500]}")

    combined = "\n\n".join(contents)
    log_audit("WEB_RESEARCH", f"Gathered {len(contents)} sources ({len(combined)} chars)")
    return combined
