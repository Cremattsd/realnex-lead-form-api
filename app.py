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

@app.route("/listing/<listing_id>", methods=["GET", "POST"])
def listing_detail(listing_id):
    company_id = request.args.get("companyId")
    token = request.args.get("token")

    if not company_id or not token:
        return "Missing company ID or token", 400

    headers = {"Authorization": f"Bearer {token}"}
    listing = {}
    attachments = []
    demographics = {}
    contacts = []

    try:
        listings_resp = requests.get(f"https://sync.realnex.com/api/v2/marketplace/listings/company/{company_id}", headers=headers)
        if listings_resp.status_code == 200:
            listings = listings_resp.json()
            listing = next((l for l in listings if str(l.get("id")) == str(listing_id)), {})

            if not listing.get("images"):
                photos_resp = requests.get(f"https://sync.realnex.com/api/v2/marketplace/listings/{listing_id}/photos", headers=headers)
                if photos_resp.status_code == 200:
                    listing["images"] = [p["url"] for p in photos_resp.json() if p.get("url")]

            attach_resp = requests.get(f"https://sync.realnex.com/api/v2/marketplace/listings/{listing_id}/attachments", headers=headers)
            if attach_resp.status_code == 200:
                attachments = attach_resp.json()

            demo_resp = requests.get(f"https://sync.realnex.com/api/v2/marketplace/listings/{listing_id}/demographics", headers=headers)
            if demo_resp.status_code == 200:
                demographics = demo_resp.json()

            contact_resp = requests.get(f"https://sync.realnex.com/api/v2/marketplace/listings/{listing_id}/contacts", headers=headers)
            if contact_resp.status_code == 200:
                contacts = contact_resp.json()

        else:
            return f"Failed to fetch listing: {listings_resp.text}", 500
    except Exception as e:
        return f"Error fetching listing: {str(e)}", 500

    if request.method == "POST":
        try:
            first_name = sanitize_input(request.form.get("first_name"))
            last_name = sanitize_input(request.form.get("last_name"))
            email = sanitize_input(request.form.get("email"))
            phone = sanitize_input(request.form.get("phone"))
            message = sanitize_input(request.form.get("message"))

            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            contact_payload = {
                "firstName": first_name,
                "lastName": last_name,
                "email": email,
                "phones": [{"number": phone, "type": "work"}] if phone else [],
                "prospect": True
            }
            contact_resp = requests.post("https://sync.realnex.com/api/v1/Crm/contact", headers=headers, json=contact_payload)
            contact = contact_resp.json()
            contact_key = contact.get("contact", {}).get("key")

            history_payload = {
                "subject": f"Listing Inquiry: {listing.get('title', 'Unknown Listing')}",
                "notes": message or "Submitted from listing detail page",
                "eventTypeKey": "Note",
                "contactKey": contact_key
            }
            requests.post("https://sync.realnex.com/api/v1/Crm/history", headers=headers, json=history_payload)

            flash("Your inquiry has been submitted!", "success")
        except Exception as e:
            flash(f"Error submitting inquiry: {str(e)}", "error")

    return render_template(
        "listing_detail.html",
        listing=listing,
        token=token,
        attachments=attachments,
        demographics=demographics,
        contacts=contacts
    )

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
