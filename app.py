import os
from functools import wraps
from pathlib import Path

from flask import (
    Flask, render_template, request, redirect, url_for, session, flash,
    send_file, jsonify, abort,
)

import db
from calculator import calculate, breakdown_rows, settings_is_valid
from words import format_amount, amount_to_words
from pdf_generator import generate_pdf, payslip_filename

BASE_DIR = Path(__file__).parent

COMPANIES = {
    "Credithive Technologies": {
        "name": "CREDITHIVE PRIVATE LIMITED",
        "address_lines": ["Floor 6, Almonte IT Park, Kharadi,", "Pune - 411014"],
        "pan": "AANCC8647H",
        "cin": "U62099PN2026PTC255950",
    },
    "Mobihive Technologies": {
        "name": "MOBIHIVE TECHNOLOGIES PRIVATE LIMITED",
        "address_lines": ["House no. 1319, sector 18c,", "Chandigarh, Chandigarh - 160018"],
        "pan": "AAJCM3001F",
        "cin": "04AAJCM3001F2Z3",
    },
}
DEFAULT_COMPANY = "Credithive Technologies"

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
TAX_REGIME_OPTIONS = ["Regular Tax Regime", "New Tax Regime", "Old Tax Regime"]

SLIP_FIELDS = [
    "month", "year", "company", "employee_id", "employee_name", "employee_no",
    "designation", "location", "bank_details", "date_of_joining", "tax_regime",
    "pan", "uan", "pf_account_number", "esi_number", "pran", "total_earnings",
    "deduction",
]

app = Flask(__name__)
app.secret_key = os.environ.get("PORTAL_SECRET_KEY", "dev-secret-change-me")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8MB, generous for a signature photo
PORTAL_PASSWORD = os.environ.get("PORTAL_PASSWORD", "credithive")

db.init_db()


# ---- Auth ----

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("authed"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == PORTAL_PASSWORD:
            session["authed"] = True
            return redirect(request.args.get("next") or url_for("home"))
        flash("Incorrect password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---- Home ----

@app.route("/")
@login_required
def home():
    return render_template("home.html", company=COMPANIES[DEFAULT_COMPANY])


# ---- Employees ----

@app.route("/employees")
@login_required
def employees():
    return render_template("employees.html", employees=db.list_employees())


@app.route("/employees/new", methods=["GET", "POST"])
@login_required
def employee_new():
    if request.method == "POST":
        _save_employee_from_form(None)
        return redirect(url_for("employees"))
    return render_template("employee_form.html", employee=None)


@app.route("/employees/<int:employee_id>/edit", methods=["GET", "POST"])
@login_required
def employee_edit(employee_id):
    employee = db.get_employee(employee_id)
    if not employee:
        abort(404)
    if request.method == "POST":
        _save_employee_from_form(employee_id)
        return redirect(url_for("employees"))
    return render_template("employee_form.html", employee=employee)


@app.route("/employees/<int:employee_id>/delete", methods=["POST"])
@login_required
def employee_delete(employee_id):
    db.delete_employee(employee_id)
    return redirect(url_for("employees"))


def _save_employee_from_form(employee_id):
    db.save_employee(
        employee_id,
        name=request.form.get("name", "").strip(),
        employee_no=request.form.get("employee_no", "").strip(),
        designation=request.form.get("designation", "").strip(),
        date_of_joining=request.form.get("date_of_joining", "").strip(),
        pan=request.form.get("pan", "").strip(),
        account_no=request.form.get("account_no", "").strip(),
        ifsc_code=request.form.get("ifsc_code", "").strip(),
    )


@app.route("/api/employees/<int:employee_id>")
@login_required
def api_employee(employee_id):
    employee = db.get_employee(employee_id)
    if not employee:
        abort(404)
    employee["bank_details_summary"] = db.bank_details_summary(employee)
    return jsonify(employee)


# ---- Settings ----

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        if request.form.get("action") == "reset":
            from calculator import DEFAULT_SETTINGS
            db.save_settings(dict(DEFAULT_SETTINGS))
            flash("Formula settings reset to defaults.", "success")
        else:
            try:
                new_settings = {
                    "basic_pct": float(request.form.get("basic_pct", 0)),
                    "hra_pct": float(request.form.get("hra_pct", 0)),
                    "lta_pct": float(request.form.get("lta_pct", 0)),
                    "other_pct": float(request.form.get("other_pct", 0)),
                }
            except ValueError:
                flash("Percentages must be numbers.", "error")
                return redirect(url_for("settings"))
            if not settings_is_valid(new_settings):
                flash("Those percentages would make Conveyance negative. Not saved.", "error")
                return redirect(url_for("settings"))
            db.save_settings(new_settings)
            flash("Formula settings saved.", "success")
        return redirect(url_for("settings"))

    has_signature = db.SIGNATURE_PATH.exists()
    return render_template("settings.html", settings=db.load_settings(), has_signature=has_signature)


@app.route("/settings/signature", methods=["POST"])
@login_required
def save_signature():
    import base64
    import io

    uploaded = request.files.get("signature_file")
    if uploaded and uploaded.filename:
        raw = uploaded.read()
    else:
        data_url = request.form.get("signature_data")
        if not data_url or "," not in data_url:
            flash("No signature captured.", "error")
            return redirect(url_for("settings"))
        header, encoded = data_url.split(",", 1)
        raw = base64.b64decode(encoded)

    try:
        from PIL import Image
        image = Image.open(io.BytesIO(raw))
        image.load()
    except Exception:
        flash("That signature image could not be read. Please try again.", "error")
        return redirect(url_for("settings"))

    db.DATA_DIR.mkdir(parents=True, exist_ok=True)
    image.convert("RGBA").save(db.SIGNATURE_PATH, format="PNG")
    flash("Signature saved.", "success")
    return redirect(url_for("settings"))


@app.route("/settings/signature/image")
@login_required
def signature_image():
    if not db.SIGNATURE_PATH.exists():
        abort(404)
    return send_file(db.SIGNATURE_PATH, mimetype="image/png")


@app.route("/settings/signature/clear", methods=["POST"])
@login_required
def clear_signature():
    if db.SIGNATURE_PATH.exists():
        db.SIGNATURE_PATH.unlink()
    flash("Signature cleared.", "success")
    return redirect(url_for("settings"))


# ---- Slip form / preview / pdf ----

def _form_data_from_request(source):
    data = {field: source.get(field, "").strip() for field in SLIP_FIELDS}
    if not data["month"]:
        data["month"] = MONTH_NAMES[0]
    if not data["tax_regime"]:
        data["tax_regime"] = TAX_REGIME_OPTIONS[0]
    if data["company"] not in COMPANIES:
        data["company"] = DEFAULT_COMPANY
    return data


def _parse_amount(raw):
    """Total Earnings as typed by a person - tolerate "30,000", "₹30,000" etc.
    instead of crashing on the plain float() the field used to get."""
    if not raw:
        return 0.0
    cleaned = raw.replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


@app.route("/slip")
@login_required
def slip_form():
    employee_id = request.args.get("employee_id", type=int)
    prefill = {field: "" for field in SLIP_FIELDS}
    import datetime
    now = datetime.datetime.now()
    prefill["month"] = MONTH_NAMES[now.month - 1]
    prefill["year"] = str(now.year)
    prefill["location"] = "Pune"
    prefill["tax_regime"] = TAX_REGIME_OPTIONS[0]
    prefill["company"] = DEFAULT_COMPANY

    if employee_id:
        employee = db.get_employee(employee_id)
        if employee:
            prefill["employee_id"] = str(employee["id"])
            prefill["employee_name"] = employee["name"]
            prefill["employee_no"] = employee["employee_no"]
            prefill["designation"] = employee["designation"]
            prefill["date_of_joining"] = employee["date_of_joining"]
            prefill["pan"] = employee["pan"]
            prefill["bank_details"] = db.bank_details_summary(employee)

    year_options = list(range(2024, now.year + 11))
    return render_template(
        "slip_form.html",
        form=prefill,
        employees=db.list_employees(),
        months=MONTH_NAMES,
        years=year_options,
        tax_regimes=TAX_REGIME_OPTIONS,
        companies=list(COMPANIES),
    )


@app.route("/slip/preview", methods=["POST"])
@login_required
def slip_preview():
    form = _form_data_from_request(request.form)
    total_earnings = _parse_amount(form["total_earnings"])
    deduction = _parse_amount(form.get("deduction", ""))
    breakdown = calculate(total_earnings, db.load_settings(), deduction)
    rows = breakdown_rows(breakdown)
    net = format_amount(breakdown["net_amount"])
    words = amount_to_words(breakdown["net_amount"]) if breakdown["net_amount"] > 0 else ""
    has_signature = db.SIGNATURE_PATH.exists()
    return render_template(
        "preview.html",
        form=form,
        company=COMPANIES[form["company"]],
        breakdown=breakdown,
        rows=rows,
        net=net,
        words=words,
        format_amount=format_amount,
        has_signature=has_signature,
        slip_fields=SLIP_FIELDS,
    )


@app.route("/slip/pdf", methods=["POST"])
@login_required
def slip_pdf():
    form = _form_data_from_request(request.form)
    total_earnings = _parse_amount(form["total_earnings"])
    deduction = _parse_amount(form.get("deduction", ""))
    breakdown = calculate(total_earnings, db.load_settings(), deduction)

    pdf_form = dict(form)
    if form.get("employee_id"):
        employee = db.get_employee(int(form["employee_id"]))
        if employee:
            pdf_form["_employee_bank_details"] = db.bank_details_summary(employee)

    import io
    filename = payslip_filename(pdf_form)
    signature_path = db.SIGNATURE_PATH if db.SIGNATURE_PATH.exists() else None
    buffer = io.BytesIO()
    generate_pdf(buffer, pdf_form, breakdown, COMPANIES[form["company"]], signature_path)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype="application/pdf")


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5050)
