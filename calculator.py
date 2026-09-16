"""Earnings breakdown calculation - mirrors app/src/main/java/.../data/SalaryCalculator.kt

Total Earnings is the one fixed number the user enters; every other earning is
derived from it so the breakdown always adds back up exactly. Basic/HRA/LTA/Other
are percentages (editable via FormulaSettings); Conveyance absorbs the rounding
remainder so the printed Total Earnings never drifts from user input.
"""
from decimal import Decimal, ROUND_HALF_UP

DEFAULT_SETTINGS = {
    "basic_pct": 30.0,
    "hra_pct": 50.0,
    "lta_pct": 55.0,
    "other_pct": 84.0,
}


def _round2(value):
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def settings_is_valid(settings):
    basic_pct = settings["basic_pct"]
    hra_pct = settings["hra_pct"]
    lta_pct = settings["lta_pct"]
    other_pct = settings["other_pct"]
    if not (0.0 <= basic_pct <= 100.0):
        return False
    if hra_pct < 0.0 or lta_pct < 0.0 or other_pct < 0.0:
        return False
    basic_fraction = basic_pct / 100.0
    combined_fraction = (100.0 + hra_pct + lta_pct + other_pct) / 100.0
    return basic_fraction * combined_fraction < 1.0


def calculate(total_earnings, settings=None, tds=0.0, leave=0.0):
    """Returns a dict breakdown: basic_pay, conveyance_allowance, hra, lta,
    other_allowances, total_earnings, tds, leave, deduction, net_amount.

    tds and leave are the two slip-level deductions; deduction is their sum,
    subtracted from total_earnings to get net_amount (floored at zero)."""
    settings = settings or DEFAULT_SETTINGS
    tds = _round2(max(0.0, tds or 0.0))
    leave = _round2(max(0.0, leave or 0.0))
    deduction = _round2(tds + leave)
    if total_earnings is None or total_earnings <= 0.0:
        return {
            "basic_pay": 0.0,
            "conveyance_allowance": 0.0,
            "hra": 0.0,
            "lta": 0.0,
            "other_allowances": 0.0,
            "total_earnings": 0.0,
            "tds": tds,
            "leave": leave,
            "deduction": deduction,
            "net_amount": 0.0,
        }
    basic = _round2(total_earnings * settings["basic_pct"] / 100.0)
    hra = _round2(basic * settings["hra_pct"] / 100.0)
    lta = _round2(basic * settings["lta_pct"] / 100.0)
    other = _round2(basic * settings["other_pct"] / 100.0)
    conveyance = _round2(total_earnings - (basic + hra + lta + other))
    return {
        "basic_pay": basic,
        "conveyance_allowance": conveyance,
        "hra": hra,
        "lta": lta,
        "other_allowances": other,
        "total_earnings": total_earnings,
        "tds": tds,
        "leave": leave,
        "deduction": deduction,
        "net_amount": _round2(max(0.0, total_earnings - deduction)),
    }


def breakdown_rows(breakdown):
    """List[(label, amount)] matching EarningsBreakdown.rows in the Kotlin app."""
    return [
        ("Basic Pay", breakdown["basic_pay"]),
        ("Conveyance Allowance", breakdown["conveyance_allowance"]),
        ("HRA", breakdown["hra"]),
        ("LTA", breakdown["lta"]),
        ("Other Allowances", breakdown["other_allowances"]),
    ]
