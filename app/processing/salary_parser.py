import re
from typing import Any

# Standard exchange rates against INR for realistic CTC comparison
CURRENCY_TO_INR_RATES: dict[str, float] = {
    "INR": 1.0,
    "USD": 86.5,
    "EUR": 92.0,
    "GBP": 110.0,
    "AED": 23.5,
    "SGD": 65.0,
    "CAD": 61.0,
    "AUD": 54.0,
}


def parse_salary_lpa(salary_val: Any) -> float | None:
    """Calculates midpoint Lakhs per Annum (LPA) from normalized job fields or raw text fallback,
    converting non-INR foreign currencies to equivalent INR LPA using standard market exchange rates.

    Returns:
        float | None: Salary in LPA (e.g., 15.0 for ₹15 LPA, or ~69.2 for $80k USD), or None if unparseable.
    """
    if hasattr(salary_val, "salary_min") and salary_val.salary_min is not None:
        try:
            s_min = float(salary_val.salary_min)
            s_max = float(getattr(salary_val, "salary_max", None) or s_min)
            curr = getattr(salary_val, "currency", "INR") or "INR"
            rate = CURRENCY_TO_INR_RATES.get(curr.upper(), 1.0)
            midpoint = ((s_min + s_max) / 2.0) * rate
            return midpoint / 100_000.0
        except (ValueError, TypeError):
            pass
    if hasattr(salary_val, "salary_max") and salary_val.salary_max is not None:
        try:
            curr = getattr(salary_val, "currency", "INR") or "INR"
            s_max = float(salary_val.salary_max)
            rate = CURRENCY_TO_INR_RATES.get(curr.upper(), 1.0)
            return (s_max * rate) / 100_000.0
        except (ValueError, TypeError):
            pass

    raw = (
        getattr(salary_val, "salary_raw", None)
        if hasattr(salary_val, "salary_raw")
        else (salary_val if isinstance(salary_val, str) else None)
    )
    if not raw:
        return None

    s_min, s_max, curr = parse_salary(raw)
    if s_min is not None or s_max is not None:
        val_min = float(s_min if s_min is not None else s_max)
        val_max = float(s_max if s_max is not None else s_min)
        rate = CURRENCY_TO_INR_RATES.get(curr.upper(), 1.0)
        midpoint = ((val_min + val_max) / 2.0) * rate
        return midpoint / 100_000.0
    return None


def format_salary_display(
    salary_min: float | None,
    salary_max: float | None,
    currency: str = "INR",
    salary_raw: str | None = None,
) -> str:
    """Formats salary string for UI display.
    If currency is foreign (USD, EUR, GBP, AED, SGD), appends the approximate INR LPA conversion.

    Examples:
        (80000.0, 120000.0, "USD") -> "$80k - $120k / yr (~₹69.2 - 103.8 LPA)"
        (180000.0, 240000.0, "AED") -> "180k - 240k AED / yr (~₹42.3 - 56.4 LPA)"
        (800000.0, 1400000.0, "INR") -> "₹8 - 14 LPA"
    """
    if salary_min is None and salary_max is None:
        return salary_raw or ""

    s_min = float(salary_min) if salary_min is not None else None
    s_max = float(salary_max) if salary_max is not None else None

    curr = (currency or "INR").upper()
    rate = CURRENCY_TO_INR_RATES.get(curr, 1.0)

    if curr == "INR":
        if s_min is not None and s_max is not None:
            min_lpa = round(s_min / 100_000.0, 1)
            max_lpa = round(s_max / 100_000.0, 1)
            min_str = int(min_lpa) if min_lpa.is_integer() else min_lpa
            max_str = int(max_lpa) if max_lpa.is_integer() else max_lpa
            return f"₹{min_str} - {max_str} LPA"
        elif s_max is not None:
            max_lpa = round(s_max / 100_000.0, 1)
            max_str = int(max_lpa) if max_lpa.is_integer() else max_lpa
            return f"Up to ₹{max_str} LPA"
        elif s_min is not None:
            min_lpa = round(s_min / 100_000.0, 1)
            min_str = int(min_lpa) if min_lpa.is_integer() else min_lpa
            return f"From ₹{min_str} LPA"

    # Foreign Currency with INR LPA Conversion
    min_inr_lpa = round((s_min * rate) / 100_000.0, 1) if s_min is not None else None
    max_inr_lpa = round((s_max * rate) / 100_000.0, 1) if s_max is not None else None

    sym = "$" if curr == "USD" else ("€" if curr == "EUR" else ("£" if curr == "GBP" else f"{curr} "))

    def fmt_num(n: float) -> str:
        if n >= 1000:
            val = round(n / 1000.0, 1)
            return f"{int(val) if val.is_integer() else val}k"
        return f"{int(n)}"

    if s_min is not None and s_max is not None:
        base = f"{sym}{fmt_num(s_min)} - {sym}{fmt_num(s_max)} / yr"
        lpa_str = f"~₹{min_inr_lpa} - {max_inr_lpa} LPA"
    elif s_max is not None:
        base = f"Up to {sym}{fmt_num(s_max)} / yr"
        lpa_str = f"~₹{max_inr_lpa} LPA"
    else:
        base = f"From {sym}{fmt_num(s_min)} / yr"
        lpa_str = f"~₹{min_inr_lpa} LPA"

    return f"{base} ({lpa_str})"


def parse_salary(salary_raw: str | None) -> tuple[float | None, float | None, str]:
    """Parses raw salary text (including Indian LPA, Lakhs, annual and monthly figures)
    into numeric min, max annual amounts and currency code.
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
    s_upper = s.upper()

    currency = "INR"
    if "AED" in s_upper or "DHS" in s_upper or "DIRHAM" in s_upper:
        currency = "AED"
    elif "SGD" in s_upper or "S$" in s_upper:
        currency = "SGD"
    elif "$" in s or "USD" in s_upper:
        currency = "USD"
    elif "€" in s or "EUR" in s_upper:
        currency = "EUR"
    elif "£" in s or "GBP" in s_upper:
        currency = "GBP"
    elif "CAD" in s_upper or "C$" in s_upper:
        currency = "CAD"
    elif "AUD" in s_upper or "A$" in s_upper:
        currency = "AUD"

    curr_prefix = r"(?:₹|INR|Rs\.?|\$|€|£|AED|SGD)?"

    # 0. Up to / Upto single LPA / Lakhs (e.g. "Up to 25 LPA", "Upto ₹18 Lakhs", "Max 30 LPA")
    up_to_lpa = re.search(
        r"(?:up\s*to|upto|max(?:imum)?)\s*" + curr_prefix + r"\s*(\d+(?:\.\d+)?)\s*(?:L|Lacs?|Lakhs?|LPA)\b",
        s,
        re.IGNORECASE,
    )
    if up_to_lpa:
        v = float(up_to_lpa.group(1))
        return None, v * 100_000.0, currency

    # 1. Lakhs / LPA / Lacs range (e.g. ₹18-35 LPA, 5-12 Lacs P.A., ₹25L - ₹36L, 14L - 24L, Rs. 10 - 15 Lakhs)
    lpa_range = re.search(
        curr_prefix + r"\s*(\d+(?:\.\d+)?)\s*(?:L|Lacs?|Lakhs?|LPA)?\s*(?:-|to)\s*" + curr_prefix + r"\s*(\d+(?:\.\d+)?)\s*(?:L|Lacs?|Lakhs?|LPA)\b",
        s,
        re.IGNORECASE,
    )
    if lpa_range:
        v1, v2 = float(lpa_range.group(1)), float(lpa_range.group(2))
        return v1 * 100_000.0, v2 * 100_000.0, currency

    # 1b. Single Lakhs / LPA value (e.g. 18 LPA, ₹25 Lakhs, Rs. 14 LPA)
    single_lpa = re.search(
        curr_prefix + r"\s*(\d+(?:\.\d+)?)\s*(?:L|Lacs?|Lakhs?|LPA)\b",
        s,
        re.IGNORECASE,
    )
    if single_lpa:
        v = float(single_lpa.group(1))
        return v * 100_000.0, None, currency

    # 1c. 'k' / 'K' thousands range (e.g. $80k - $120k, $80K - $120K / year, 120k - 180k AED)
    k_range = re.search(
        curr_prefix + r"\s*(\d+(?:\.\d+)?)\s*(?:k|K)\b\s*(?:-|to)\s*" + curr_prefix + r"\s*(\d+(?:\.\d+)?)\s*(?:k|K)\b",
        s,
        re.IGNORECASE,
    )
    if k_range:
        v1, v2 = float(k_range.group(1)) * 1000.0, float(k_range.group(2)) * 1000.0
        if "month" in s.lower():
            return v1 * 12.0, v2 * 12.0, currency
        return v1, v2, currency

    # 1d. Single 'k' / 'K' value (e.g. $100k / year, Up to $120k)
    single_k = re.search(
        r"(?:up\s*to|upto|max(?:imum)?|from)?\s*" + curr_prefix + r"\s*(\d+(?:\.\d+)?)\s*(?:k|K)\b",
        s,
        re.IGNORECASE,
    )
    if single_k:
        v = float(single_k.group(1)) * 1000.0
        is_upto = bool(re.search(r"\b(?:up\s*to|upto|max)\b", s, re.IGNORECASE))
        if "month" in s.lower():
            v *= 12.0
        if is_upto:
            return None, v, currency
        return v, None, currency

    # 2. Annual or Monthly Range (e.g. ₹400000.00/yr - ₹600000.00/yr, ₹800000 - ₹1000000 a year, Rs. 600000 - 1000000 P.A.)
    ann_range = re.search(
        curr_prefix + r"\s*(\d+(?:\.\d+)?)\s*(?:/yr|a year|p\.?a\.?)?\s*(?:-|to)\s*" + curr_prefix + r"\s*(\d+(?:\.\d+)?)\s*(?:/yr|a year|p\.?a\.?)?",
        s,
        re.IGNORECASE,
    )
    if ann_range:
        v1, v2 = float(ann_range.group(1)), float(ann_range.group(2))
        # Small numbers (< 100) are likely shorthand LPA numbers without explicit unit
        if v1 < 100 and v2 < 100:
            return v1 * 100_000.0, v2 * 100_000.0, currency
        # Monthly detection: explicit "month" keyword or numbers <= 80,000 without "yr"
        if "month" in s.lower() or (v1 <= 80_000 and v2 <= 80_000 and "yr" not in s.lower() and "year" not in s.lower() and "p.a" not in s.lower() and "pa" not in s.lower()):
            return v1 * 12.0, v2 * 12.0, currency
        return v1, v2, currency

    # 3. Monthly single (e.g. "From ₹80,000 a month", "Rs. 40,000 per month")
    monthly = re.search(
        r"(?:from\s+)?" + curr_prefix + r"\s*(\d+(?:\.\d+)?)\s*(?:a\s+month|per\s+month|/month|pm\b)",
        s,
        re.IGNORECASE,
    )
    if monthly:
        v = float(monthly.group(1))
        return v * 12.0, None, currency

    # 4. Annual single (e.g. "₹800,000 a year", "₹1200000/yr", "Rs. 1000000 P.A.")
    annual_single = re.search(
        r"(?:from\s+)?" + curr_prefix + r"\s*(\d+(?:\.\d+)?)\s*(?:/yr|a\s+year|per\s+annum|p\.?a\.?)",
        s,
        re.IGNORECASE,
    )
    if annual_single:
        v = float(annual_single.group(1))
        return v, None, currency

    return None, None, currency
