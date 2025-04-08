from flask import Flask, request, render_template, redirect, url_for, flash, session
import requests
import os
import re
from dotenv import load_dotenv
from functools import wraps

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your-dev-secret")

RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "")

# Helpers
def sanitize_input(val):
    return re.sub(r'[<>"\'&]', '', val.strip()) if val else ""

def validate_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

def validate_phone(phone):
    digits = re.sub(r'\D', '', phone)
    return digits if 7 <= len(digits) <= 15 else None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/form", methods=["GET", "POST"])
def form():
    token = request.args.get("token") or request.form.get("token")
    if not token:
        flash("Missing RealNex API Token in URL or form.", "error")

    form_data = {
        "first_name": "",
        "last_name": "",
        "email": "",
        "phone": "",
        "company": "",
        "address": "",
        "comments": "",
        "token": token,
        "admin_token": False
    }

    if request.method == "POST":
        first_name = sanitize_input(request.form.get("first_name"))
        last_name = sanitize_input(request.form.get("last_name"))
        email = sanitize_input(request.form.get("email"))
        phone = validate_phone(request.form.get("phone"))
        company = sanitize_input(request.form.get("company"))
        address = sanitize_input(request.form.get("address"))
        comments = sanitize_input(request.form.get("comments"))
        recaptcha_response = request.form.get("g-recaptcha-response")

        form_data.update({
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": request.form.get("phone"),
            "company": company,
            "address": address,
            "comments": comments
        })

        errors = []
        if not token:
            errors.append("API Token is required.")
        if not first_name:
            errors.append("First name is required.")
        if not last_name:
            errors.append("Last name is required.")
        if not email or not validate_email(email):
            errors.append("A valid email is required.")
        if not recaptcha_response:
            errors.append("Please complete the reCAPTCHA.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

        # Validate reCAPTCHA
        verify_resp = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": RECAPTCHA_SECRET_KEY, "response": recaptcha_response}
        )
        if not verify_resp.json().get("success"):
            flash("reCAPTCHA validation failed.", "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            # Check for existing contact
            contact_key = None
            search = requests.get(f"https://sync.realnex.com/api/v1/Crm/contacts?email={email}", headers=headers)
            if search.ok and search.json().get("items"):
                for contact in search.json()["items"]:
                    if contact["firstName"].lower() == first_name.lower() and contact["lastName"].lower() == last_name.lower():
                        contact_key = contact["key"]
                        break

            # Create contact if not found
            if not contact_key:
                contact_payload = {
                    "firstName": first_name,
                    "lastName": last_name,
                    "email": email,
                    "phones": [{"number": phone}] if phone else []
                }
                res = requests.post("https://sync.realnex.com/api/v1/Crm/contact", headers=headers, json=contact_payload)
                contact_key = res.json().get("contact", {}).get("key")

            # Create company
            company_key = None
            if company:
                comp_payload = {
                    "name": company,
                    "address_info": {
                        "company": company,
                        "address_1": address
                    }
                }
                comp_res = requests.post("https://sync.realnex.com/api/v1/Crm/company", headers=headers, json=comp_payload)
                company_key = comp_res.json().get("company", {}).get("key")

            # Create history
            if contact_key:
                history_payload = {
                    "subject": "Weblead",
                    "notes": comments or "Submitted via form",
                    "linkedContactKeys": [contact_key],
                    "linkedCompanyKeys": [company_key] if company_key else [],
                    "eventTypeKey": 1  # Use a valid integer event type (like '1' for Note)
                }
                hist = requests.post("https://sync.realnex.com/api/v1/Crm/history", headers=headers, json=history_payload)
                if not hist.ok:
                    flash(f"Error posting history: {hist.status_code} {hist.text}", "error")

            session["lead_data"] = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "company": company
            }
            return redirect(url_for("success"))

        except Exception as e:
            flash(f"Error submitting to RealNex: {str(e)}", "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

    return render_template("form.html", messages=session.get('_flashes', []), **form_data)

@app.route("/success")
def success():
    lead_data = session.pop("lead_data", {})
    if not lead_data:
        flash("No submission found.", "error")
        return redirect(url_for("form"))

    return render_template("success.html", **lead_data)

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "False").lower() == "true")
