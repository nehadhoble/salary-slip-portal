"""Amount formatting - mirrors app/src/main/java/.../data/AmountInWords.kt"""
from decimal import Decimal, ROUND_HALF_UP

ONES = [
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
    "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
    "Seventeen", "Eighteen", "Nineteen",
]
TENS = [
    "", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety",
]


def _two_digit_words(n):
    if n == 0:
        return ""
    if n < 20:
        return ONES[n]
    tail = f" {ONES[n % 10]}" if n % 10 != 0 else ""
    return f"{TENS[n // 10]}{tail}".strip()


def _three_digit_words(n):
    hundreds = n // 100
    rest = n % 100
    parts = ""
    if hundreds > 0:
        parts += f"{ONES[hundreds]} Hundred"
        if rest > 0:
            parts += " "
    if rest > 0:
        parts += _two_digit_words(rest)
    return parts


def number_to_indian_words(number):
    """Converts a non-negative whole number into Indian-numbering words (Crore/Lakh/Thousand)."""
    if number == 0:
        return "Zero"
    n = number
    crore, n = divmod(n, 10_000_000)
    lakh, n = divmod(n, 100_000)
    thousand, n = divmod(n, 1_000)
    hundred = n

    parts = []
    if crore > 0:
        parts.append(f"{_three_digit_words(crore)} Crore")
    if lakh > 0:
        parts.append(f"{_three_digit_words(lakh)} Lakh")
    if thousand > 0:
        parts.append(f"{_three_digit_words(thousand)} Thousand")
    if hundred > 0:
        parts.append(_three_digit_words(hundred))
    return " ".join(parts).strip()


def amount_to_words(amount):
    """e.g. "INR Fifty Four Thousand One Hundred Sixty Six and Ninety Nine Paise Only" """
    rounded = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    rupees = int(rounded)
    paise = int((rounded - rupees) * 100)

    rupee_words = number_to_indian_words(rupees)
    if paise > 0:
        return f"INR {rupee_words} and {number_to_indian_words(paise)} Paise Only"
    return f"INR {rupee_words} Only"


def _indian_group(int_part_str):
    if len(int_part_str) <= 3:
        return int_part_str
    last3 = int_part_str[-3:]
    rest = int_part_str[:-3]
    groups = []
    while len(rest) > 2:
        groups.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        groups.insert(0, rest)
    return ",".join(groups + [last3])


def format_amount(amount):
    """e.g. 54166.99 -> "54,166.99" using Indian digit grouping."""
    rounded = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sign = "-" if rounded < 0 else ""
    rounded = abs(rounded)
    int_part, frac_part = f"{rounded:.2f}".split(".")
    return f"{sign}{_indian_group(int_part)}.{frac_part}"
