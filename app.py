from flask import Flask, render_template, request, jsonify
import requests
import os

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return render_template("form.html")

@app.route("/submit", methods=["POST"])
def submit():
    try:
        token = request.form["token"]
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        email = request.form["email"]
        phone = request.form.get("phone")
        investor_type = request.form.get("investor_type")
        tenant_min = request.form.get("tenant_min")
        tenant_max = request.form.get("tenant_max")

        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "custom_fields": {
                "Investor Type": investor_type,
                "Tenant Size Min": tenant_min,
                "Tenant Size Max": tenant_max
            }
        }

        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post("https://api.realnex.com/v2/contacts", json=payload, headers=headers)

        if response.status_code == 200:
            return "Contact submitted successfully!"
        else:
            return f"Error: {response.text}", 400

    except Exception as e:
        return f"Server Error: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True)