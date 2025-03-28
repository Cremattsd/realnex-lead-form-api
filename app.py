from flask import Flask, request, render_template_string, jsonify
import requests

app = Flask(__name__)

HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>Submit a Lead</title>
</head>
<body>
    <h2>Submit a Lead</h2>
    <form method="POST">
        <input type="text" name="token" placeholder="API Token" required><br>
        <input type="text" name="first_name" placeholder="First Name" required><br>
        <input type="text" name="last_name" placeholder="Last Name" required><br>
        <input type="email" name="email" placeholder="Email" required><br>
        <input type="text" name="company" placeholder="Company (optional)"><br>
        <input type="text" name="phone" placeholder="Phone (optional)"><br>
        <input type="text" name="address" placeholder="Address (optional)"><br>
        <textarea name="notes" placeholder="Comments (optional)"></textarea><br>
        <button type="submit">Submit</button>
    </form>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def lead_form():
    if request.method == "POST":
        token = request.form.get("token")
        contact_payload = {
            "firstName": request.form.get("first_name"),
            "lastName": request.form.get("last_name"),
            "email": request.form.get("email"),
        }

        if request.form.get("phone"):
            contact_payload["phone"] = request.form.get("phone")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Step 1: Create Contact
        contact_response = requests.post(
            "https://sync.realnex.com/api/v1/Crm/contact",
            headers=headers,
            json=contact_payload
        )

        if contact_response.status_code != 200:
            return jsonify({"status": "error", "message": "Failed to create contact", "details": contact_response.text})

        contact_data = contact_response.json()
        contact_key = contact_data.get("key") or contact_data.get("contact", {}).get("key")

        if not contact_key:
            return jsonify({"status": "error", "message": "Contact key not found.", "raw": contact_data})

        # Step 2: Create Company if provided
        company_name = request.form.get("company")
        if company_name:
            company_payload = {"name": company_name}
            company_response = requests.post(
                "https://sync.realnex.com/api/v1/Crm/company",
                headers=headers,
                json=company_payload
            )
            if company_response.status_code == 200:
                company_data = company_response.json()
                company_key = company_data.get("key") or company_data.get("company", {}).get("key")
                # Optionally associate company with contact
                requests.put(
                    f"https://sync.realnex.com/api/v1/Crm/contact/{contact_key}/company/{company_key}",
                    headers=headers
                )

        # Step 3: Add Address if provided
        address = request.form.get("address")
        if address:
            address_payload = {
                "address1": address,
                "principalType": "Contact",
                "principalKey": contact_key
            }
            requests.post(
                "https://sync.realnex.com/api/v1/Crm/address",
                headers=headers,
                json=address_payload
            )

        # Step 4: Add History record with Web Lead info
        notes = request.form.get("notes")
        history_payload = {
            "subject": "Web Lead",
            "note": notes or "New web lead submission.",
            "contactKey": contact_key
        }
        requests.post(
            "https://sync.realnex.com/api/v1/Crm/history",
            headers=headers,
            json=history_payload
        )

        return jsonify({"status": "success", "contact_key": contact_key})

    return render_template_string(HTML_FORM)

if __name__ == "__main__":
    app.run(debug=True)
