from flask import Flask, request, render_template_string, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>RealNex Lead Form</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f4f4; padding: 2rem; }
        form { max-width: 600px; margin: auto; background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        input, textarea, button { width: 100%; padding: 10px; margin: 10px 0; }
        button { background-color: #007BFF; color: white; border: none; cursor: pointer; }
        button:hover { background-color: #0056b3; }
    </style>
</head>
<body>
    <form method="POST">
        <h2>Submit a Lead</h2>
        <input type="text" name="token" placeholder="RealNex Token" required />
        <input type="text" name="first_name" placeholder="First Name" required />
        <input type="text" name="last_name" placeholder="Last Name" required />
        <input type="email" name="email" placeholder="Email Address" required />
        <input type="text" name="phone" placeholder="Phone Number" />
        <input type="text" name="company" placeholder="Company Name (Optional)" />
        <input type="text" name="address" placeholder="Address (Optional)" />
        <textarea name="comments" placeholder="Comments or Notes"></textarea>
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

            # Step 1: Create Contact
            contact_payload = {
                "firstName": request.form['first_name'],
                "lastName": request.form['last_name'],
                "email": request.form['email']
            }

            phone = request.form.get("phone")
            if phone:
                contact_payload["phones"] = [{"number": phone, "type": "Mobile", "isPrimary": True}]

            address = request.form.get("address")
            if address:
                contact_payload["addresses"] = [{"address1": address}]

            contact_response = requests.post(
                "https://sync.realnex.com/api/v1/Crm/contact",
                headers=headers,
                json=contact_payload
            )
            contact_data = contact_response.json()
            contact_key = contact_data.get("contact", {}).get("key")

            if not contact_key:
                return jsonify({"status": "error", "details": contact_data})

            # Step 2: Create Company (Optional)
            company_name = request.form.get("company")
            if company_name:
                company_payload = {"name": company_name}
                company_response = requests.post(
                    "https://sync.realnex.com/api/v1/Crm/company",
                    headers=headers,
                    json=company_payload
                )
                company_data = company_response.json()
                company_key = company_data.get("company", {}).get("key")

                if company_key:
                    requests.post(
                        f"https://sync.realnex.com/api/v1/Crm/contact/{contact_key}/company/{company_key}",
                        headers=headers
                    )

            # Step 3: Create History Note
            comments = request.form.get("comments")
            if comments:
                history_payload = {
                    "subject": "Web Lead",
                    "note": comments,
                    "contactKeys": [contact_key]
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
