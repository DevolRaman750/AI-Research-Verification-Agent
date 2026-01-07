from pydantic import BaseModel
from typing import List
from utils.llm_client import llm_complete


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
            return []

        prompt = self._build_prompt(text)

        response = llm_complete(prompt)

        claims = self._parse_response(response, source_url)

        return claims
    
    def _build_prompt(self, text: str) -> str:
        return f"""
        You are an information extraction system.

        Extract ONLY explicit, factual claims from the text below.

        Rules:
        - Extract only verifiable factual statements
        - One claim per bullet
        - Do NOT summarize
        - Do NOT infer
        - Do NOT rewrite meaning
        - Ignore navigation, menus, UI text
        - If no factual claims exist, return NONE

        Return format:
        - <claim 1>
        - <claim 2>

        TEXT:
        {text}
        """
    
    @staticmethod
    def is_too_short(claim: str) -> bool:
        return len(claim.split()) < 6

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
                continue

            if self.is_boilerplate(claim_text):
                continue


            claims.append(
                ExtractedClaim(
                    claim=claim_text,
                    source_url=source_url
                )
            )

        return claims
    
   




