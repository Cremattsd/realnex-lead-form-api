from flask import Flask, request, render_template, redirect, url_for, flash, session, get_flashed_messages
import requests
import os
import re
import logging
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super-secret")
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "")
REALNEX_API_BASE = os.getenv("REALNEX_API_BASE", "https://sync.realnex.com")

logging.basicConfig(
    filename=os.path.join(os.getenv("LOG_DIR", "."), "realnex_lead_form.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
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

@app.route("/snippet/form", methods=["GET", "POST"])
def snippet_form():
    generated_code = ""
    token = ""
    if request.method == "POST":
        token = sanitize_input(request.form.get("token"))
        if token:
            iframe_url = f"/form?token={token}"
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
            iframe_url = f"/listings?companyId={company_id}&token={token}"
            generated_code = f'<iframe src="{iframe_url}" width="100%" height="800" frameborder="0"></iframe>'
        else:
            flash("Both Company ID and CRM Token are required.", "error")
    return render_template("snippet_listings.html", generated_code=generated_code, company_id=company_id, token=token)
