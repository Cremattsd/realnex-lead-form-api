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
        "investor_type": "",
        "tenant_size_range": "",
        "utm_source": request.args.get("utm_source", ""),
        "utm_medium": request.args.get("utm_medium", ""),
        "utm_campaign": request.args.get("utm_campaign", ""),
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
            "comments": sanitize_input(request.form.get("comments")),
            "investor_type": sanitize_input(request.form.get("investor_type")),
            "tenant_size_range": sanitize_input(request.form.get("tenant_size_range"))
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

        recaptcha_verify = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": RECAPTCHA_SECRET_KEY, "response": recaptcha_response}
        )
        if not recaptcha_verify.json().get("success"):
            flash("reCAPTCHA verification failed.", "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        try:
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
                    "phones": [{"number": form_data["phone"], "type": "work"}] if form_data["phone"] else [],
                    "customFields": [
                        {"fieldName": "Investor Type", "value": form_data["investor_type"]},
                        {"fieldName": "Tenant Size Range", "value": form_data["tenant_size_range"]}
                    ],
                    "notes": f"UTM Source: {form_data['utm_source']}, Medium: {form_data['utm_medium']}, Campaign: {form_data['utm_campaign']}"
                }
                contact_resp = requests.post(
                    "https://sync.realnex.com/api/v1/Crm/contact",
                    headers=headers,
                    json=contact_payload
                )
                contact = contact_resp.json()
                contact_key = contact.get("contact", {}).get("key")

            history_payload = {
                "subject": "Weblead Submission",
                "notes": f"{form_data['comments'] or 'Submitted via web form.'}\n\nUTM Source: {form_data['utm_source']}, Medium: {form_data['utm_medium']}, Campaign: {form_data['utm_campaign']}",
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
            logging.error("Error submitting to RealNex: %s", str(e))
            flash(f"Error submitting to RealNex: {str(e)}", "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

    return render_template("form.html", messages=session.get('_flashes', []), **form_data)

@app.route("/listings", methods=["GET", "POST"])
def listings():
    company_id = request.args.get("companyId")
    if not company_id:
        return "Company ID is required", 400

    listings_data = []
    inquiry_result = None

    if request.method == "GET":
        try:
            response = requests.get(
                f"https://sync.realnex.com/api/v2/marketplace/listings/company/{company_id}"
            )
            if response.status_code == 200:
                listings_data = response.json()
            else:
                app.logger.warning("Failed to fetch listings: %s", response.text)
        except Exception as e:
            app.logger.error("Error fetching listings: %s", str(e))

    elif request.method == "POST":
        try:
            first_name = sanitize_input(request.form.get("first_name"))
            last_name = sanitize_input(request.form.get("last_name"))
            email = sanitize_input(request.form.get("email"))
            phone = sanitize_input(request.form.get("phone"))
            message = sanitize_input(request.form.get("message"))
            listing_id = sanitize_input(request.form.get("listing_id"))
            token = request.form.get("token")

            if not all([first_name, last_name, email, token]):
                flash("Missing required fields", "error")
                return redirect(request.url)

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            contact_payload = {
                "firstName": first_name,
                "lastName": last_name,
                "email": email,
                "phones": [{"number": phone, "type": "work"}] if phone else [],
                "prospect": True
            }

            contact_resp = requests.post(
                "https://sync.realnex.com/api/v1/Crm/contact",
                headers=headers,
                json=contact_payload
            )
            contact = contact_resp.json()
            contact_key = contact.get("contact", {}).get("key")

            history_payload = {
                "subject": f"Listing Inquiry: {listing_id}",
                "notes": message or "Submitted from listing form",
                "eventTypeKey": "Note",
                "contactKey": contact_key
            }

            requests.post(
                "https://sync.realnex.com/api/v1/Crm/history",
                headers=headers,
                json=history_payload
            )

            inquiry_result = "Thank you! Your inquiry has been submitted."

        except Exception as e:
            app.logger.error("Error submitting inquiry: %s", str(e))
            flash("Something went wrong while submitting your inquiry.", "error")

    return render_template("listings.html", listings=listings_data, inquiry_result=inquiry_result)

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

@app.route("/success")
def lead_success():
    lead_data = session.pop("lead_data", {})
    if not lead_data:
        flash("No submission found", "error")
        return redirect(url_for("lead_form"))
    return render_template("success.html", **lead_data)

if __name__ == "__main__":
    app.run(debug=True)
