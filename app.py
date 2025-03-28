from flask import Flask, request, render_template_string, jsonify
import requests

app = Flask(__name__)

HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>Submit a Lead</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 2rem; background-color: #f4f4f4; }
        form { max-width: 500px; margin: auto; background: #fff; padding: 2rem; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        input, button, textarea { width: 100%; margin: 0.5rem 0; padding: 0.75rem; border-radius: 4px; border: 1px solid #ccc; }
        button { background-color: #007BFF; color: white; font-weight: bold; border: none; cursor: pointer; }
        button:hover { background-color: #0056b3; }
    </style>
</head>
<body>
    <form method="POST">
        <h2>Submit a Lead</h2>
        <input type="text" name="token" placeholder="Your RealNex API Token" required />
        <input type="text" name="first_name" placeholder="First Name" required />
        <input type="text" name="last_name" placeholder="Last Name" required />
        <input type="email" name="email" placeholder="Email Address" required />
        <input type="text" name="company" placeholder="Company (optional)" />
        <input type="text" name="address" placeholder="Address (optional)" />
        <textarea name="notes" placeholder="Additional Notes (optional)"></textarea>
        <button type="submit">Submit</button>
    </form>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def lead_form():
    if request.method == "POST":
        try:
            token = request.form["token"]
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            contact_payload = {
                "firstName": request.form["first_name"],
                "lastName": request.form["last_name"],
                "email": request.form["email"],
            }

            if request.form.get("address"):
                contact_payload["addresses"] = [{"address1": request.form["address"]}]

            company_key = None
            if request.form.get("company"):
                company_resp = requests.post(
                    "https://sync.realnex.com/api/v1/Crm/company",
                    headers=headers,
                    json={"name": request.form["company"]}
                )
                if company_resp.status_code == 200 and "key" in company_resp.json():
                    company_key = company_resp.json()["key"]
                    contact_payload["companyKey"] = company_key

            contact_resp = requests.post(
                "https://sync.realnex.com/api/v1/Crm/contact",
                headers=headers,
                json=contact_payload
            )

            contact_data = contact_resp.json()
            if "contact" in contact_data:
                contact_key = contact_data["contact"]["key"]

                # Create Weblead History Record
                history_payload = {
                    "description": request.form.get("notes", "Lead submitted via Web Form."),
                    "eventType": "Weblead",
                    "contactKeys": [contact_key]
                }
                history_resp = requests.post(
                    "https://sync.realnex.com/api/v1/Crm/history",
                    headers=headers,
                    json=history_payload
                )

                return jsonify({
                    "status": "success",
                    "contact_key": contact_key,
                    "history_status": history_resp.status_code
                })

            else:
                return jsonify({"status": "error", "message": "Contact not created.", "details": contact_data})

        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})

    return render_template_string(HTML_FORM)

if __name__ == "__main__":
    app.run(debug=True)
