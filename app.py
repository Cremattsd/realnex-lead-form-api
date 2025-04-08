from flask import Flask, request, render_template, redirect, url_for, flash, session
import requests
import os
import re
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "")

def sanitize_input(value):
    return re.sub(r'[<>"\'&;()]', '', value).strip() if value else ""

def validate_phone(phone):
    digits = re.sub(r'\D', '', phone or "")
    return digits if 7 <= len(digits) <= 15 else None

def validate_email(email):
    return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email or ""))

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/form", methods=["GET", "POST"])
def lead_form():
    token = request.args.get("token") or sanitize_input(request.form.get("token"))

    form_data = {
        "token": token,
        "first_name": "",
        "last_name": "",
        "email": "",
        "phone": "",
        "company": "",
        "address": "",
        "comments": ""
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
            errors.append("First Name is required.")
        if not last_name:
            errors.append("Last Name is required.")
        if not email or not validate_email(email):
            errors.append("A valid email is required.")
        if request.form.get("phone") and phone is None:
            errors.append("Invalid phone number.")
        if not recaptcha_response:
            errors.append("Please complete the reCAPTCHA.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

        # reCAPTCHA check
        try:
            recaptcha_result = requests.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={"secret": RECAPTCHA_SECRET_KEY, "response": recaptcha_response}
            ).json()

            if not recaptcha_result.get("success"):
                flash("reCAPTCHA verification failed.", "error")
                return render_template("form.html", messages=session.get('_flashes', []), **form_data)
        except Exception:
            flash("Error validating reCAPTCHA.", "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            # Contact check
            search = requests.get(f"https://sync.realnex.com/api/v1/Crm/contacts?email={email}", headers=headers)
            contact_data = search.json()
            match = next((c for c in contact_data.get("items", [])
                         if c["firstName"].lower() == first_name.lower() and c["lastName"].lower() == last_name.lower()), None)

            if match:
                contact_key = match["key"]
            else:
                contact_resp = requests.post("https://sync.realnex.com/api/v1/Crm/contact", headers=headers, json={
                    "firstName": first_name,
                    "lastName": last_name,
                    "email": email,
                    "phones": [{"number": phone}] if phone else []
                })
                contact_key = contact_resp.json().get("contact", {}).get("key")

            # Company check
            company_key = None
            if company:
                companies = requests.get(
                    f"https://sync.realnex.com/api/v1/Crm/companies?name={company}",
                    headers=headers).json().get("items", [])
                if companies:
                    company_key = companies[0]["key"]
                else:
                    company_resp = requests.post("https://sync.realnex.com/api/v1/Crm/company", headers=headers, json={
                        "name": company,
                        "address1": address
                    })
                    company_key = company_resp.json().get("company", {}).get("key")

            # History
            if contact_key:
                requests.post("https://sync.realnex.com/api/v1/Crm/history", headers=headers, json={
                    "subject": "Weblead",
                    "notes": comments or "Submitted via web form",
                    "linkedContactKeys": [contact_key],
                    "linkedCompanyKeys": [company_key] if company_key else [],
                    "eventType": "Note"
                })

            session['lead_data'] = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "company": company
            }
            return redirect(url_for("lead_success"))

        except Exception as e:
            flash(f"Error submitting to RealNex: {e}", "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

    return render_template("form.html", messages=session.get('_flashes', []), **form_data)

@app.route("/success")
def lead_success():
    data = session.pop("lead_data", {})
    if not data:
        flash("No lead was submitted.", "error")
        return redirect(url_for("home"))
    return render_template("success.html", **data)

if __name__ == "__main__":
    app.run(debug=True)
