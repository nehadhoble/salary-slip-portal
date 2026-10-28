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


def _round_whole(value):
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


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


def calculate(total_earnings, settings=None, tds=0.0, leave=0.0, plb=0.0):
    """Returns a dict breakdown (all amounts in whole rupees): basic_pay,
    conveyance_allowance, hra, lta, other_allowances, plb, total_earnings, tds,
    leave, deduction, net_amount.

    total_earnings passed in is the fixed amount the percentage split is built
    from. plb is entered manually and sits outside that split; it is added on
    top, so the returned total_earnings is the split amount plus plb. tds and
    leave sum to deduction, subtracted to get net_amount (floored at zero)."""
    settings = settings or DEFAULT_SETTINGS
    base = _round_whole(max(0.0, total_earnings or 0.0))
    plb = _round_whole(max(0.0, plb or 0.0))
    tds = _round_whole(max(0.0, tds or 0.0))
    leave = _round_whole(max(0.0, leave or 0.0))
    deduction = tds + leave
    if base <= 0:
        basic = hra = lta = other = conveyance = 0
    else:
        basic = _round_whole(base * settings["basic_pct"] / 100.0)
        hra = _round_whole(basic * settings["hra_pct"] / 100.0)
        lta = _round_whole(basic * settings["lta_pct"] / 100.0)
        other = _round_whole(basic * settings["other_pct"] / 100.0)
        conveyance = base - (basic + hra + lta + other)
    gross = base + plb
    return {
        "basic_pay": basic,
        "conveyance_allowance": conveyance,
        "hra": hra,
        "lta": lta,
        "other_allowances": other,
        "plb": plb,
        "total_earnings": gross,
        "tds": tds,
        "leave": leave,
        "deduction": deduction,
        "net_amount": max(0, gross - deduction),
    }


def breakdown_rows(breakdown):
    """List[(label, amount)] matching EarningsBreakdown.rows in the Kotlin app."""
    return [
        ("Basic Pay", breakdown["basic_pay"]),
        ("Conveyance Allowance", breakdown["conveyance_allowance"]),
        ("HRA", breakdown["hra"]),
        ("LTA", breakdown["lta"]),
        ("Other Allowances", breakdown["other_allowances"]),
        ("PLB", breakdown["plb"]),
    ]
