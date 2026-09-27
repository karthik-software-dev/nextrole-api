import re


def parse_salary(salary_raw: str | None) -> tuple[float | None, float | None, str]:
    """Parses raw salary text (including Indian LPA, Lakhs, annual and monthly figures)
    into numeric min, max annual amounts and currency code.

    Examples:
        "₹18-35 LPA" -> (1800000.0, 3500000.0, "INR")
        "5-12 Lacs P.A." -> (500000.0, 1200000.0, "INR")
        "₹25L – ₹36L" -> (2500000.0, 3600000.0, "INR")
        "₹8,00,000 - ₹10,00,000 a year" -> (800000.0, 1000000.0, "INR")
        "₹400,000.00/yr - ₹600,000.00/yr" -> (400000.0, 600000.0, "INR")
        "From ₹80,000 a month" -> (960000.0, None, "INR")
        "₹30,000 – ₹40,000" -> (360000.0, 480000.0, "INR")
        "No equity" -> (None, None, "INR")

    Returns:
        tuple[float | None, float | None, str]: (salary_min, salary_max, currency)
    """
    if not salary_raw:
        return None, None, "INR"

    s = (
        salary_raw.strip()
        .replace(",", "")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("—", "-")
    )

    currency = "INR"
    if "$" in s or "USD" in s:
        currency = "USD"
    elif "€" in s or "EUR" in s:
        currency = "EUR"
    elif "£" in s or "GBP" in s:
        currency = "GBP"

    # 1. Lakhs / LPA / Lacs range (e.g. ₹18-35 LPA, 5-12 Lacs P.A., ₹25L - ₹36L, 14L - 24L)
    lpa_range = re.search(
        r"(?:₹|INR|\$)?\s*(\d+(?:\.\d+)?)\s*(?:L|Lacs?|Lakhs?|LPA)?\s*(?:-|to)\s*(?:₹|INR|\$)?\s*(\d+(?:\.\d+)?)\s*(?:L|Lacs?|Lakhs?|LPA)",
        s,
        re.IGNORECASE,
    )
    if lpa_range:
        v1, v2 = float(lpa_range.group(1)), float(lpa_range.group(2))
        return v1 * 100_000.0, v2 * 100_000.0, currency

    # 1b. Single Lakhs / LPA value (e.g. 18 LPA, ₹25 Lakhs)
    single_lpa = re.search(
        r"(?:₹|INR|\$)?\s*(\d+(?:\.\d+)?)\s*(?:L|Lacs?|Lakhs?|LPA)\b",
        s,
        re.IGNORECASE,
    )
    if single_lpa:
        v = float(single_lpa.group(1))
        return v * 100_000.0, None, currency

    # 2. Annual or Monthly Range (e.g. ₹400000.00/yr - ₹600000.00/yr, ₹800000 - ₹1000000 a year, ₹30000 - ₹40000)
    ann_range = re.search(
        r"(?:₹|INR|\$)?\s*(\d+(?:\.\d+)?)\s*(?:/yr|a year)?\s*(?:-|to)\s*(?:₹|INR|\$)?\s*(\d+(?:\.\d+)?)\s*(?:/yr|a year)?",
        s,
        re.IGNORECASE,
    )
    if ann_range:
        v1, v2 = float(ann_range.group(1)), float(ann_range.group(2))
        # Small numbers (< 100) are likely shorthand LPA numbers without explicit unit
        if v1 < 100 and v2 < 100:
            return v1 * 100_000.0, v2 * 100_000.0, currency
        # Monthly detection: explicit "month" keyword or numbers <= 80,000 without "yr"
        if "month" in s.lower() or (v1 <= 80_000 and v2 <= 80_000 and "yr" not in s.lower() and "year" not in s.lower()):
            return v1 * 12.0, v2 * 12.0, currency
        return v1, v2, currency

    # 3. Monthly single (e.g. "From ₹80,000 a month")
    monthly = re.search(
        r"(?:from\s+)?(?:₹|INR|\$)?\s*(\d+(?:\.\d+)?)\s*a\s+month",
        s,
        re.IGNORECASE,
    )
    if monthly:
        v = float(monthly.group(1))
        return v * 12.0, None, currency

    # 4. Annual single (e.g. "₹800,000 a year", "₹1200000/yr")
    annual_single = re.search(
        r"(?:from\s+)?(?:₹|INR|\$)?\s*(\d+(?:\.\d+)?)\s*(?:/yr|a\s+year)",
        s,
        re.IGNORECASE,
    )
    if annual_single:
        v = float(annual_single.group(1))
        return v, None, currency

    return None, None, currency
