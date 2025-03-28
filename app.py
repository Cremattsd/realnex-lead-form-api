from flask import Flask, request, render_template_string, jsonify
import requests

app = Flask(__name__)

HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>RealNex Lead Form</title>
    <style>
        body { font-family: Arial; padding: 2rem; background: #f2f2f2; }
        form { background: white; padding: 2rem; border-radius: 10px; max-width: 500px; margin: auto; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        input, textarea, button { width: 100%; margin: 0.5rem 0; padding: 0.75rem; border-radius: 5px; border: 1px solid #ccc; }
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
        <input type="text" name="phone" placeholder="Phone (optional)" />
        <input type="text" name="company" placeholder="Company (optional)" />
        <input type="text" name="address" placeholder="Address (optional)" />
        <textarea name="comments" placeholder="Comments (will appear in notes)"></textarea>
        <button type="submit">Submit</button>
    </form>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def lead_form():
    if request.method == "POST":
        try:
            # Get form data
            token = request.form["token"]
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            first_name = request.form.get("first_name")
            last_name = request.form.get("last_name")
            email = request.form.get("email")
            phone = request.form.get("phone", "")
            company_name = request.form.get("company", "")
            address = request.form.get("address", "")
            comments = request.form.get("comments", "")

            # STEP 1: Create Contact
            contact_payload = {
                "firstName": first_name,
                "lastName": last_name,
                "email": email,
                "phones": [{"number": phone, "type": "Mobile"}] if phone else [],
                "addresses": [{"address1": address}] if address else []
            }

            contact_res = requests.post(
                "https://sync.realnex.com/api/v1/Crm/contact",
                headers=headers,
                json=contact_payload
            )
            contact_data = contact_res.json()
            contact_key = contact_data.get("contact", {}).get("key") or contact_data.get("key")

            if not contact_key:
                return jsonify({"status": "error", "message": "Contact not created", "response": contact_data})

            # STEP 2: Create Company (optional)
            if company_name:
                company_payload = {"name": company_name}
                company_res = requests.post(
                    "https://sync.realnex.com/api/v1/Crm/company",
                    headers=headers,
                    json=company_payload
                )
                company_key = company_res.json().get("key")

                if company_key:
                    # Link contact to company
                    link_payload = {"companyKey": company_key}
                    requests.post(
                        f"https://sync.realnex.com/api/v1/Crm/contact/{contact_key}/company",
                        headers=headers,
                        json=link_payload
                    )

            # STEP 3: Create History Record
            history_payload = {
                "subject": "Weblead",
                "notes": comments,
                "eventType": "Note",
                "linkedContacts": [contact_key]
            }

            requests.post(
                "https://sync.realnex.com/api/v1/Crm/history",
                headers=headers,
                json=history_payload
            )

            return jsonify({"status": "success", "contact_key": contact_key})

        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})

    return render_template_string(HTML_FORM)

if __name__ == "__main__":
    app.run(debug=True)
