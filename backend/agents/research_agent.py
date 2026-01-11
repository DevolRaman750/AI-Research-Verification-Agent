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
        "for", "on", "with", "by", "as", "that", "this",
        "what", "how", "why", "when", "where", "which",
        "does", "do", "are", "was", "were", "will", "would",
        "can", "could", "should", "must", "may", "might"
    }

    return {
        word
        for word in text.split()
        if word not in stopwords and len(word) > 2  # Allow shorter words like "api", "aws"
    }


def is_relevant(claim: str, question: str) -> bool:
    """Check if a claim is relevant to the question.
    
    More permissive matching - requires at least 1 significant keyword overlap.
    """
    claim_words = normalize(claim)
    question_words = normalize(question)
    overlap = claim_words & question_words
    
    # At least 1 keyword match is enough 
    is_match = len(overlap) >= 1
    
    if not is_match:
        print(f"[Relevance] SKIP claim (no overlap): claim_words={list(claim_words)[:5]}... question_words={list(question_words)}")
    
    return is_match


class ResearchAgent:
    """
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

        print(f"[ResearchAgent] Starting research for: {question}")

        #  Observe the world
        documents = self.web_env.run(question,num_docs=num_docs)
        print(f"[ResearchAgent] Retrieved {len(documents)} documents")

        #  Extract + filter claims
        extracted_claims: List[ExtractedClaim] = []

        for doc in documents:
            print(f"[ResearchAgent] Extracting claims from: {doc.url}")
            claims = self.claim_extractor.extract_claims(
                text=doc.text,
                source_url=doc.url
            )
            print(f"[ResearchAgent] Found {len(claims)} raw claims from {doc.url}")
            for claim in claims:
                if is_relevant(claim.claim, question):
                    extracted_claims.append(claim)
            print(f"[ResearchAgent] {len(extracted_claims)} total relevant claims so far")

        if not extracted_claims:
            print(f"[ResearchAgent] No relevant claims extracted, returning low confidence")
            return {
                "answer": "Insufficient verified information is available to answer this question.",
                "confidence_level": "LOW",
                "confidence_reason": "No relevant claims could be extracted from available sources.",
                "evidence": [],
                "notes": "Further investigation is recommended."
            }

        print(f"[ResearchAgent] Total extracted claims: {len(extracted_claims)}")

        #  Verify claims
        verified_claims = self.verifier.verify(extracted_claims)
        print(f"[ResearchAgent] Verified {len(verified_claims)} claims")

        #  Score confidence
        confidence = self.confidence_scorer.score(verified_claims)
        print(f"[ResearchAgent] Confidence: {confidence}")

       #  Synthesize answer (NO decisions)
        return self.synthesizer.synthesize(
            question=question,
            verified_claims=verified_claims,
            confidence=confidence
        )


       
