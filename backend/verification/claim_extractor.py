from pydantic import BaseModel
from typing import List
from utils.llm_client import llm_complete

# Maximum text length to send to LLM (roughly 4000 tokens)
MAX_TEXT_LENGTH = 12000


class ExtractedClaim(BaseModel):
    claim: str
    source_url: str


class ClaimExtractor:
    """
    Converts raw text into atomic factual claims.
    TEA-compliant: pure transformation, no reasoning.
    """

    def extract_claims(self, text: str, source_url: str) -> List[ExtractedClaim]:
        if not text or len(text.strip()) < 50:
            print(f"[ClaimExtractor] Text too short ({len(text) if text else 0} chars), skipping")
            return []

        # Truncate very long texts to avoid LLM timeout
        original_length = len(text)
        if len(text) > MAX_TEXT_LENGTH:
            text = text[:MAX_TEXT_LENGTH]
            print(f"[ClaimExtractor] Truncated text from {original_length} to {MAX_TEXT_LENGTH} chars")

        prompt = self._build_prompt(text)

        try:
            print(f"[ClaimExtractor] Calling LLM for {len(text)} chars from {source_url}")
            response = llm_complete(prompt)
            print(f"[ClaimExtractor] LLM response length: {len(response) if response else 0} chars")
        except Exception as e:
            print(f"[ClaimExtractor] LLM call failed: {e}")
            return []

        claims = self._parse_response(response, source_url)
        print(f"[ClaimExtractor] Parsed {len(claims)} claims from {source_url}")

        return claims
    
    def _build_prompt(self, text: str) -> str:
        return f"""
You are an information extraction system specialized in extracting SUBSTANTIVE factual claims.

Extract ONLY explicit, factual claims that contain real information about the topic.

EXTRACT (examples):
- "ONDC was launched by the Government of India in 2022"
- "ONDC is not mandatory for e-commerce platforms"
- "Amazon reported $500 billion in revenue"
- "Python 3.12 was released in October 2023"

DO NOT EXTRACT (skip these completely):
- Author names: "Written by John Smith"
- Publication dates: "Published on January 5, 2024"
- Read time: "5 min read"
- Navigation text: "Home > News > Technology"
- Social sharing: "Share on Twitter"
- Metadata: "Last updated 2 hours ago"
- Article structure: "In this article we will discuss..."
- Generic statements: "This is an important topic"

Rules:
- Extract only verifiable factual statements WITH REAL INFORMATION
- One claim per bullet (minimum 8 words each)
- Claims must contain specific facts, names, numbers, dates, or concrete information
- Ignore all metadata, timestamps, author info, navigation, UI elements
- If no substantive factual claims exist, return NONE

Return format (use exactly this format):
- <claim 1>
- <claim 2>

TEXT:
{text}
"""
    
    @staticmethod
    def is_too_short(claim: str) -> bool:
        return len(claim.split()) < 8  # Increased minimum from 6 to 8 words

    @staticmethod
    def is_boilerplate(claim: str) -> bool:
        boilerplate_keywords = [
            "member fdic",
            "all rights reserved",
            "privacy policy",
            "terms of use",
            "copyright",
            "offers checking accounts"
        ]
        claim_lower = claim.lower()
        return any(k in claim_lower for k in boilerplate_keywords)

    @staticmethod
    def is_metadata(claim: str) -> bool:
        """Filter out metadata claims like author names, dates, timestamps.
        
        Be careful NOT to filter substantive claims that happen to mention organizations.
        """
        claim_lower = claim.lower()
        words = claim_lower.split()
        
        # Only filter very short claims that are purely metadata
        # Long claims (10+ words) are likely substantive even if they contain metadata-like words
        if len(words) >= 10:
            return False
        
        # Patterns that indicate PURE metadata (not substantive content)
        pure_metadata_patterns = [
            "written by", "authored by", "posted by",
            "min read", "minute read", "reading time",
            "share on twitter", "share on facebook", "follow us", "subscribe to",
            "last modified", "last updated",
            "advertisement", "sponsored content",
            "table of contents",
            "click here", "read more about",
            "home >", "news >", "blog >",  # Breadcrumb navigation
        ]
        
        if any(p in claim_lower for p in pure_metadata_patterns):
            return True
        
        # Check if claim is ONLY about dates/times (e.g., "Published Jan 10, 2024 at 5:30 PM IST")
        import re
        # Very short claims that are mostly timestamp info
        if len(words) < 8:
            time_pattern = r'\b(\d{1,2}:\d{2}|am|pm|ist|gmt|utc)\b'
            time_matches = re.findall(time_pattern, claim_lower)
            if len(time_matches) >= 2:  # Multiple time indicators = likely pure timestamp
                return True
        
        return False
        
    def _parse_response(self, response: str, source_url: str) -> List[ExtractedClaim]:
        claims = []

        if not response:
            return claims

        lines = response.splitlines()

        for line in lines:
            line = line.strip()
            if not line.startswith("-"):
                continue

            claim_text = line.lstrip("-").strip()

            if self.is_too_short(claim_text):
                print(f"[ClaimExtractor] SKIP too short: {claim_text[:50]}...")
                continue

            if self.is_boilerplate(claim_text):
                print(f"[ClaimExtractor] SKIP boilerplate: {claim_text[:50]}...")
                continue

            if self.is_metadata(claim_text):
                print(f"[ClaimExtractor] SKIP metadata: {claim_text[:50]}...")
                continue


            claims.append(
                ExtractedClaim(
                    claim=claim_text,
                    source_url=source_url
                )
            )

        return claims

        return claims
    
   




