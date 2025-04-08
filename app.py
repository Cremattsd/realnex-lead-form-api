# ... previous imports ...
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

def sanitize_input(s):
    return re.sub(r'[<>"\'&;()]', '', s or "").strip()

def validate_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

@app.route("/form", methods=["GET", "POST"])
def lead_form():
    token = request.args.get("token") or request.form.get("token")
    if not token:
        flash("API Token is required.", "error")

    data = {
        "token": token,
        "first_name": sanitize_input(request.form.get("first_name", "")),
        "last_name": sanitize_input(request.form.get("last_name", "")),
        "email": sanitize_input(request.form.get("email", "")),
        "phone": sanitize_input(request.form.get("phone", "")),
        "company": sanitize_input(request.form.get("company", "")),
        "address": sanitize_input(request.form.get("address", "")),
        "comments": sanitize_input(request.form.get("comments", "")),
    }

    if request.method == "POST":
        # reCAPTCHA
        recaptcha_response = request.form.get("g-recaptcha-response")
        if not recaptcha_response:
            flash("Please complete the reCAPTCHA.", "error")
        else:
            verify = requests.post("https://www.google.com/recaptcha/api/siteverify", data={
                "secret": RECAPTCHA_SECRET_KEY,
                "response": recaptcha_response
            })
            if not verify.json().get("success"):
                flash("reCAPTCHA verification failed.", "error")

        if not validate_email(data["email"]):
            flash("Invalid email address.", "error")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Contact logic
        try:
            existing_contact = requests.get(
                f"https://sync.realnex.com/api/v1/Crm/contacts?email={data['email']}",
                headers=headers
            ).json()

            contact_key = None
            for contact in existing_contact.get("items", []):
                if contact["firstName"].lower() == data["first_name"].lower() and \
                   contact["lastName"].lower() == data["last_name"].lower():
                    contact_key = contact["key"]
                    break

            if not contact_key:
                resp = requests.post("https://sync.realnex.com/api/v1/Crm/contact", headers=headers, json={
                    "firstName": data["first_name"],
                    "lastName": data["last_name"],
                    "email": data["email"],
                    "phones": [{"number": data["phone"]}] if data["phone"] else []
                }).json()
                contact_key = resp.get("contact", {}).get("key")

            # Company logic
            company_key = None
            if data["company"]:
                resp = requests.post("https://sync.realnex.com/api/v1/Crm/company", headers=headers, json={
                    "name": data["company"],
                    "address_info": {
                        "company": data["company"],
                        "address_1": data["address"]
                    }
                }).json()
                company_key = resp.get("company", {}).get("key")

            # History
            history_payload = {
                "subject": "Weblead",
                "notes": data["comments"] or "Submitted via web form.",
                "linkedContactKeys": [contact_key],
                "linkedCompanyKeys": [company_key] if company_key else [],
                "history_info": {
                    "subject": "Weblead",
                    "event_type_key": "Note"
                }
            }

            hist_resp = requests.post(
                "https://sync.realnex.com/api/v1/Crm/history",
                headers=headers,
                json=history_payload
            )

            if hist_resp.status_code >= 400:
                flash(f"Error posting history: {hist_resp.status_code} {hist_resp.text}", "error")

            session["lead_data"] = {
                "first_name": data["first_name"],
                "last_name": data["last_name"],
                "email": data["email"],
                "company": data["company"]
            }
            return redirect(url_for("lead_success"))

        except Exception as e:
            flash(f"Error submitting to RealNex: {e}", "error")

    return render_template("form.html", messages=session.get('_flashes', []), **data)

@app.route("/success")
def lead_success():
    lead_data = session.pop("lead_data", {})
    return render_template("success.html", **lead_data)

if __name__ == "__main__":
    app.run(debug=True)
