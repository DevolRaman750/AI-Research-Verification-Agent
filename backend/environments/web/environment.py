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
            results = self.search_client.search(query, limit=limit)
        except Exception as e:
            self.state.errors.append(str(e))
            return []

        for result in results:
            url = result["url"]

            if self.is_blocked_domain(url):
                continue

            if url in self.state.visited_urls:
                continue

            try:
                html = self.fetcher.fetch(url)
                text, metadata = self.extractor.extract(html)

                if len(text) < MIN_TEXT_LENGTH:
                    continue

                doc = WebDocument(
                    url=url,
                    title=metadata.get("title"),
                    text=text,
                    metadata=metadata
                )

                self.state.visited_urls.append(url)
                self.state.documents.append(doc)

            except Exception as e:
                self.state.errors.append(f"{url}: {str(e)}")

        return self.state.documents
