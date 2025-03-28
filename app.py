from flask import Flask, request, render_template_string, jsonify
import requests

app = Flask(__name__)

HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>RealNex Lead Form</title>
    <style>
        body { font-family: Arial; padding: 2rem; background: #f9f9f9; }
        form { max-width: 500px; margin: auto; background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        input, button { width: 100%; padding: 0.75rem; margin: 0.5rem 0; border: 1px solid #ccc; border-radius: 5px; }
        button { background-color: #007BFF; color: white; border: none; }
    </style>
</head>
<body>
    <form method="POST">
        <h2>Submit a Lead</h2>
        <input type="text" name="token" placeholder="Your RealNex Token" required />
        <input type="text" name="first_name" placeholder="First Name" required />
        <input type="text" name="last_name" placeholder="Last Name" required />
        <input type="email" name="email" placeholder="Email Address" required />
        <input type="text" name="company" placeholder="Company Name (optional)" />
        <input type="text" name="address" placeholder="Address (optional)" />
        <textarea name="notes" placeholder="Additional Notes (optional)" rows="3"></textarea>
        <button type="submit">Submit</button>
    </form>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def lead_form():
    if request.method == "POST":
        token = request.form.get("token")
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        company = request.form.get("company")
        address = request.form.get("address")
        notes = request.form.get("notes")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            # Step 1: Create Contact
            contact_payload = {
                "firstName": first_name,
                "lastName": last_name,
                "email": email
            }

            contact_response = requests.post(
                "https://sync.realnex.com/api/v1/Crm/contact",
                headers=headers,
                json=contact_payload
            )
            contact_response.raise_for_status()
            contact_data = contact_response.json()
            contact_key = contact_data["contact"]["key"]

            # Step 2: Create Company (if provided)
            if company:
                company_payload = {"name": company}
                company_response = requests.post(
                    "https://sync.realnex.com/api/v1/Crm/company",
                    headers=headers,
                    json=company_payload
                )
                company_response.raise_for_status()
                company_key = company_response.json()["company"]["key"]

                # Link Contact to Company
                requests.put(
                    f"https://sync.realnex.com/api/v1/Crm/contact/{contact_key}/company/{company_key}",
                    headers=headers
                )

            # Step 3: Add Address (if provided)
            if address:
                address_payload = {
                    "address1": address,
                    "contactKey": contact_key
                }
                requests.post(
                    "https://sync.realnex.com/api/v1/Crm/contact/address",
                    headers=headers,
                    json=address_payload
                )

            # Step 4: Add History Entry
            history_payload = {
                "contactKeys": [contact_key],
                "eventType": "Weblead",
                "subject": "Weblead submitted",
                "notes": notes or "Submitted from website."
            }
            requests.post(
                "https://sync.realnex.com/api/v1/Crm/history",
                headers=headers,
                json=history_payload
            )

            return jsonify({"status": "success", "message": "Lead submitted successfully."})

        except requests.exceptions.RequestException as e:
            return jsonify({"status": "error", "message": str(e)})

    return render_template_string(HTML_FORM)

if __name__ == "__main__":
    app.run(debug=True)
