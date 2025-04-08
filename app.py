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

# Get reCAPTCHA secret from environment (no default)
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY")

# Helper functions
def sanitize_input(input_string):
    if not input_string:
        return ""
    return re.sub(r'[<>"\'&;()]', '', input_string).strip()

def validate_phone(phone):
    digits_only = re.sub(r'\D', '', phone)
    return digits_only if 7 <= len(digits_only) <= 15 else None

def validate_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email))

def get_token_from_request():
    return request.args.get("token") or request.form.get("token")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/form", methods=["GET", "POST"])
def lead_form():
    token = get_token_from_request()
    form_data = {
        "token": token or "",
        "first_name": "",
        "last_name": "",
        "email": "",
        "phone": "",
        "company": "",
        "address": "",
        "comments": "",
        "admin_token": False
    }

    if request.method == "POST":
        token = sanitize_input(token)
        first_name = sanitize_input(request.form.get("first_name"))
        last_name = sanitize_input(request.form.get("last_name"))
        email = sanitize_input(request.form.get("email"))
        phone = validate_phone(sanitize_input(request.form.get("phone")))
        company = sanitize_input(request.form.get("company"))
        address = sanitize_input(request.form.get("address"))
        comments = sanitize_input(request.form.get("comments"))
        recaptcha_response = request.form.get("g-recaptcha-response")

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
            errors.append("Please enter a valid email address.")
        if phone is None and request.form.get("phone"):
            errors.append("Please enter a valid phone number.")
        if not recaptcha_response:
            errors.append("Please complete the reCAPTCHA.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

        # Verify reCAPTCHA
        recaptcha_verify = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": RECAPTCHA_SECRET_KEY, "response": recaptcha_response}
        )
        try:
            recaptcha_result = recaptcha_verify.json()
        except Exception:
            flash("reCAPTCHA verification failed.", "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

        if not recaptcha_result.get("success"):
            flash("reCAPTCHA verification failed.", "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            search_resp = requests.get(
                f"https://sync.realnex.com/api/v1/Crm/contacts?email={email}",
                headers=headers, timeout=10
            )
            existing_contact = None
            if search_resp.ok:
                contact_data = search_resp.json()
                existing_contact = next((c for c in contact_data.get("items", [])
                                        if c["firstName"].lower() == first_name.lower() and c["lastName"].lower() == last_name.lower()), None)

            if existing_contact:
                contact_key = existing_contact["key"]
            else:
                contact_payload = {
                    "firstName": first_name,
                    "lastName": last_name,
                    "email": email,
                    "phones": [{"number": phone}] if phone else []
                }
                contact_resp = requests.post(
                    "https://sync.realnex.com/api/v1/Crm/contact",
                    headers=headers, json=contact_payload, timeout=10
                )
                if not contact_resp.ok:
                    flash(f"Error creating contact: {contact_resp.status_code} - {contact_resp.text}", "error")
                    return render_template("form.html", messages=session.get('_flashes', []), **form_data)
                contact = contact_resp.json()
                contact_key = contact.get("contact", {}).get("key")

            company_key = None
            if company:
                company_search = requests.get(
                    f"https://sync.realnex.com/api/v1/Crm/companies?name={company}",
                    headers=headers, timeout=10
                )
                if company_search.ok:
                    companies = company_search.json().get("items", [])
                    if companies:
                        company_key = companies[0]["key"]
                if not company_key:
                    comp_resp = requests.post(
                        "https://sync.realnex.com/api/v1/Crm/company",
                        headers=headers,
                        json={"name": company, "address1": address},
                        timeout=10
                    )
                    if comp_resp.ok:
                        comp_data = comp_resp.json()
                        company_key = comp_data.get("company", {}).get("key")

            history_payload = {
                "subject": "Weblead",
                "notes": comments or "Submitted via web form.",
                "linkedContactKeys": [contact_key],
                "linkedCompanyKeys": [company_key] if company_key else [],
                "eventTypeName": "Note"
            }
            history_resp = requests.post(
                "https://sync.realnex.com/api/v1/Crm/history",
                headers=headers, json=history_payload, timeout=10
            )
            if not history_resp.ok:
                flash(f"Error posting history: {history_resp.status_code} - {history_resp.text}", "error")

            session['lead_data'] = {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'company': company
            }
            return redirect(url_for('lead_success'))

        except Exception as e:
            flash(f"Error submitting to RealNex: {str(e)}", "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

    return render_template("form.html", messages=session.get('_flashes', []), **form_data)

@app.route("/success")
def lead_success():
    lead_data = session.pop('lead_data', {})
    if not lead_data:
        flash("No lead submission found", "error")
        return redirect(url_for('lead_form'))
    return render_template("success.html", **lead_data)

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "False").lower() == "true")
