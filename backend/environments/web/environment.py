from typing import List
from environments.base import Environment
from environments.web.state import WebEnvironmentState, WebDocument
from environments.web.search import WebSearch
from environments.web.fetch import WebFetcher
from environments.web.extract import WebExtractor
from urllib.parse import urlparse
from constants.rules import BLOCKED_DOMAINS, MIN_TEXT_LENGTH

class WebEnvironment(Environment):
    MAX_PAGES = 5

    def __init__(self, search_client: WebSearch):
        self.search_client = search_client
        self.fetcher = WebFetcher()
        self.extractor = WebExtractor()
        self.state = WebEnvironmentState()

    def reset(self) -> None:
        self.state = WebEnvironmentState()

    def observe(self):
        return self.state.dict()
    
    def is_blocked_domain(self, url: str) -> bool:
        domain = urlparse(url).netloc.lower()
        return any(blocked in domain for blocked in BLOCKED_DOMAINS)


    def run(self, query: str, num_docs: int | None = None) -> List[WebDocument]:
        self.reset()
        self.state.query = query

        try:
            limit = self.MAX_PAGES
            if num_docs is not None:
                limit = max(1, min(int(num_docs), self.MAX_PAGES))
            print(f"[WebEnvironment] Searching for: {query} (limit={limit})")
            results = self.search_client.search(query, limit=limit)
            print(f"[WebEnvironment] Search returned {len(results)} results")
        except Exception as e:
            print(f"[WebEnvironment] Search error: {e}")
            self.state.errors.append(str(e))
            return []

        for result in results:
            url = result["url"]
            print(f"[WebEnvironment] Processing: {url}")

            if self.is_blocked_domain(url):
                print(f"[WebEnvironment] Blocked domain: {url}")
                continue

            if url in self.state.visited_urls:
                print(f"[WebEnvironment] Already visited: {url}")
                continue

            try:
                html = self.fetcher.fetch(url)
                text, metadata = self.extractor.extract(html)
                print(f"[WebEnvironment] Extracted {len(text)} chars from {url}")

                if len(text) < MIN_TEXT_LENGTH:
                    print(f"[WebEnvironment] Text too short ({len(text)} < {MIN_TEXT_LENGTH}): {url}")
                    continue

                doc = WebDocument(
                    url=url,
                    title=metadata.get("title"),
                    text=text,
                    metadata=metadata
                )

                self.state.visited_urls.append(url)
                self.state.documents.append(doc)
                print(f"[WebEnvironment] Added document: {url}")

            except Exception as e:
                print(f"[WebEnvironment] Fetch/extract error for {url}: {e}")
                self.state.errors.append(f"{url}: {str(e)}")

        print(f"[WebEnvironment] Total documents collected: {len(self.state.documents)}")
        return self.state.documents
