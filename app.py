from flask import Flask, request, render_template, redirect, url_for, flash, session
import requests
import os
import re
from dotenv import load_dotenv
from functools import wraps

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "")

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

@app.route("/form", methods=["GET", "POST"])
def lead_form():
    token = request.args.get("token") or request.form.get("token")
    if not token and request.method == "POST":
        flash("API Token is required.", "error")

    form_data = {
        "token": token or "",
        "first_name": sanitize_input(request.form.get("first_name")),
        "last_name": sanitize_input(request.form.get("last_name")),
        "email": sanitize_input(request.form.get("email")),
        "phone": request.form.get("phone"),
        "company": sanitize_input(request.form.get("company")),
        "address": sanitize_input(request.form.get("address")),
        "comments": sanitize_input(request.form.get("comments")),
    }

    admin_token = False

    if request.method == "POST":
        errors = []

        phone = validate_phone(form_data["phone"])
        if not token:
            errors.append("API Token is required.")
        if not form_data["first_name"]:
            errors.append("First Name is required.")
        if not form_data["last_name"]:
            errors.append("Last Name is required.")
        if not form_data["email"] or not validate_email(form_data["email"]):
            errors.append("Please enter a valid email address.")
        if phone is None and form_data["phone"]:
            errors.append("Please enter a valid phone number.")

        recaptcha_response = request.form.get("g-recaptcha-response")
        if not recaptcha_response:
            errors.append("Please complete the reCAPTCHA.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("form.html", messages=session.get('_flashes', []), admin_token=admin_token, **form_data)

        # Verify reCAPTCHA
        recaptcha_verify = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": RECAPTCHA_SECRET_KEY, "response": recaptcha_response}
        )

        if not recaptcha_verify.json().get("success"):
            flash("reCAPTCHA failed. Please try again.", "error")
            return render_template("form.html", messages=session.get('_flashes', []), admin_token=admin_token, **form_data)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            # Search for existing contact
            search_resp = requests.get(
                f"https://sync.realnex.com/api/v1/Crm/contacts?email={form_data['email']}",
                headers=headers, timeout=10
            )
            existing_contact = None
            if search_resp.status_code == 200:
                try:
                    contact_data = search_resp.json()
                    existing_contact = next((c for c in contact_data.get("items", [])
                        if c["firstName"].lower() == form_data["first_name"].lower() and \
                           c["lastName"].lower() == form_data["last_name"].lower()), None)
                except Exception as e:
                    print("Invalid JSON in contact search:", search_resp.text)

            if existing_contact:
                contact_key = existing_contact["key"]
            else:
                contact_payload = {
                    "firstName": form_data["first_name"],
                    "lastName": form_data["last_name"],
                    "email": form_data["email"],
                    "phones": [{"number": phone}] if phone else []
                }
                contact_resp = requests.post(
                    "https://sync.realnex.com/api/v1/Crm/contact",
                    headers=headers, json=contact_payload, timeout=10
                )
                if contact_resp.status_code == 200:
                    try:
                        contact_body = contact_resp.json()
                        contact_key = contact_body.get("contact", {}).get("key")
                    except Exception as e:
                        print("Invalid JSON in contact creation:", contact_resp.text)
                        flash("Error reading contact response.", "error")
                        return render_template("form.html", messages=session.get('_flashes', []), admin_token=admin_token, **form_data)
                else:
                    flash("Error creating contact in RealNex.", "error")
                    return render_template("form.html", messages=session.get('_flashes', []), admin_token=admin_token, **form_data)

            company_key = None
            if form_data["company"]:
                company_payload = {
                    "name": form_data["company"],
                    "address1": form_data["address"]
                }
                company_resp = requests.post(
                    "https://sync.realnex.com/api/v1/Crm/company",
                    headers=headers, json=company_payload, timeout=10
                )
                if company_resp.status_code == 200:
                    try:
                        company_body = company_resp.json()
                        company_key = company_body.get("company", {}).get("key")
                    except Exception as e:
                        print("Invalid JSON in company creation:", company_resp.text)

            history_payload = {
                "subject": "Weblead",
                "notes": form_data["comments"] or "Submitted via web form.",
                "linkedContactKeys": [contact_key],
                "linkedCompanyKeys": [company_key] if company_key else [],
                "eventType": "Note"
            }
            history_resp = requests.post(
                "https://sync.realnex.com/api/v1/Crm/history",
                headers=headers, json=history_payload, timeout=10
            )
            if history_resp.status_code != 200:
                print("Error posting history:", history_resp.status_code, history_resp.text)

            session['lead_data'] = {
                'first_name': form_data['first_name'],
                'last_name': form_data['last_name'],
                'email': form_data['email'],
                'company': form_data['company']
            }
            return redirect(url_for('lead_success'))

        except Exception as e:
            print("General error submitting to RealNex:", str(e))
            flash(f"Error submitting to RealNex: {str(e)}", "error")

    return render_template("form.html", messages=session.get('_flashes', []), admin_token=admin_token, **form_data)

@app.route("/success")
def lead_success():
    lead_data = session.pop('lead_data', {})
    if not lead_data:
        flash("No lead submission found", "error")
        return redirect(url_for('lead_form'))
    return render_template("success.html", **lead_data)

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "False").lower() == "true")
