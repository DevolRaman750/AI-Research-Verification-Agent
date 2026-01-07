import requests
from tenacity import retry, stop_after_attempt, wait_fixed


class WebFetcher:
    def __init__(self, timeout: int = 8):
        self.timeout = timeout

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def fetch(self, url: str) -> str:
        headers = {
            "User-Agent": "TEA-Research-Agent/1.0"
        }
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response.text
