from flask import Flask, request, render_template_string, jsonify
import requests

app = Flask(__name__)

HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>Submit a Lead</title>
    <style>
        body { font-family: Arial; padding: 2rem; background: #f2f2f2; }
        form { background: #fff; padding: 2rem; max-width: 500px; margin: auto; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        input, textarea, button { width: 100%; margin-bottom: 1rem; padding: 0.75rem; border: 1px solid #ccc; border-radius: 4px; }
        button { background-color: #007BFF; color: white; border: none; }
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

        first = request.form.get("first_name")
        last = request.form.get("last_name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        company = request.form.get("company")
        address = request.form.get("address")
        comments = request.form.get("comments")

        try:
            # Search for existing contact
            search_resp = requests.get(
                f"https://sync.realnex.com/api/v1/Crm/contacts?email={email}",
                headers=headers
            )
            if search_resp.status_code != 200:
                return jsonify({"status": "error", "message": f"Contact search failed: {search_resp.text}"})

            contact_data = search_resp.json()
            existing_contact = next((c for c in contact_data.get("items", []) if c["firstName"].lower() == first.lower() and c["lastName"].lower() == last.lower()), None)

            if existing_contact:
                contact_key = existing_contact["key"]
            else:
                contact_payload = {
                    "firstName": first,
                    "lastName": last,
                    "email": email,
                    "phones": [{"number": phone, "isPrimary": True}] if phone else []
                }
                contact_resp = requests.post("https://sync.realnex.com/api/v1/Crm/contact", headers=headers, json=contact_payload)
                if contact_resp.status_code != 200:
                    return jsonify({"status": "error", "message": f"Contact creation failed: {contact_resp.text}"})
                contact = contact_resp.json()
                contact_key = contact.get("contact", {}).get("key")

            company_key = None
            if company:
                company_search = requests.get(f"https://sync.realnex.com/api/v1/Crm/companies?name={company}", headers=headers)
                if company_search.status_code == 200:
                    companies = company_search.json().get("items", [])
                    if companies:
                        company_key = companies[0]["key"]
                    else:
                        company_payload = {"name": company, "address1": address}
                        comp_resp = requests.post("https://sync.realnex.com/api/v1/Crm/company", headers=headers, json=company_payload)
                        if comp_resp.status_code == 200:
                            company_key = comp_resp.json().get("company", {}).get("key")

            history_payload = {
                "subject": "Weblead",
                "notes": comments or "Submitted via web form.",
                "linkedContactKeys": [contact_key],
                "linkedCompanyKeys": [company_key] if company_key else [],
                "eventType": "Note"
            }
            history_resp = requests.post("https://sync.realnex.com/api/v1/Crm/history", headers=headers, json=history_payload)
            if history_resp.status_code != 200:
                return jsonify({"status": "error", "message": f"History creation failed: {history_resp.text}"})

            return jsonify({"status": "success", "contact_key": contact_key, "company_key": company_key})

        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})

    return render_template_string(HTML_FORM)

if __name__ == "__main__":
    app.run(debug=True)
