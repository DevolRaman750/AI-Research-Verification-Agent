from bs4 import BeautifulSoup


class WebExtractor:
    def extract(self, html: str) -> tuple[str, dict]:
        soup = BeautifulSoup(html, "html.parser")

        # Remove scripts & styles
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text = " ".join(soup.stripped_strings)

        metadata = {}
        title = soup.title.string if soup.title else None
        if title:
            metadata["title"] = title

        return text, metadata
