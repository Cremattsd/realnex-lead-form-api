from flask import Flask, request, render_template, redirect, url_for, flash, session
import requests
import os
import re
import logging
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# === Flask Config ===
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super-secret")
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "")

# === Logging Config ===
logging.basicConfig(
    filename='realnex_lead_form.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)

# === Utils ===
def sanitize_input(input_string):
    return re.sub(r'[<>"\'&;()]', '', input_string).strip() if input_string else ""

def validate_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

def validate_phone(phone):
    digits_only = re.sub(r'\D', '', phone)
    return digits_only if 7 <= len(digits_only) <= 15 else None

# === Routes ===

@app.route("/", methods=["GET"])
def index():
    return render_template("landing_page.html")

@app.route("/form", methods=["GET", "POST"])
def lead_form():
    token = request.args.get("token") or sanitize_input(request.form.get("token"))
    admin_token = bool(os.getenv("REALNEX_API_TOKEN"))

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
        form_data.update({
            "first_name": sanitize_input(request.form.get("first_name")),
            "last_name": sanitize_input(request.form.get("last_name")),
            "email": sanitize_input(request.form.get("email")),
            "phone": sanitize_input(request.form.get("phone")),
            "company": sanitize_input(request.form.get("company")),
            "address": sanitize_input(request.form.get("address")),
            "comments": sanitize_input(request.form.get("comments"))
        })

        recaptcha_response = request.form.get("g-recaptcha-response")
        errors = []

        if not token:
            errors.append("API Token is required.")
        if not form_data["first_name"]:
            errors.append("First Name is required.")
        if not form_data["last_name"]:
            errors.append("Last Name is required.")
        if not form_data["email"] or not validate_email(form_data["email"]):
            errors.append("Please enter a valid email address.")
        if not recaptcha_response:
            errors.append("Please complete the reCAPTCHA.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

        # === reCAPTCHA verification ===
        recaptcha_verify = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": RECAPTCHA_SECRET_KEY, "response": recaptcha_response}
        )
        if not recaptcha_verify.json().get("success"):
            flash("reCAPTCHA verification failed.", "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        try:
            # === Contact Lookup or Creation ===
            contact_key = None
            search_resp = requests.get(
                f"https://sync.realnex.com/api/v1/Crm/contacts?email={form_data['email']}", headers=headers)
            contact_data = search_resp.json()
            existing_contact = next((c for c in contact_data.get("items", [])), None)

            if existing_contact:
                contact_key = existing_contact["key"]
            else:
                contact_payload = {
                    "firstName": form_data["first_name"],
                    "lastName": form_data["last_name"],
                    "email": form_data["email"],
                    "prospect": True,
                    "address": {
                        "address1": form_data["address"],
                        "company": form_data["company"]
                    },
                    "phones": [{"number": form_data["phone"], "type": "work"}] if form_data["phone"] else []
                }
                contact_resp = requests.post(
                    "https://sync.realnex.com/api/v1/Crm/contact",
                    headers=headers,
                    json=contact_payload
                )
                contact = contact_resp.json()
                contact_key = contact.get("contact", {}).get("key")

            # === Company Lookup or Creation ===
            company_key = None
            if form_data["company"]:
                company_search = requests.get(
                    f"https://sync.realnex.com/api/v1/Crm/companies?name={form_data['company']}", headers=headers)
                companies = company_search.json().get("items", [])
                if companies:
                    company_key = companies[0]["key"]
                else:
                    comp_resp = requests.post(
                        "https://sync.realnex.com/api/v1/Crm/company",
                        headers=headers,
                        json={
                            "name": form_data["company"],
                            "address1": form_data["address"]
                        }
                    )
                    comp_data = comp_resp.json()
                    company_key = comp_data.get("company", {}).get("key")

            # === History Record ===
            history_payload = {
                "subject": "Weblead Submission",
                "notes": form_data["comments"] or "Submitted via web form.",
                "eventTypeKey": "Note",
                "contactKey": contact_key
            }
            if company_key:
                history_payload["companyKey"] = company_key

            history_resp = requests.post(
                "https://sync.realnex.com/api/v1/Crm/history",
                headers=headers,
                json=history_payload
            )

            if history_resp.status_code != 200:
                logging.warning("Failed to create history record: %s", history_resp.text)

            # === Save and Redirect ===
            session['lead_data'] = {
                'first_name': form_data["first_name"],
                'last_name': form_data["last_name"],
                'email': form_data["email"],
                'company': form_data["company"]
            }

            logging.info("Lead successfully submitted: %s", session['lead_data'])
            return redirect(url_for("lead_success"))

        except Exception as e:
            logging.error("Submission error: %s", str(e))
            flash(f"Error submitting to RealNex: {str(e)}", "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

    return render_template("form.html", messages=session.get('_flashes', []), **form_data)

@app.route("/success")
def lead_success():
    lead_data = session.pop("lead_data", {})
    if not lead_data:
        flash("No submission found", "error")
        return redirect(url_for("lead_form"))
    return render_template("success.html", **lead_data)

if __name__ == "__main__":
    app.run(debug=True)
