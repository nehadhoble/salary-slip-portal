# Salary Slip Web Portal

Web counterpart to the Android app: same employee records, earnings-split
formula, signature, and payslip PDF layout, served as a Flask app so anyone
on the team can generate a slip from a browser.

## Setup

```bash
cd web_portal
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

## Run

```bash
PORTAL_PASSWORD=choose-a-real-password ./.venv/bin/python app.py
```

Open http://127.0.0.1:5050 and sign in with the password you set.

- `PORTAL_PASSWORD` - shared login password (default `credithive` if unset - change this before any real use).
- `PORTAL_SECRET_KEY` - Flask session signing key (set a random value before deploying anywhere shared).

Data is stored in `web_portal/data/` (`salaryslip.db` for employees and
formula settings, `signature.png` for the authorised-signatory signature).
Back that folder up the way you would the Android app's local database.

## What's implemented

- Employee records (add/edit/delete), reused to autofill new slips
- Editable earnings-split formula (Basic/HRA/LTA/Other %, same validation as the app)
- Signature pad (draw once, reused on every payslip) with basic image validation
- Slip form -> live HTML preview -> PDF download, matching the Android app's
  payslip layout pixel-for-pixel logic (calculator, amount-in-words, table layout)
- Simple shared-password login gate (the data here includes PAN, bank details,
  and a signature image, so don't run this without a password on a shared network)

## Not yet carried over from the app

- Per-device draft autosave (the app remembers your last unsaved form; the
  portal does not yet)
- A generated-slip history (the app doesn't persist these either, it only
  ever produces the PDF on demand - same behaviour here)

## Deploying beyond your own machine

This ships with Flask's development server (`app.run(debug=True)`), which is
fine for local/LAN use but not for the public internet. Before exposing it
beyond localhost:
- Run behind a production WSGI server (gunicorn/waitress) instead of `python app.py`
- Set `PORTAL_PASSWORD` and `PORTAL_SECRET_KEY` to real secrets (env vars, not hardcoded)
- Put it behind HTTPS
- Consider per-user accounts instead of one shared password if more than a
  couple of people need access
