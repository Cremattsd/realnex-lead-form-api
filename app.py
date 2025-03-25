from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from real_nex_sync_api_data_facade.services.crm_contact import CrmContactService
from real_nex_sync_api_data_facade.models import CreateContact
import os

app = Flask(__name__)
CORS(app)

REALNEX_BASE_URL = "https://api.realnex.com"

# Basic landing page with embedded test form
@app.route("/")
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Submit a Test Lead</title>
    </head>
    <body>
      <h1>Submit a Test Lead</h1>
      <form id="leadForm">
        <input type="text" name="token" placeholder="Token" required /><br/>
        <input type="text" name="first_name" placeholder="First Name" required /><br/>
        <input type="text" name="last_name" placeholder="Last Name" required /><br/>
        <input type="email" name="email" placeholder="Email" required /><br/>
        <input type="text" name="phone" placeholder="Phone" required /><br/>
        <textarea name="comments" placeholder="Comments"></textarea><br/>
        <button type="submit">Submit</button>
      </form>

      <p id="result"></p>

      <script>
        const form = document.getElementById('leadForm');
        form.addEventListener('submit', async (e) => {
          e.preventDefault();
          const data = Object.fromEntries(new FormData(form));
          const res = await fetch('/submit-lead', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
          });
          const json = await res.json();
          document.getElementById('result').innerText = JSON.stringify(json, null, 2);
        });
      </script>
    </body>
    </html>
    """)


@app.route("/submit-lead", methods=["POST"])
def submit_lead():
    try:
        data = request.json
        token = data.get("token")

        if not token:
            return jsonify({"error": "Missing token"}), 400

        # Create dynamic contact service
        contact_service = CrmContactService()
        contact_service.base_url = REALNEX_BASE_URL
        contact_service._default_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        new_contact = CreateContact(
            firstName=data.get("first_name"),
            lastName=data.get("last_name"),
            email=data.get("email"),
            phone=data.get("phone"),
            comments=data.get("comments")
        )

        created = contact_service.post_contact_async(new_contact)
        return jsonify({"status": "success", "contact": created}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
