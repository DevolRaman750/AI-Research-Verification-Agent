from typing import List, Dict, Set
import re

from environments.web.environment import WebEnvironment
from verification.claim_extractor import ClaimExtractor, ExtractedClaim
from verification.verifier import VerificationEngine
from synthesis.answer_synthesizer import AnswerSynthesizer
from confidence.confidence_scorer import ConfidenceScorer



def normalize(text: str) -> Set[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)

    stopwords = {
        "the", "is", "a", "an", "of", "to", "and", "in",
        "for", "on", "with", "by", "as", "that", "this"
    }

    return {
        word
        for word in text.split()
        if word not in stopwords and len(word) > 3
    }


def is_relevant(claim: str, question: str) -> bool:
    return len(normalize(claim) & normalize(question)) >= 2


class ResearchAgent:
    """
    TEA-compliant Research Agent.
    Orchestrates environment → extraction → verification → confidence → meta-control → synthesis
    """

    def __init__(
        self,
        web_environment: WebEnvironment,
        claim_extractor: ClaimExtractor,
        verification_engine: VerificationEngine,
        confidence_scorer: ConfidenceScorer,
        answer_synthesizer: AnswerSynthesizer
    ):
        self.web_env = web_environment
        self.claim_extractor = claim_extractor
        self.verifier = verification_engine
        self.confidence_scorer = confidence_scorer
        self.synthesizer = answer_synthesizer

    def research(self, question: str,num_docs:int=5) -> Dict:
        """
        Single-attempt research pipeline (Planner Agent will add retries later)
        """

        

        # 1️⃣ Observe the world
        documents = self.web_env.run(question,num_docs=num_docs)

        # 2️⃣ Extract + filter claims
        extracted_claims: List[ExtractedClaim] = []

        for doc in documents:
            claims = self.claim_extractor.extract_claims(
                text=doc.text,
                source_url=doc.url
            )
            for claim in claims:
                if is_relevant(claim.claim, question):
                    extracted_claims.append(claim)

        if not extracted_claims:
            return {
                "answer": "Insufficient verified information is available to answer this question.",
                "confidence_level": "LOW",
                "confidence_reason": "No relevant claims could be extracted from available sources.",
                "evidence": [],
                "notes": "Further investigation is recommended."
            }

        # 3️⃣ Verify claims
        verified_claims = self.verifier.verify(extracted_claims)

        # 4️⃣ Score confidence
        confidence = self.confidence_scorer.score(verified_claims)

       # 5️⃣ Synthesize answer (NO decisions)
        return self.synthesizer.synthesize(
            question=question,
            verified_claims=verified_claims,
            confidence=confidence
        )


       
