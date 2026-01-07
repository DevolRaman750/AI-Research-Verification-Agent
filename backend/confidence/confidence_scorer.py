"""
Confidence Scorer

Scores the confidence of verified claims based on:
- Number of sources
- Agreement/conflict status
- Source diversity
"""

from typing import Dict, List
from verification.models import VerifiedClaim, VerificationStatus


class ConfidenceScorer:
    """
    Scores confidence based on verified claims.
    
    Confidence levels:
    - HIGH: Multiple sources agree (AGREEMENT status)
    - MEDIUM: Some agreement, minor conflicts
    - LOW: Single source, conflicts, or insufficient data
    """
    
    def score(self, verified_claims: List[VerifiedClaim]) -> Dict:
        """
        Score the confidence level based on verified claims.
        
        Returns dict with:
        - confidence_level: "HIGH", "MEDIUM", or "LOW"
        - confidence_reason: Explanation of the confidence level
        """
        if not verified_claims:
            return {
                "confidence_level": "LOW",
                "confidence_reason": "No verified claims available."
            }
        
        # Count claims by status
        agreement_count = sum(
            1 for c in verified_claims 
            if c.status == VerificationStatus.AGREEMENT
        )
        conflict_count = sum(
            1 for c in verified_claims 
            if c.status == VerificationStatus.CONFLICT
        )
        single_source_count = sum(
            1 for c in verified_claims 
            if c.status == VerificationStatus.SINGLE_SOURCE
        )
        
        total_claims = len(verified_claims)
        
        # Count unique sources across all claims
        all_sources = set()
        for claim in verified_claims:
            all_sources.update(claim.sources)
        source_count = len(all_sources)
        
        # Scoring logic
        
        # Any conflict → LOW confidence
        if conflict_count > 0:
            return {
                "confidence_level": "LOW",
                "confidence_reason": f"Conflicting information detected in {conflict_count} claim(s)."
            }
        
        # All single source → LOW confidence
        if single_source_count == total_claims:
            return {
                "confidence_level": "LOW",
                "confidence_reason": f"All {total_claims} claim(s) from single sources only (no corroboration)."
            }
        
        # No agreement → LOW confidence  
        if agreement_count == 0:
            return {
                "confidence_level": "LOW",
                "confidence_reason": "No claims have multi-source agreement."
            }
        
        # Majority agreement → HIGH confidence
        if agreement_count >= total_claims * 0.5 and source_count >= 2:
            return {
                "confidence_level": "HIGH",
                "confidence_reason": f"Strong agreement: {agreement_count}/{total_claims} claims corroborated by multiple independent sources ({source_count} total)."
            }
        
        # Some agreement but not majority → MEDIUM confidence
        if agreement_count > 0:
            return {
                "confidence_level": "MEDIUM",
                "confidence_reason": f"Partial corroboration: {agreement_count}/{total_claims} claims agreed upon."
            }
        
        # Default fallback
        return {
            "confidence_level": "LOW",
            "confidence_reason": "Insufficient evidence for confident answer."
        }
