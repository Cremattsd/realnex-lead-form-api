from flask import Flask, request, render_template, redirect, url_for, flash, session
import requests
import os
import re
import logging
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# === Flask Config ===
app = Flask(__name__, static_folder='static')
app.secret_key = os.getenv("SECRET_KEY", "super-secret")
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "")
RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY", "")
REALNEX_API_TOKEN = os.getenv("REALNEX_API_TOKEN", "")

# === Logging Config ===
logging.basicConfig(
    filename='realnex_lead_form.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)

# === Utils ===
def sanitize_input(input_string):
    return re.sub(r'[<>"\'&;()]', '', input_string).strip() if input_string else ""

def validate_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

def validate_phone(phone):
    digits_only = re.sub(r'\D', '', phone)
    return digits_only if 7 <= len(digits_only) <= 15 else None

# === Home ===
@app.route("/", methods=["GET"])
def index():
    logger.info("Rendering index page")
    return render_template("index.html")

# === Contact Form ===
@app.route("/form", methods=["GET", "POST"])
def lead_form():
    token = request.args.get("token") or sanitize_input(request.form.get("token"))
    admin_token = bool(REALNEX_API_TOKEN)

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
            logger.warning("Form validation errors: %s", errors)
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

        recaptcha_verify = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": RECAPTCHA_SECRET_KEY, "response": recaptcha_response}
        )
        if not recaptcha_verify.json().get("success"):
            flash("reCAPTCHA verification failed.", "error")
            logger.warning("reCAPTCHA verification failed")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        try:
            # Contact Lookup or Creation
            contact_key = None
            search_resp = requests.get(
                f"https://sync.realnex.com/api/v1/Crm/contacts?email={form_data['email']}", headers=headers)
            search_resp.raise_for_status()
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
                    "notes": f"UTM Source: {form_data['utm_source']}, "
                             f"Medium: {form_data['utm_medium']}, "
                             f"Campaign: {form_data['utm_campaign']}"
                }
                contact_resp = requests.post(
                    "https://sync.realnex.com/api/v1/Crm/contact",
                    headers=headers,
                    json=contact_payload
                )
                contact_resp.raise_for_status()
                contact = contact_resp.json()
                contact_key = contact.get("contact", {}).get("key")

            # Company Handling
            company_key = None
            if form_data["company"]:
                company_search = requests.get(
                    f"https://sync.realnex.com/api/v1/Crm/companies?name={form_data['company']}", headers=headers)
                company_search.raise_for_status()
                companies = company_search.json().get("items", [])
                if companies:
                    company_key = companies[0]["key"]
                else:
                    comp_resp = requests.post(
                        "https://sync.realnex.com/api/v1/Crm/company",
                        headers=headers,
                        json={"name": form_data["company"], "address1": form_data["address"]}
                    )
                    comp_resp.raise_for_status()
                    comp_data = comp_resp.json()
                    company_key = comp_data.get("company", {}).get("key")

            # History Record
            history_payload = {
                "subject": "Weblead Submission",
                "notes": f"{form_data['comments'] or 'Submitted via web form.'}\n\n"
                         f"UTM Source: {form_data['utm_source']}, "
                         f"Medium: {form_data['utm_medium']}, "
                         f"Campaign: {form_data['utm_campaign']}",
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
            history_resp.raise_for_status()

            session['lead_data'] = {
                'first_name': form_data["first_name"],
                'last_name': form_data["last_name"],
                'email': form_data["email"],
                'company': form_data["company"]
            }
            logger.info("Lead submitted successfully for email: %s", form_data["email"])
            return redirect(url_for("lead_success"))

        except requests.exceptions.HTTPError as e:
            logger.error("HTTP error submitting to RealNex: %s, Response: %s", e, e.response.text)
            flash(f"Error submitting to RealNex: {str(e)}", "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)
        except Exception as e:
            logger.error("Unexpected error submitting to RealNex: %s", str(e))
            flash(f"Error submitting to RealNex: {str(e)}", "error")
            return render_template("form.html", messages=session.get('_flashes', []), **form_data)

    logger.info("Rendering lead form")
    return render_template("form.html", messages=session.get('_flashes', []), **form_data)

# === Listings View + Inquiry Form ===
@app.route("/listings", methods=["GET", "POST"])
def listings():
    company_id = request.args.get("companyId")
    token = request.args.get("token")
    if not company_id or not token:
        flash("Company ID and Token are required.", "error")
        logger.warning("Missing companyId or token in /listings")
        return render_template("listings.html", listings=[], inquiry_result=None, messages=session.get('_flashes', []))

    listings_data = []
    inquiry_result = None

    if request.method == "GET":
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(
                f"https://sync.realnex.com/api/v2/marketplace/listings/company/{company_id}",
                headers=headers
            )
            response.raise_for_status()
            listings_data = response.json()
            logger.info("Fetched %d listings for companyId: %s", len(listings_data), company_id)
        except requests.exceptions.HTTPError as e:
            logger.error("HTTP error fetching listings: %s, Response: %s", e, e.response.text)
            flash("Failed to fetch listings.", "error")
        except Exception as e:
            logger.error("Unexpected error fetching listings: %s", str(e))
            flash("Error fetching listings.", "error")

    elif request.method == "POST":
        try:
            first_name = sanitize_input(request.form.get("first_name"))
            last_name = sanitize_input(request.form.get("last_name"))
            email = sanitize_input(request.form.get("email"))
            phone = sanitize_input(request.form.get("phone"))
            message = sanitize_input(request.form.get("message"))
            listing_id = sanitize_input(request.form.get("listing_id"))

            if not all([first_name, last_name, email, token]):
                flash("Missing required fields", "error")
                logger.warning("Missing required fields in listings inquiry")
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
            contact_resp.raise_for_status()
            contact = contact_resp.json()
            contact_key = contact.get("contact", {}).get("key")

            history_payload = {
                "subject": f"Listing Inquiry: {listing_id}",
                "notes": message or "Submitted from listing form",
                "eventTypeKey": "Note",
                "contactKey": contact_key
            }

            history_resp = requests.post(
                "https://sync.realnex.com/api/v1/Crm/history",
                headers=headers,
                json=history_payload
            )
            history_resp.raise_for_status()

            inquiry_result = "Thank you! Your inquiry has been submitted."
            logger.info("Inquiry submitted for listing_id: %s, email: %s", listing_id, email)

        except requests.exceptions.HTTPError as e:
            logger.error("HTTP error submitting inquiry: %s, Response: %s", e, e.response.text)
            flash("Failed to log inquiry to CRM.", "error")
        except Exception as e:
            logger.error("Unexpected error submitting inquiry: %s", str(e))
            flash("Something went wrong while submitting your inquiry.", "error")

    return render_template("listings.html", listings=listings_data, inquiry_result=inquiry_result, messages=session.get('_flashes', []))

# === Snippet Generator ===
@app.route("/snippet", methods=["GET", "POST"])
def snippet():
    generated_code = ""
    company_id = ""
    token = ""
    snippet_type = "contact"

    if request.method == "POST":
        company_id = sanitize_input(request.form.get("company_id"))
        token = sanitize_input(request.form.get("token"))
        snippet_type = request.form.get("snippet_type", "contact")

        if not token:
            flash("CRM Token is required.", "error")
            logger.warning("Missing token in snippet generation")
        elif snippet_type == "listings" and not company_id:
            flash("Company ID is required for Listings.", "error")
            logger.warning("Missing company_id for listings snippet")
        else:
            iframe_url = f"https://realnex-lead-form-api.onrender.com/{'form' if snippet_type == 'contact' else 'listings'}?token={token}"
            if snippet_type == "listings":
                iframe_url += f"&companyId={company_id}"
            generated_code = f'<iframe src="{iframe_url}" width="100%" height="800" frameborder="0"></iframe>'
            logger.info("Generated snippet for type: %s, companyId: %s", snippet_type, company_id or "N/A")

    return render_template("snippet.html", generated_code=generated_code, company_id=company_id, token=token, snippet_type=snippet_type)

# === Success Page ===
@app.route("/success")
def lead_success():
    lead_data = session.pop("lead_data", {})
    if not lead_data:
        flash("No submission found", "error")
        logger.warning("No lead_data in session for /success")
        return redirect(url_for("lead_form"))
    logger.info("Rendering success page for email: %s", lead_data.get("email"))
    return render_template("success.html", **lead_data)

# === Debug CSS Route ===
@app.route("/test_css")
def test_css():
    logger.info("Serving test CSS page")
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
