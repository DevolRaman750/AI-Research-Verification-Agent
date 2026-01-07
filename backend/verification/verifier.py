from typing import List
from verification.models import VerifiedClaim, VerificationStatus
from verification.claim_extractor import ExtractedClaim
from verification.claim_matcher import ClaimMatcher
from utils.polarity import polarity_score


class VerificationEngine:
    def __init__(self):
        self.matcher = ClaimMatcher()

    def _is_conflicting(self, claim_a: str, claim_b: str) -> bool:
        """
        Detects conflict using polarity.
        Positive vs negative stance → conflict.
        """
        score_a = polarity_score(claim_a)
        score_b = polarity_score(claim_b)

        return score_a * score_b < 0  # opposite signs

    def verify(
        self, extracted_claims: List[ExtractedClaim]
    ) -> List[VerifiedClaim]:

        grouped_claims = self.matcher.group_similar_claims(extracted_claims)
        verified_results: List[VerifiedClaim] = []

        for group in grouped_claims:
            sources = list({c.source_url for c in group})
            representative_claim = group[0].claim

            # 🟢 CASE 1: Only one source
            if len(sources) == 1:
                status = VerificationStatus.SINGLE_SOURCE

            # 🟡 CASE 2: Multiple sources → check conflict
            else:
                conflict_found = False

                for i in range(len(group)):
                    for j in range(i + 1, len(group)):
                        if self._is_conflicting(
                            group[i].claim,
                            group[j].claim
                        ):
                            conflict_found = True
                            break
                    if conflict_found:
                        break

                status = (
                    VerificationStatus.CONFLICT
                    if conflict_found
                    else VerificationStatus.AGREEMENT
                )

            verified_results.append(
                VerifiedClaim(
                    claim=representative_claim,
                    sources=sources,
                    status=status
                )
            )

        return verified_results
