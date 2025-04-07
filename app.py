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

# Environment config
DEFAULT_API_TOKEN = os.getenv("REALNEX_API_TOKEN", "")
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "")


# === Helper Functions ===

def sanitize_input(value):
    return re.sub(r'[<>"\'&;()]', '', value).strip() if value else ""

def validate_email(email):
    return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email))

def validate_phone(phone):
    digits = re.sub(r'\D', '', phone or "")
    return digits if 7 <= len(digits) <= 15 else None


# === Routes ===

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/form", methods=["GET", "POST"])
def lead_form():
    token = request.args.get("token", DEFAULT_API_TOKEN)
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
        token = sanitize_input(request.form.get("token")) or DEFAULT_API_TOKEN
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
            "comments": comments,
        })

        errors = []
        if not token:
            errors.append("API Token is required.")
        if not first_name:
            errors.append("First name is required.")
        if not last_name:
            errors.append("Last name is required.")
        if not email or not validate_email(email):
            errors.append("Valid email is required.")
        if request.form.get("phone") and phone is None:
            errors.append("Please enter a valid phone number.")
        if not recaptcha_response:
            errors.append("Please complete the reCAPTCHA.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

        # === Verify reCAPTCHA ===
        recaptcha_result = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": RECAPTCHA_SECRET_KEY, "response": recaptcha_response}
        ).json()

        if not recaptcha_result.get("success"):
            flash("reCAPTCHA verification failed.", "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            # Search for existing contact
            contact_key = None
            resp = requests.get(f"https://sync.realnex.com/api/v1/Crm/contacts?email={email}", headers=headers, timeout=10)
            contacts = resp.json().get("items", [])

            for contact in contacts:
                if contact["firstName"].lower() == first_name.lower() and contact["lastName"].lower() == last_name.lower():
                    contact_key = contact["key"]
                    break

            # Create contact if not found
            if not contact_key:
                payload = {
                    "firstName": first_name,
                    "lastName": last_name,
                    "email": email,
                    "phones": [{"number": phone}] if phone else []
                }
                res = requests.post("https://sync.realnex.com/api/v1/Crm/contact", headers=headers, json=payload)
                contact_key = res.json().get("contact", {}).get("key")

            # Search or create company
            company_key = None
            if company:
                comp_search = requests.get(f"https://sync.realnex.com/api/v1/Crm/companies?name={company}", headers=headers, timeout=10)
                items = comp_search.json().get("items", [])
                if items:
                    company_key = items[0]["key"]
                else:
                    comp_create = requests.post("https://sync.realnex.com/api/v1/Crm/company", headers=headers,
                                                json={"name": company, "address1": address})
                    company_key = comp_create.json().get("company", {}).get("key")

            # Create history note
            if contact_key:
                note_payload = {
                    "subject": "Weblead",
                    "notes": comments or "Submitted via web form.",
                    "linkedContactKeys": [contact_key],
                    "linkedCompanyKeys": [company_key] if company_key else [],
                    "eventType": "Note"
                }
                requests.post("https://sync.realnex.com/api/v1/Crm/history", headers=headers, json=note_payload)

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
        return redirect(url_for("lead_form"))
    return render_template("success.html", **lead_data)


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "False").lower() == "true")
