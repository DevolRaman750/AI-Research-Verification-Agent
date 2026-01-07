import requests
from typing import List, Dict

class WebSearch:
    def __init__(self, api_key: str, endpoint: str, cx: str):
        self.api_key = api_key
        self.endpoint = endpoint
        self.cx = cx

    def search(self, query: str, limit: int = 5) -> List[Dict]:
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
        return [
            {"url": item.get("link"), "title": item.get("title", "")}
            for item in items
        ]
