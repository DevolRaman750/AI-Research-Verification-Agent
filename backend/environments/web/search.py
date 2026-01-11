import requests
import os
import json
from typing import List, Dict

class WebSearch:
    def __init__(self, api_key: str, endpoint: str, cx: str):
        self.api_key = api_key
        self.endpoint = endpoint
        self.cx = cx

    def search(self, query: str, limit: int = 5) -> List[Dict]:
        # Check if API credentials are configured
        if not self.api_key or not self.cx:
            print(f"[WebSearch] WARNING: Missing API credentials, using fallback")
            return self._fallback_search(query, limit)
        
        try:
            params = {
                "key": self.api_key,
                "cx": self.cx,
                "q": query,
                "num": limit
            }
            response = requests.get(self.endpoint, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            items = data.get("items", [])
            results = [
                {"url": item.get("link"), "title": item.get("title", "")}
                for item in items
            ]
            print(f"[WebSearch] Google returned {len(results)} results for: {query}")
            return results
        except Exception as e:
            print(f"[WebSearch] Google search failed: {e}, using fallback")
            return self._fallback_search(query, limit)

    def _fallback_search(self, query: str, limit: int = 5) -> List[Dict]:
        """Fallback using DuckDuckGo Instant Answer API + web scraping"""
        results = []
        
        # Try DuckDuckGo Lite (more reliable than HTML version)
        try:
            results = self._duckduckgo_lite_search(query, limit)
            if results:
                return results
        except Exception as e:
            print(f"[WebSearch] DuckDuckGo Lite failed: {e}")
        
        # Try Bing web scraping as second fallback
        try:
            results = self._bing_scrape_search(query, limit)
            if results:
                return results
        except Exception as e:
            print(f"[WebSearch] Bing scrape failed: {e}")
        
        # Try Wikipedia API for factual queries
        try:
            results = self._wikipedia_search(query, limit)
            if results:
                return results
        except Exception as e:
            print(f"[WebSearch] Wikipedia search failed: {e}")
        
        return results

    def _duckduckgo_lite_search(self, query: str, limit: int) -> List[Dict]:
        """Scrape DuckDuckGo Lite (simpler HTML, less bot detection)"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        
        response = requests.post(
            "https://lite.duckduckgo.com/lite/",
            data={"q": query},
            headers=headers,
            timeout=15
        )
        response.raise_for_status()
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")
        
        results = []
        # DuckDuckGo Lite uses tables for results
        for link in soup.select("a.result-link")[:limit]:
            href = link.get("href", "")
            if href.startswith("http"):
                results.append({
                    "url": href,
                    "title": link.get_text(strip=True)
                })
        
        # Alternative selector for DDG Lite
        if not results:
            for row in soup.select("tr"):
                link = row.select_one("a[href^='http']")
                if link and "duckduckgo.com" not in link.get("href", ""):
                    href = link.get("href", "")
                    if href.startswith("http"):
                        results.append({
                            "url": href,
                            "title": link.get_text(strip=True)
                        })
                        if len(results) >= limit:
                            break
        
        print(f"[WebSearch] DuckDuckGo Lite returned {len(results)} results")
        return results

    def _bing_scrape_search(self, query: str, limit: int) -> List[Dict]:
        """Scrape Bing search results"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        
        response = requests.get(
            "https://www.bing.com/search",
            params={"q": query},
            headers=headers,
            timeout=15
        )
        response.raise_for_status()
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")
        
        results = []
        for item in soup.select("li.b_algo h2 a")[:limit]:
            href = item.get("href", "")
            if href.startswith("http"):
                results.append({
                    "url": href,
                    "title": item.get_text(strip=True)
                })
        
        print(f"[WebSearch] Bing scrape returned {len(results)} results")
        return results

    def _wikipedia_search(self, query: str, limit: int) -> List[Dict]:
        """Use Wikipedia API for factual queries"""
        response = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "opensearch",
                "search": query,
                "limit": limit,
                "namespace": 0,
                "format": "json"
            },
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        # OpenSearch returns [query, [titles], [descriptions], [urls]]
        if len(data) >= 4:
            titles = data[1]
            urls = data[3]
            results = [
                {"url": url, "title": title}
                for title, url in zip(titles, urls)
            ]
            print(f"[WebSearch] Wikipedia returned {len(results)} results")
            return results
        
        return []
