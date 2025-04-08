from flask import Flask, request, render_template, redirect, url_for, flash, session
import requests
import os
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

# reCAPTCHA secret
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY")

# --- Helper Functions ---
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

# --- Routes ---
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/form", methods=["GET", "POST"])
def lead_form():
    token = request.args.get("token") or sanitize_input(request.form.get("token"))

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

        # --- Validation ---
        errors = []
        if not token:
            errors.append("API Token is required.")
        if not first_name:
            errors.append("First name is required.")
        if not last_name:
            errors.append("Last name is required.")
        if not email or not validate_email(email):
            errors.append("Please enter a valid email address.")
        if phone is None and request.form.get("phone"):
            errors.append("Invalid phone number.")
        if not recaptcha_response:
            errors.append("Please complete the reCAPTCHA.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

        # --- reCAPTCHA verification ---
        verify_response = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={
                "secret": RECAPTCHA_SECRET_KEY,
                "response": recaptcha_response
            }
        )
        recaptcha_result = verify_response.json()
        if not recaptcha_result.get("success"):
            flash("reCAPTCHA verification failed.", "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            # Check for existing contact
            contact_resp = requests.get(
                f"https://sync.realnex.com/api/v1/Crm/contacts?email={email}",
                headers=headers, timeout=10
            )
            contact_data = contact_resp.json()
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
                create_resp = requests.post(
                    "https://sync.realnex.com/api/v1/Crm/contact",
                    headers=headers, json=contact_payload, timeout=10
                )
                created = create_resp.json()
                contact_key = created.get("contact", {}).get("key")

            # Check or create company
            company_key = None
            if company:
                company_check = requests.get(
                    f"https://sync.realnex.com/api/v1/Crm/companies?name={company}",
                    headers=headers, timeout=10
                )
                items = company_check.json().get("items", [])
                if items:
                    company_key = items[0]["key"]
                else:
                    company_payload = {
                        "name": company,
                        "address1": address
                    }
                    company_create = requests.post(
                        "https://sync.realnex.com/api/v1/Crm/company",
                        headers=headers, json=company_payload, timeout=10
                    )
                    company_data = company_create.json()
                    company_key = company_data.get("company", {}).get("key")

            # Add history note with corrected eventTypeKey
            history_payload = {
                "subject": "Weblead",
                "notes": comments or "Submitted via web form.",
                "linkedContactKeys": [contact_key],
                "linkedCompanyKeys": [company_key] if company_key else [],
                "eventTypeKey": "Note"  # 👈 This is the correct field
            }

            history_post = requests.post(
                "https://sync.realnex.com/api/v1/Crm/history",
                headers=headers, json=history_payload, timeout=10
            )

            if not history_post.ok:
                flash(f"Error posting history: {history_post.status_code} {history_post.text}", "error")

            # Redirect to success page
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
    return render_template("success.html", **lead_data)
