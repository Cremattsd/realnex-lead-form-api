from flask import Flask, request, render_template, redirect, url_for, flash, session
import requests
import os
import re
import logging
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super-secret")
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "")

logging.basicConfig(
    filename='realnex_lead_form.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)

def sanitize_input(input_string):
    return re.sub(r'[<>"]', '', input_string).strip() if input_string else ""

def validate_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

def validate_phone(phone):
    digits_only = re.sub(r'\D', '', phone)
    return digits_only if 7 <= len(digits_only) <= 15 else None

@app.route("/")
def index():
    return render_template("landing_page.html")

@app.route("/success")
def lead_success():
    lead_data = session.pop("lead_data", {})
    if not lead_data:
        flash("No submission found", "error")
        return redirect(url_for("lead_form"))
    return render_template("success.html", **lead_data)

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
        "comments": "",
        "utm_source": request.args.get("utm_source", ""),
        "utm_medium": request.args.get("utm_medium", ""),
        "utm_campaign": request.args.get("utm_campaign", "")
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

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        try:
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
            contact_resp = requests.post("https://sync.realnex.com/api/v1/Crm/contact", headers=headers, json=contact_payload)
            contact = contact_resp.json()
            contact_key = contact.get("contact", {}).get("key")

            history_payload = {
                "subject": "Weblead Submission",
                "notes": form_data["comments"] or "Submitted via web form.",
                "eventTypeKey": "Note",
                "contactKey": contact_key
            }
            requests.post("https://sync.realnex.com/api/v1/Crm/history", headers=headers, json=history_payload)

            session['lead_data'] = {
                'first_name': form_data["first_name"],
                'last_name': form_data["last_name"],
                'email': form_data["email"],
                'company': form_data["company"]
            }
            return redirect(url_for("lead_success"))
        except Exception as e:
            flash(f"Error submitting to RealNex: {str(e)}", "error")

    return render_template("form.html", messages=session.get('_flashes', []), **form_data)

@app.route("/snippet/form", methods=["GET", "POST"])
def snippet_form():
    generated_code = ""
    token = ""

    if request.method == "POST":
        token = sanitize_input(request.form.get("token"))
        if token:
            iframe_url = f"https://realnex-lead-form-api.onrender.com/form?token={token}"
            generated_code = f'<iframe src="{iframe_url}" width="100%" height="600" frameborder="0"></iframe>'
        else:
            flash("CRM Token is required.", "error")

    return render_template("snippet_form.html", generated_code=generated_code, token=token)

@app.route("/snippet/listings", methods=["GET", "POST"])
def snippet_listings():
    generated_code = ""
    company_id = ""
    token = ""

    if request.method == "POST":
        company_id = sanitize_input(request.form.get("company_id"))
        token = sanitize_input(request.form.get("token"))

        if company_id and token:
            iframe_url = f"https://realnex-lead-form-api.onrender.com/listings?companyId={company_id}&token={token}"
            generated_code = f'<iframe src="{iframe_url}" width="100%" height="800" frameborder="0"></iframe>'
        else:
            flash("Both Company ID and CRM Token are required.", "error")

    return render_template("snippet_listings.html", generated_code=generated_code, company_id=company_id, token=token)
