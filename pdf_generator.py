"""Payslip PDF generation - mirrors app/src/main/java/.../pdf/PayslipPdfGenerator.kt

Draws the payslip onto a single A4-ish page (595x842 pt), replicating the
reference layout pixel-for-pixel (Android canvas y grows downward, so each
drawn y is converted to ReportLab's bottom-up coordinate via PAGE_HEIGHT - y).
"""
import re

from reportlab.lib.colors import HexColor, black
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from words import amount_to_words, format_amount

PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN = 40.0
USABLE_WIDTH = PAGE_WIDTH - 2 * MARGIN

COL_WIDTHS = [140.0, 72.0, 72.0, 95.0, 68.0, 68.0]

FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"


def _font(bold=False, size=9.0):
    return (FONT_BOLD if bold else FONT_REGULAR), size


def _draw_text(c, x, y_top, text, size, bold=False, align="left"):
    font, sz = _font(bold, size)
    c.setFont(font, sz)
    y = PAGE_HEIGHT - y_top
    if align == "center":
        c.drawCentredString(x, y, text)
    elif align == "right":
        c.drawRightString(x, y, text)
    else:
        c.drawString(x, y, text)


def _fit_text(text, font, size, max_width):
    if not text:
        return ""
    if stringWidth(text, font, size) <= max_width:
        return text
    truncated = text
    while truncated and stringWidth(truncated + "…", font, size) > max_width:
        truncated = truncated[:-1]
    return f"{truncated}…"


def _draw_fitted_text(c, x, y_top, text, size, bold, max_width):
    font, sz = _font(bold, size)
    fitted = _fit_text(text, font, sz, max_width)
    if not fitted:
        return
    c.setFont(font, sz)
    c.drawString(x, PAGE_HEIGHT - y_top, fitted)


def _wrap_text(text, font, size, max_width):
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if stringWidth(candidate, font, size) > max_width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _build_payslip_rows(breakdown):
    net = format_amount(breakdown["total_earnings"])
    return [
        {"el": "Earnings", "ea": "Amount", "eg": "Gross Salary", "dl": "Deductions",
         "da": "Amount", "dg": "Gross Salary", "bold": False, "header": True},
        {"el": "Basic Pay", "ea": format_amount(breakdown["basic_pay"]), "eg": format_amount(breakdown["basic_pay"]),
         "dl": "", "da": "", "dg": "", "bold": False, "header": False},
        {"el": "Conveyance Allowance", "ea": format_amount(breakdown["conveyance_allowance"]),
         "eg": format_amount(breakdown["conveyance_allowance"]), "dl": "", "da": "", "dg": "",
         "bold": False, "header": False},
        {"el": "HRA", "ea": format_amount(breakdown["hra"]), "eg": format_amount(breakdown["hra"]),
         "dl": "", "da": "", "dg": "", "bold": False, "header": False},
        {"el": "LTA", "ea": format_amount(breakdown["lta"]), "eg": format_amount(breakdown["lta"]),
         "dl": "", "da": "", "dg": "", "bold": False, "header": False},
        {"el": "Other Allowances", "ea": format_amount(breakdown["other_allowances"]),
         "eg": format_amount(breakdown["other_allowances"]), "dl": "", "da": "", "dg": "",
         "bold": False, "header": False},
        {"el": "Total Earnings", "ea": format_amount(breakdown["total_earnings"]),
         "eg": format_amount(breakdown["total_earnings"]), "dl": "Total Deductions", "da": "0.00",
         "dg": "0.00", "bold": True, "header": False},
        {"el": "", "ea": "", "eg": "", "dl": "Net Amount", "da": f"Rs. {net}", "dg": f"Rs. {net}",
         "bold": True, "header": False},
    ]


def _build_detail_columns(form, employee_bank_details):
    left = [
        ("Employee Number", form.get("employee_no", "")),
        ("Function", form.get("function", "")),
        ("Designation", form.get("designation", "")),
        ("Location", form.get("location", "")),
        ("Bank Details", employee_bank_details or form.get("bank_details", "")),
        ("Date of joining", form.get("date_of_joining", "")),
    ]
    right = [
        ("Tax Regime", form.get("tax_regime", "")),
        ("Income Tax Number (PAN)", form.get("pan", "")),
        ("Universal Account Number (UAN)", form.get("uan", "")),
        ("PF account number", form.get("pf_account_number", "")),
        ("ESI Number", form.get("esi_number", "")),
        ("PR Account Number (PRAN)", form.get("pran", "")),
    ]
    return left, right


def _draw_detail_grid(c, start_y, form, employee_bank_details):
    left, right = _build_detail_columns(form, employee_bank_details)
    row_height = 15.5
    left_label_x = MARGIN
    left_value_x = MARGIN + 108
    left_value_max_width = 148
    right_label_x = MARGIN + 268
    right_value_x = MARGIN + 415
    right_value_max_width = PAGE_WIDTH - MARGIN - right_value_x

    y = start_y
    for (llabel, lvalue), (rlabel, rvalue) in zip(left, right):
        _draw_text(c, left_label_x, y, f"{llabel} :", 8.6, bold=True)
        _draw_fitted_text(c, left_value_x, y, lvalue or "-", 8.6, False, left_value_max_width)
        _draw_text(c, right_label_x, y, f"{rlabel} :", 8.6, bold=True)
        _draw_fitted_text(c, right_value_x, y, rvalue or "-", 8.6, False, right_value_max_width)
        y += row_height
    return y


def _draw_earnings_table(c, start_y, breakdown):
    rows = _build_payslip_rows(breakdown)
    row_height = 20.0
    table_width = sum(COL_WIDTHS)
    table_height = row_height * len(rows)

    top_y_pdf = PAGE_HEIGHT - start_y
    bottom_y_pdf = PAGE_HEIGHT - (start_y + table_height)

    c.setFillColor(HexColor("#E8ECF3"))
    c.rect(MARGIN, top_y_pdf - row_height, table_width, row_height, stroke=0, fill=1)
    c.setFillColor(black)

    c.setStrokeColor(black)
    c.setLineWidth(0.75)
    c.rect(MARGIN, bottom_y_pdf, table_width, table_height, stroke=1, fill=0)
    for r in range(1, len(rows)):
        ry = PAGE_HEIGHT - (start_y + r * row_height)
        c.line(MARGIN, ry, MARGIN + table_width, ry)
    cx = MARGIN
    for w in COL_WIDTHS:
        c.line(cx, top_y_pdf, cx, bottom_y_pdf)
        cx += w
    c.line(cx, top_y_pdf, cx, bottom_y_pdf)

    for index, row in enumerate(rows):
        row_top = start_y + index * row_height
        baseline = row_top + row_height * 0.68
        bold = row["bold"] or row["header"]
        size = 9.0

        col_x = MARGIN
        _draw_fitted_text(c, col_x + 5, baseline, row["el"], size, bold, COL_WIDTHS[0] - 8)
        col_x += COL_WIDTHS[0]
        _draw_text(c, col_x + COL_WIDTHS[1] - 5, baseline, row["ea"], size, bold=bold, align="right")
        col_x += COL_WIDTHS[1]
        _draw_text(c, col_x + COL_WIDTHS[2] - 5, baseline, row["eg"], size, bold=bold, align="right")
        col_x += COL_WIDTHS[2]
        _draw_fitted_text(c, col_x + 5, baseline, row["dl"], size, bold, COL_WIDTHS[3] - 8)
        col_x += COL_WIDTHS[3]
        _draw_text(c, col_x + COL_WIDTHS[4] - 5, baseline, row["da"], size, bold=bold, align="right")
        col_x += COL_WIDTHS[4]
        _draw_text(c, col_x + COL_WIDTHS[5] - 5, baseline, row["dg"], size, bold=bold, align="right")

    return start_y + table_height


def _draw_footer(c, start_y, breakdown, company, signature_path):
    right_x = MARGIN + sum(COL_WIDTHS)

    _draw_text(c, MARGIN, start_y, "Amount (in words):", 8.6, bold=True)
    _draw_text(c, right_x, start_y, f"for {company['name']}", 9.5, bold=True, align="right")

    words = amount_to_words(breakdown["total_earnings"])
    wrapped = _wrap_text(words, FONT_REGULAR, 9.0, USABLE_WIDTH * 0.62)
    y = start_y + 14
    for line in wrapped:
        _draw_text(c, MARGIN, y, line, 9.0)
        y += 12

    if signature_path and signature_path.exists():
        from reportlab.lib.utils import ImageReader

        width, height = ImageReader(str(signature_path)).getSize()
        max_width, max_height = 120.0, 38.0
        scale = min(max_width / width, max_height / height)
        draw_width = width * scale
        draw_height = height * scale
        img_y_top = start_y + 6 + draw_height
        c.drawImage(
            str(signature_path),
            right_x - draw_width,
            PAGE_HEIGHT - img_y_top,
            width=draw_width,
            height=draw_height,
            mask="auto",
        )

    _draw_text(c, right_x, start_y + 55, "Authorised Signatory", 9.0, align="right")


def _safe_filename(name):
    safe = re.sub(r"[^A-Za-z0-9 _-]", "", name or "Employee")
    return safe.replace(" ", "_") or "Employee"


def generate_pdf(output_path, form, breakdown, company, signature_path=None):
    """form: dict of slip fields (month, year, employee_name, employee_no, function,
    designation, location, bank_details, date_of_joining, tax_regime, pan, uan,
    pf_account_number, esi_number, pran). breakdown: dict from calculator.calculate().
    company: dict with name, address_lines, pan, cin."""
    c = canvas.Canvas(str(output_path), pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    center_x = PAGE_WIDTH / 2.0
    y = 55.0

    _draw_text(c, center_x, y, company["name"], 15, bold=True, align="center")
    y += 16
    for line in company["address_lines"]:
        _draw_text(c, center_x, y, line, 9.5, align="center")
        y += 13
    _draw_text(c, center_x, y, f"PAN - {company['pan']}", 9.5, align="center")
    y += 13
    _draw_text(c, center_x, y, f"CIN: {company['cin']}", 9.5, align="center")

    y += 30
    _draw_text(c, center_x, y, "Pay Slip", 14, bold=True, align="center")
    y += 16
    _draw_text(c, center_x, y, f"for {form.get('month', '')}-{form.get('year', '')}", 10.5, align="center")

    y += 26
    display_name = form.get("employee_name") or "—"
    _draw_text(c, center_x, y, display_name, 12.5, bold=True, align="center")

    y += 24
    y = _draw_detail_grid(c, y, form, form.get("_employee_bank_details"))

    y += 18
    y = _draw_earnings_table(c, y, breakdown)

    y += 22
    _draw_footer(c, y, breakdown, company, signature_path)

    c.showPage()
    c.save()
    return output_path


def payslip_filename(form):
    safe_name = _safe_filename(form.get("employee_name"))
    return f"Payslip_{form.get('month', '')}_{form.get('year', '')}_{safe_name}.pdf"
