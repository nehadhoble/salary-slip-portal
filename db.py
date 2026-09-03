import sqlite3
from pathlib import Path

from calculator import DEFAULT_SETTINGS

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "salaryslip.db"
SIGNATURE_PATH = DATA_DIR / "signature.png"

SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    employee_no TEXT NOT NULL DEFAULT '',
    designation TEXT NOT NULL DEFAULT '',
    date_of_joining TEXT NOT NULL DEFAULT '',
    pan TEXT NOT NULL DEFAULT '',
    account_no TEXT NOT NULL DEFAULT '',
    ifsc_code TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS formula_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    basic_pct REAL NOT NULL,
    hra_pct REAL NOT NULL,
    lta_pct REAL NOT NULL,
    other_pct REAL NOT NULL
);
"""


def get_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    try:
        conn.executescript(SCHEMA)
        existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(employees)")}
        if "employee_no" not in existing_columns:
            conn.execute("ALTER TABLE employees ADD COLUMN employee_no TEXT NOT NULL DEFAULT ''")
        row = conn.execute("SELECT 1 FROM formula_settings WHERE id = 1").fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO formula_settings (id, basic_pct, hra_pct, lta_pct, other_pct) "
                "VALUES (1, ?, ?, ?, ?)",
                (
                    DEFAULT_SETTINGS["basic_pct"],
                    DEFAULT_SETTINGS["hra_pct"],
                    DEFAULT_SETTINGS["lta_pct"],
                    DEFAULT_SETTINGS["other_pct"],
                ),
            )
        conn.commit()
    finally:
        conn.close()


# ---- Employees ----

def list_employees():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM employees ORDER BY name COLLATE NOCASE").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_employee(employee_id):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def save_employee(employee_id, name, employee_no, designation, date_of_joining, pan, account_no, ifsc_code):
    conn = get_db()
    try:
        if employee_id:
            conn.execute(
                """UPDATE employees SET name=?, employee_no=?, designation=?, date_of_joining=?, pan=?,
                   account_no=?, ifsc_code=? WHERE id=?""",
                (name, employee_no, designation, date_of_joining, pan, account_no, ifsc_code, employee_id),
            )
        else:
            conn.execute(
                """INSERT INTO employees (name, employee_no, designation, date_of_joining, pan, account_no, ifsc_code)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (name, employee_no, designation, date_of_joining, pan, account_no, ifsc_code),
            )
        conn.commit()
    finally:
        conn.close()


def delete_employee(employee_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
        conn.commit()
    finally:
        conn.close()


def bank_details_summary(employee):
    parts = []
    if employee.get("account_no"):
        parts.append(f"A/c No. {employee['account_no']}")
    if employee.get("ifsc_code"):
        parts.append(f"IFSC {employee['ifsc_code']}")
    return ", ".join(parts)


# ---- Formula settings ----

def load_settings():
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM formula_settings WHERE id = 1").fetchone()
        if row is None:
            return dict(DEFAULT_SETTINGS)
        return {
            "basic_pct": row["basic_pct"],
            "hra_pct": row["hra_pct"],
            "lta_pct": row["lta_pct"],
            "other_pct": row["other_pct"],
        }
    finally:
        conn.close()


def save_settings(settings):
    conn = get_db()
    try:
        conn.execute(
            "UPDATE formula_settings SET basic_pct=?, hra_pct=?, lta_pct=?, other_pct=? WHERE id=1",
            (settings["basic_pct"], settings["hra_pct"], settings["lta_pct"], settings["other_pct"]),
        )
        conn.commit()
    finally:
        conn.close()
