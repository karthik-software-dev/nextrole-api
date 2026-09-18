import re


def extract_experience(text: str | None) -> tuple[int | None, int | None, str | None]:
    """Extracts minimum experience, maximum experience, and formatted raw string from job text.

    Returns:
        tuple[int | None, int | None, str | None]: (min_exp, max_exp, raw_exp_str)
    """
    if not text:
        return None, None, None

    clean_text = text.replace("\u00a0", " ")

    # 1. Experience Range: e.g. "1-3 years", "2 to 5 Yrs", "0 - 2 yrs", "1-4 years of experience"
    range_match = re.search(
        r"\b(\d{1,2})\s*(?:-|to)\s*(\d{1,2})\s*(?:years?|yrs?)(?:\s+(?:of\s+)?(?:relevant\s+)?(?:software\s+)?(?:work\s+)?experience)?\b",
        clean_text,
        re.IGNORECASE,
    )
    if range_match:
        val1, val2 = int(range_match.group(1)), int(range_match.group(2))
        if val1 <= 30 and val2 <= 30 and val1 <= val2:
            return val1, val2, f"{val1}-{val2} Yrs"

    # 2. Explicit Minimum: e.g. "minimum 2 years of experience", "at least 3 yrs", "min 1 year"
    min_match = re.search(
        r"\b(?:at\s+least|minimum|min)\s*(\d{1,2})\+?\s*(?:years?|yrs?)(?:\s+(?:of\s+)?(?:relevant\s+)?(?:software\s+)?(?:work\s+)?experience)?\b",
        clean_text,
        re.IGNORECASE,
    )
    if min_match:
        val = int(min_match.group(1))
        if val <= 30:
            return val, None, f"{val}+ Yrs"

    # 3. Plus notation with experience: e.g. "2+ years of experience", "3+ yrs", "5+ years of relevant experience"
    plus_match = re.search(
        r"\b(\d{1,2})\+\s*(?:years?|yrs?)(?:\s+(?:of\s+)?(?:relevant\s+)?(?:software\s+)?(?:work\s+)?experience)?\b",
        clean_text,
        re.IGNORECASE,
    )
    if plus_match:
        val = int(plus_match.group(1))
        if val <= 30:
            return val, None, f"{val}+ Yrs"

    # 4. Standard "X years of experience": e.g. "2 years of software experience"
    exact_match = re.search(
        r"\b(\d{1,2})\s*(?:years?|yrs?)\s+of\s+(?:relevant\s+)?(?:software\s+)?(?:work\s+)?experience\b",
        clean_text,
        re.IGNORECASE,
    )
    if exact_match:
        val = int(exact_match.group(1))
        if val <= 30:
            return val, None, f"{val}+ Yrs"

    return None, None, None
