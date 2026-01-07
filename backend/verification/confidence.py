from verification.models import VerificationStatus


def confidence_from_status(status: VerificationStatus) -> str:
    if status == VerificationStatus.AGREEMENT:
        return "HIGH"
    if status == VerificationStatus.SINGLE_SOURCE:
        return "LOW"
    if status == VerificationStatus.CONFLICT:
        return "LOW"
    return "UNKNOWN"
