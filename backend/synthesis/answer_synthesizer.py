from typing import List, Dict, Optional
from verification.models import VerifiedClaim
from utils.llm_client import llm_complete

from storage.repositories.answer_repo import AnswerSnapshotRepository
from storage.repositories.evidence_repo import EvidenceRepository
from sqlalchemy.orm import Session
from uuid import UUID



def build_prompt(
    question: str,
    claims: List[VerifiedClaim],
    confidence_level: str
) -> str:
    claim_lines = []

    for c in claims:
        
        claim_lines.append(
            f"- {c.claim} (Status: {c.status.value})"
        )

    claims_block = "\n".join(claim_lines)

    return f"""
You are a professional research summarizer.

STRICT RULES:
- Use ONLY the claims provided
- Do NOT add new facts
- Do NOT infer or speculate
- Do NOT change claim meaning
- Be cautious and professional in tone
- One short paragraph only

Question:
{question}

Verified Claims:
{claims_block}

Overall Confidence Level: {confidence_level}

Compose a clear, honest answer based ONLY on the above.
"""
def generate_notes(confidence_level: str) -> Optional[str]:
    if confidence_level == "LOW":
        return (
            "The available evidence is limited or conflicting. "
            "Further independent confirmation is recommended."
        )
    return None

class AnswerSynthesizer:

    def __init__(
        self,
        answer_repo: AnswerSnapshotRepository,
        evidence_repo: EvidenceRepository
    ):
        self.answer_repo = answer_repo
        self.evidence_repo = evidence_repo

    def synthesize(
        self,
        question: str,
        verified_claims: List[VerifiedClaim],
        confidence: Dict,
        session_id: UUID,
        db: Session
    ) -> Dict:

        if not verified_claims:
            return {
                "answer": "Insufficient verified information is available to answer this question.",
                "confidence_level": "LOW",
                "confidence_reason": "No verifiable claims were found.",
                "evidence": [],
                "notes": "No relevant claims could be extracted."
            }

        confidence_level = confidence["confidence_level"]
        confidence_reason = confidence["confidence_reason"]

        # 1️⃣ Build controlled prompt
        prompt = build_prompt(
            question,
            verified_claims,
            confidence_level
        )

        # 2️⃣ Generate answer text (LLM used ONLY for phrasing)
        answer_text = llm_complete(prompt)
        self.answer_repo.create(
        db=db,
        session_id=session_id,
        answer_text=answer_text,
        confidence_level=confidence_level,
        confidence_reason=confidence_reason
        )

        # 3️⃣ Attach evidence verbatim
        evidence = []
        for c in verified_claims:
            self.evidence_repo.create(
                db=db,
                session_id=session_id,
                claim=c.claim,
                status=c.status.value,
                sources=c.sources
            )
            evidence.append({
                "claim": c.claim,
                "status": c.status.value,
                "sources": c.sources
            })

        # 4️⃣ Optional notes
        notes = generate_notes(confidence_level)

        return {
            "answer": answer_text,
            "confidence_level": confidence_level,
            "confidence_reason": confidence_reason,
            "evidence": evidence,
            "notes": notes
        }




def build_prompt(
    question: str,
    claims: List[VerifiedClaim],
    confidence_level: str
) -> str:
    claim_lines = []

    for c in claims:
        claim_lines.append(
            f"- {c.claim} (Status: {c.status.value})"
        )

    claims_block = "\n".join(claim_lines)

    return f"""
You are a professional research summarizer.

STRICT RULES:
- Use ONLY the claims provided
- Do NOT add new facts
- Do NOT infer or speculate
- Do NOT change claim meaning
- Be cautious and professional in tone
- One short paragraph only

Question:
{question}

Verified Claims:
{claims_block}

Overall Confidence Level: {confidence_level}

Compose a clear, honest answer based ONLY on the above.
"""
def generate_notes(confidence_level: str) -> Optional[str]:
    if confidence_level == "LOW":
        return (
            "The available evidence is limited or conflicting. "
            "Further independent confirmation is recommended."
        )
    return None

class AnswerSynthesizer:

    def synthesize(
        self,
        question: str,
        verified_claims: List[VerifiedClaim],
        confidence: Dict
    ) -> Dict:

        if not verified_claims:
            return {
                "answer": "Insufficient verified information is available to answer this question.",
                "confidence_level": "LOW",
                "confidence_reason": "No verifiable claims were found.",
                "evidence": [],
                "notes": "No relevant claims could be extracted."
            }

        confidence_level = confidence["confidence_level"]
        confidence_reason = confidence["confidence_reason"]

        # 1️⃣ Build controlled prompt
        prompt = build_prompt(
            question,
            verified_claims,
            confidence_level
        )

        # 2️⃣ Generate answer text (LLM used ONLY for phrasing)
        answer_text = llm_complete(prompt)
        

        # 3️⃣ Attach evidence verbatim
        evidence = [
            {
                "claim": c.claim,
                "status": c.status.value,
                "sources": c.sources
            }
            for c in verified_claims
        ]

        # 4️⃣ Optional notes
        notes = generate_notes(confidence_level)

        return {
            "answer": answer_text,
            "confidence_level": confidence_level,
            "confidence_reason": confidence_reason,
            "evidence": evidence,
            "notes": notes
        }

