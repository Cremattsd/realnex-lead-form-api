from flask import Flask, request, render_template, redirect, url_for, flash, session
import requests
import os
import re
from dotenv import load_dotenv
from functools import wraps

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

# Default settings from environment
DEFAULT_API_TOKEN = os.getenv("REALNEX_API_TOKEN", "")
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "")

# Sanitize helpers
def sanitize_input(input_string):
    if not input_string:
        return ""
    return re.sub(r'[<>"\'&;()]', '', input_string).strip()

def validate_phone(phone):
    digits = re.sub(r'\D', '', phone)
    return digits if 7 <= len(digits) <= 15 else None

def validate_email(email):
    return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email))

def admin_token_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not DEFAULT_API_TOKEN:
            flash("Admin API token not configured.", "error")
        return f(*args, **kwargs)
    return wrapper

@app.route("/", methods=["GET"])
@admin_token_required
def home():
    return render_template("index.html")

@app.route("/form", methods=["GET", "POST"])
def lead_form():
    token = request.args.get("token") or DEFAULT_API_TOKEN
    admin_token = bool(DEFAULT_API_TOKEN)

    form_data = {
        "token": token,
        "first_name": "",
        "last_name": "",
        "email": "",
        "phone": "",
        "company": "",
        "address": "",
        "comments": "",
        "admin_token": admin_token
    }

    if request.method == "POST":
        token = sanitize_input(request.form.get("token")) or request.args.get("token") or DEFAULT_API_TOKEN
        first_name = sanitize_input(request.form.get("first_name"))
        last_name = sanitize_input(request.form.get("last_name"))
        email = sanitize_input(request.form.get("email"))
        phone = validate_phone(sanitize_input(request.form.get("phone")))
        company = sanitize_input(request.form.get("company"))
        address = sanitize_input(request.form.get("address"))
        comments = sanitize_input(request.form.get("comments"))
        recaptcha_response = request.form.get("g-recaptcha-response")

        # Update form for sticky fields
        form_data.update({
            "token": token,
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
            errors.append("First Name is required.")
        if not last_name:
            errors.append("Last Name is required.")
        if not email or not validate_email(email):
            errors.append("Valid Email is required.")
        if request.form.get("phone") and phone is None:
            errors.append("Phone number is invalid.")
        if not recaptcha_response:
            errors.append("Please complete the reCAPTCHA.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

        # Verify reCAPTCHA
        recaptcha_check = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": RECAPTCHA_SECRET_KEY, "response": recaptcha_response}
        )
        try:
            recaptcha_result = recaptcha_check.json()
            if not recaptcha_result.get("success"):
                flash("reCAPTCHA verification failed.", "error")
                return render_template("form.html", messages=session.get('_flashes', []), **form_data)
        except Exception:
            flash("Error verifying reCAPTCHA.", "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            # Check if contact already exists
            search = requests.get(
                f"https://sync.realnex.com/api/v1/Crm/contacts?email={email}",
                headers=headers, timeout=10
            )
            contact_data = search.json()
            existing = next((c for c in contact_data.get("items", [])
                            if c["firstName"].lower() == first_name.lower() and c["lastName"].lower() == last_name.lower()), None)

            if existing:
                contact_key = existing["key"]
            else:
                payload = {
                    "firstName": first_name,
                    "lastName": last_name,
                    "email": email,
                    "phones": [{"number": phone}] if phone else []
                }
                response = requests.post(
                    "https://sync.realnex.com/api/v1/Crm/contact",
                    headers=headers, json=payload, timeout=10
                )
                contact = response.json()
                contact_key = contact.get("contact", {}).get("key")

            company_key = None
            if company:
                search_company = requests.get(
                    f"https://sync.realnex.com/api/v1/Crm/companies?name={company}",
                    headers=headers, timeout=10
                )
                company_results = search_company.json().get("items", [])
                if company_results:
                    company_key = company_results[0]["key"]
                else:
                    new_company = requests.post(
                        "https://sync.realnex.com/api/v1/Crm/company",
                        headers=headers,
                        json={"name": company, "address1": address},
                        timeout=10
                    )
                    created = new_company.json()
                    company_key = created.get("company", {}).get("key")

            # Create history note
            if contact_key:
                history_payload = {
                    "subject": "Weblead",
                    "notes": comments or "Submitted via web form",
                    "linkedContactKeys": [contact_key],
                    "linkedCompanyKeys": [company_key] if company_key else [],
                    "eventType": "Note"
                }
                requests.post(
                    "https://sync.realnex.com/api/v1/Crm/history",
                    headers=headers, json=history_payload, timeout=10
                )

            session['lead_data'] = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "company": company
            }
            return redirect(url_for("lead_success"))

        except Exception as e:
            flash(f"Error: {str(e)}", "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

    return render_template("form.html", messages=session.get('_flashes', []), **form_data)

@app.route("/success")
def lead_success():
    lead_data = session.pop("lead_data", {})
    if not lead_data:
        flash("No lead submission found", "error")
        return redirect(url_for("home"))
    return render_template("success.html", **lead_data)

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "False").lower() == "true")
