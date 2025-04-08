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

# Helper Functions
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
    token = request.args.get("token") or sanitize_input(request.form.get("token"))
    admin_token = bool(not not token)
    
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
        phone = validate_phone(sanitize_input(request.form.get("phone")))
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
            errors.append("API Token is required")
        if not first_name:
            errors.append("First Name is required")
        if not last_name:
            errors.append("Last Name is required")
        if not email or not validate_email(email):
            errors.append("Please enter a valid email address")
        if phone is None and request.form.get("phone"):
            errors.append("Please enter a valid phone number")
        if not recaptcha_response:
            errors.append("Please complete the reCAPTCHA")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

        # Verify reCAPTCHA
        recaptcha_verify = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": RECAPTCHA_SECRET_KEY, "response": recaptcha_response}
        )
        recaptcha_result = recaptcha_verify.json()
        if not recaptcha_result.get("success"):
            flash("reCAPTCHA failed. Please try again.", "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            # Create or find contact
            search_resp = requests.get(f"https://sync.realnex.com/api/v1/Crm/contacts?email={email}", headers=headers)
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
                contact_resp = requests.post("https://sync.realnex.com/api/v1/Crm/contact", headers=headers, json=contact_payload)
                contact = contact_resp.json()
                contact_key = contact.get("contact", {}).get("key")

            # Create company if provided
            company_key = None
            if company:
                company_payload = {
                    "name": company,
                    "address_info": {
                        "address_1": address,
                        "company": company
                    }
                }
                company_resp = requests.post("https://sync.realnex.com/api/v1/Crm/company", headers=headers, json=company_payload)
                comp_data = company_resp.json()
                company_key = comp_data.get("company", {}).get("key")

            # Create history for contact
            history_payload = {
                "subject": "Weblead",
                "notes": comments or "Submitted via web form.",
                "eventTypeKey": 1,
                "published": True,
                "timeless": True
            }
            history_url = f"https://sync.realnex.com/api/v1/Crm/object/{contact_key}/history"
            history_resp = requests.post(history_url, headers=headers, json=history_payload)

            if history_resp.status_code >= 400:
                print("Error posting history:", history_resp.status_code, history_resp.text)

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

@app.route("/event-types")
def get_event_types():
    token = request.args.get("token")
    if not token:
        return {"error": "Missing token"}, 400

    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get("https://sync.realnex.com/api/v1/Crm/settings/eventtypes", headers=headers)
        return resp.json(), resp.status_code
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "False").lower() == "true")
