from typing import List, Dict, Optional
from verification.models import VerifiedClaim, VerificationStatus


class VerificationDecision:
    ACCEPT = "ACCEPT"
    RETRY = "RETRY"
    STOP = "STOP"


class VerificationAgent:
    """
    TEA-compatible Verification Agent (Meta-Control).
    Decides whether verification is sufficient or needs improvement.
    """

    def decide(
        self,
        verified_claims: List[VerifiedClaim],
        confidence: Dict,
        attempt: int,
        max_attempts: int = 3
    ) -> Dict:
        """
        Decide whether to ACCEPT, RETRY, or STOP verification.

        Returns:
        {
            "decision": str,
            "reason": str,
            "recommendation": Optional[str]
        }
        """

        confidence_level = confidence.get("confidence_level")
        confidence_reason = confidence.get("confidence_reason", "")

        # --- Case 0: No claims at all ---
        if not verified_claims:
            if attempt >= max_attempts:
                return {
                    "decision": VerificationDecision.STOP,
                    "reason": (
                        "No verifiable claims could be found after multiple attempts."
                    ),
                    "recommendation": None
                }

            return {
                "decision": VerificationDecision.RETRY,
                "reason": (
                    "No verifiable claims were found. Additional sources may help."
                ),
                "recommendation": "Search broader or alternative sources."
            }

        statuses = {c.status for c in verified_claims}

        # --- Case 1: Conflicting evidence ---
        if VerificationStatus.CONFLICT in statuses:
            if attempt >= max_attempts:
                return {
                    "decision": VerificationDecision.STOP,
                    "reason": (
                        "Conflicting evidence persists despite additional verification attempts."
                    ),
                    "recommendation": None
                }

            return {
                "decision": VerificationDecision.RETRY,
                "reason": (
                    "Sources provide conflicting evidence. Further verification may resolve discrepancies."
                ),
                "recommendation": "Seek additional independent sources."
            }

        # --- Case 2: HIGH confidence ---
        if confidence_level == "HIGH":
            return {
                "decision": VerificationDecision.ACCEPT,
                "reason": (
                    "Multiple independent sources agree on the same claim. "
                    "Further verification is unlikely to change the conclusion."
                ),
                "recommendation": None
            }

        # --- Case 3: MEDIUM confidence ---
        if confidence_level == "MEDIUM":
            return {
                "decision": VerificationDecision.ACCEPT,
                "reason": (
                    "Evidence from multiple sources broadly supports the conclusion, "
                    "though agreement is limited."
                ),
                "recommendation": None
            }

        # --- Case 4: LOW confidence (single-source or weak evidence) ---
        if confidence_level == "LOW":
            if attempt >= max_attempts:
                return {
                    "decision": VerificationDecision.STOP,
                    "reason": (
                        "Confidence remains low after repeated attempts. "
                        "Further verification is unlikely to improve certainty."
                    ),
                    "recommendation": None
                }

            return {
                "decision": VerificationDecision.RETRY,
                "reason": (
                    "The conclusion is based on limited evidence. "
                    "Additional independent sources may improve confidence."
                ),
                "recommendation": "Search for authoritative or corroborating sources."
            }

        # --- Fallback (should never happen) ---
        return {
            "decision": VerificationDecision.STOP,
            "reason": "Unable to determine verification status reliably.",
            "recommendation": None
        }
