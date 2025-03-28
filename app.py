from flask import Flask, request, render_template_string, jsonify
import requests

app = Flask(__name__)

HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>Test RealNex Lead Form</title>
    <style>
        body { font-family: Arial; padding: 2rem; background: #f9f9f9; }
        form { max-width: 500px; margin: auto; background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        input, textarea, button { width: 100%; padding: 0.75rem; margin: 0.5rem 0; border: 1px solid #ccc; border-radius: 5px; }
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
        <input type="text" name="phone" placeholder="Phone Number (optional)" />
        <input type="text" name="company" placeholder="Company (optional)" />
        <input type="text" name="address" placeholder="Address (optional)" />
        <textarea name="comments" placeholder="Comments or Inquiry (optional)"></textarea>
        <button type="submit">Submit</button>
    </form>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def lead_form():
    if request.method == "POST":
        try:
            token = request.form['token']
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            # Step 1: Create the Contact
            contact_payload = {
                "firstName": request.form['first_name'],
                "lastName": request.form['last_name'],
                "email": request.form['email'],
            }

            phone = request.form.get('phone')
            if phone:
                contact_payload['phone'] = phone

            response = requests.post(
                "https://sync.realnex.com/api/v1/Crm/contact",
                headers=headers,
                json=contact_payload
            )
            contact_data = response.json()
            contact_key = contact_data.get("contact", {}).get("key")

            if not contact_key:
                return jsonify({"status": "error", "message": "Contact not created.", "details": contact_data})

            # Step 2: Create the Company if Provided
            company_name = request.form.get("company")
            if company_name:
                company_payload = {"name": company_name}
                comp_resp = requests.post(
                    "https://sync.realnex.com/api/v1/Crm/company",
                    headers=headers,
                    json=company_payload
                )
                company_data = comp_resp.json()
                company_key = company_data.get("company", {}).get("key")

                # Link Contact to Company
                if company_key:
                    requests.post(
                        f"https://sync.realnex.com/api/v1/Crm/company/{company_key}/contact/{contact_key}",
                        headers=headers
                    )

            # Step 3: Add Address if Provided
            address = request.form.get("address")
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

            # Step 4: Add History Record
            comments = request.form.get("comments")
            history_payload = {
                "subject": "Weblead",
                "notes": comments or "",
                "contactKey": contact_key
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
