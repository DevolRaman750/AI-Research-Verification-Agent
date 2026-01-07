from typing import List

# Simple verb-based polarity indicators
POSITIVE_KEYWORDS: List[str] = [
    "reduce",
    "decrease",
    "lower",
    "decline",
    "fall",
    "slow",
    "limit",
    "control",
    "curb"
]

NEGATIVE_KEYWORDS: List[str] = [
    "increase",
    "rise",
    "raise",
    "boost",
    "accelerate",
    "worsen",
    "expand"
]


def polarity_score(text: str) -> int:
    """
    Returns:
    +1 → positive assertion (e.g., reduces inflation)
    -1 → negative assertion (e.g., increases inflation)
     0 → neutral / unclear
    """

    text = text.lower()

    positive_hits = sum(word in text for word in POSITIVE_KEYWORDS)
    negative_hits = sum(word in text for word in NEGATIVE_KEYWORDS)

    if positive_hits > negative_hits:
        return +1
    elif negative_hits > positive_hits:
        return -1
    else:
        return 0
