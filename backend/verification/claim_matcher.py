from typing import List
from verification.models import VerifiedClaim
from verification.claim_extractor import ExtractedClaim
from utils.embedding import embed_text, cosine_similarity


SIMILARITY_THRESHOLD = 0.85


class ClaimMatcher:
    def group_similar_claims(
        self, claims: List[ExtractedClaim]
    ) -> List[List[ExtractedClaim]]:
        groups: List[List[ExtractedClaim]] = []

        embeddings = [embed_text(c.claim) for c in claims]

        for i, claim in enumerate(claims):
            placed = False

            for group_idx, group in enumerate(groups):
                rep_idx = claims.index(group[0])
                sim = cosine_similarity(embeddings[i], embeddings[rep_idx])

                if sim >= SIMILARITY_THRESHOLD:
                    group.append(claim)
                    placed = True
                    break

            if not placed:
                groups.append([claim])

        return groups
