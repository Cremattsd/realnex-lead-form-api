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

RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "")

# Helpers
def sanitize_input(value):
    return re.sub(r'[<>"\'&;()]', '', value.strip()) if value else ''

def validate_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

def validate_phone(phone):
    digits = re.sub(r'\D', '', phone)
    return digits if 7 <= len(digits) <= 15 else None

def fetch_event_type_key(token, name="Note"):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get("https://sync.realnex.com/api/v1/Crm/eventtypes", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("items", []):
                if item.get("name", "").lower() == name.lower():
                    return item["key"]
    except Exception as e:
        print("Error fetching event type key:", e)
    return None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/form", methods=["GET", "POST"])
def lead_form():
    token = request.args.get("token", "") or sanitize_input(request.form.get("token", ""))
    admin_token = not not token  # bool conversion

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
        if not first_name or not last_name:
            errors.append("Name is required.")
        if not validate_email(email):
            errors.append("A valid email is required.")
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
        if not recaptcha_verify.json().get("success"):
            flash("reCAPTCHA failed. Please try again.", "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        try:
            # Contact Search
            search_resp = requests.get(f"https://sync.realnex.com/api/v1/Crm/contacts?email={email}", headers=headers)
            contact_key = None
            if search_resp.status_code == 200:
                for c in search_resp.json().get("items", []):
                    if c["firstName"].lower() == first_name.lower() and c["lastName"].lower() == last_name.lower():
                        contact_key = c["key"]
                        break

            # Create Contact
            if not contact_key:
                contact_payload = {
                    "firstName": first_name,
                    "lastName": last_name,
                    "email": email,
                    "phones": [{"number": phone}] if phone else [],
                    "address": {
                        "address1": address,
                        "company": company
                    }
                }
                contact_resp = requests.post("https://sync.realnex.com/api/v1/Crm/contact", headers=headers, json=contact_payload)
                contact_key = contact_resp.json().get("contact", {}).get("key")

            # Create Company
            company_key = None
            if company:
                company_resp = requests.get(f"https://sync.realnex.com/api/v1/Crm/companies?name={company}", headers=headers)
                companies = company_resp.json().get("items", [])
                if companies:
                    company_key = companies[0]["key"]
                else:
                    new_company = {
                        "name": company,
                        "address1": address
                    }
                    created = requests.post("https://sync.realnex.com/api/v1/Crm/company", headers=headers, json=new_company)
                    company_key = created.json().get("company", {}).get("key")

            # Create History Note
            if contact_key:
                event_type_key = fetch_event_type_key(token, name="Note")
                history_payload = {
                    "subject": "Weblead",
                    "notes": comments or "Submitted via lead form",
                    "linkedContactKeys": [contact_key],
                    "linkedCompanyKeys": [company_key] if company_key else [],
                    "eventTypeKey": event_type_key or 1
                }
                history_resp = requests.post("https://sync.realnex.com/api/v1/Crm/history", headers=headers, json=history_payload)
                if history_resp.status_code >= 400:
                    print("Error posting history:", history_resp.status_code, history_resp.text)

            session["lead_data"] = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "company": company
            }
            return redirect(url_for("lead_success"))

        except Exception as e:
            flash(f"Error submitting to RealNex: {str(e)}", "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

    return render_template("form.html", messages=session.get('_flashes', []), **form_data)

@app.route("/success")
def lead_success():
    lead_data = session.pop("lead_data", {})
    if not lead_data:
        flash("No lead found.", "error")
        return redirect(url_for("lead_form"))
    return render_template("success.html", **lead_data)

if __name__ == "__main__":
    app.run(debug=True)
