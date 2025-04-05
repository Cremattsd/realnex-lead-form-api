from flask import Flask, request, render_template_string, jsonify, redirect, url_for, flash, session
import requests
import os
import re
from dotenv import load_dotenv
from functools import wraps

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
DEFAULT_API_TOKEN = os.getenv("REALNEX_API_TOKEN", "")
RECAPTCHA_SECRET = os.getenv("RECAPTCHA_SECRET", "")

# HTML Templates
HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>Submit a Lead</title>
    <script src="https://www.google.com/recaptcha/api.js" async defer></script>
    <style>
        body { font-family: Arial; padding: 2rem; background: #f2f2f2; line-height: 1.6; }
        form { background: #fff; padding: 2rem; max-width: 500px; margin: auto; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        input, textarea, button { width: 100%; margin-bottom: 1rem; padding: 0.75rem; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        button { background-color: #007BFF; color: white; border: none; cursor: pointer; }
        button:hover { background-color: #0056b3; }
    </style>
</head>
<body>
    <form method="POST">
        <h2>Submit Lead</h2>
        <input name="token" placeholder="RealNex API Token" required />
        <input name="first_name" placeholder="First Name" required />
        <input name="last_name" placeholder="Last Name" required />
        <input name="email" placeholder="Email" required type="email" />
        <input name="phone" placeholder="Phone Number" />
        <input name="company" placeholder="Company" />
        <input name="address" placeholder="Address" />
        <textarea name="comments" placeholder="Comments"></textarea>
        <div class="g-recaptcha" data-sitekey="6LdRMgsrAAAAABbjZLyAYef9uXW-xwMrjYtyHB2j"></div>
        <button type="submit">Submit</button>
    </form>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def lead_form():
    if request.method == "POST":
        token = request.form.get("token")
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        recaptcha_response = request.form.get("g-recaptcha-response")
        recaptcha_verify = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={
                "secret": RECAPTCHA_SECRET,
                "response": recaptcha_response
            }
        )
        recaptcha_result = recaptcha_verify.json()
        if not recaptcha_result.get("success"):
            return jsonify({"status": "error", "message": "reCAPTCHA verification failed."})

        first = request.form.get("first_name")
        last = request.form.get("last_name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        company = request.form.get("company")
        address = request.form.get("address")
        comments = request.form.get("comments")

        try:
            search_resp = requests.get(
                f"https://sync.realnex.com/api/v1/Crm/contacts?email={email}",
                headers=headers
            )
            contact_data = search_resp.json()
            existing_contact = None
            for c in contact_data.get("items", []):
                if c["firstName"].lower() == first.lower() and c["lastName"].lower() == last.lower():
                    existing_contact = c
                    break

            if existing_contact:
                contact_key = existing_contact["key"]
            else:
                contact_payload = {
                    "firstName": first,
                    "lastName": last,
                    "email": email,
                    "phones": [{"number": phone}] if phone else []
                }
                contact_resp = requests.post(
                    "https://sync.realnex.com/api/v1/Crm/contact",
                    headers=headers,
                    json=contact_payload
                )
                contact = contact_resp.json()
                contact_key = contact.get("contact", {}).get("key")

            company_key = None
            if company:
                company_search = requests.get(
                    f"https://sync.realnex.com/api/v1/Crm/companies?name={company}",
                    headers=headers
                )
                companies = company_search.json().get("items", [])
                if companies:
                    company_key = companies[0]["key"]
                else:
                    comp_resp = requests.post(
                        "https://sync.realnex.com/api/v1/Crm/company",
                        headers=headers,
                        json={"name": company, "address1": address}
                    )
                    comp_data = comp_resp.json()
                    company_key = comp_data.get("company", {}).get("key")

            history_payload = {
                "subject": "Weblead",
                "notes": comments or "Submitted via web form.",
                "linkedContactKeys": [contact_key],
                "linkedCompanyKeys": [company_key] if company_key else [],
                "eventType": "Note"
            }
            requests.post(
                "https://sync.realnex.com/api/v1/Crm/history",
                headers=headers,
                json=history_payload
            )

            return jsonify({"status": "success", "contact_key": contact_key, "company_key": company_key})

        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})

    return render_template_string(HTML_FORM)

if __name__ == "__main__":
    app.run(debug=True)