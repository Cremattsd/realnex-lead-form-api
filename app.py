from flask import Flask, request, jsonify, render_template
from real_nex_sync_api_data_facade import RealNexClient
from real_nex_sync_api_data_facade.services.crm_contact import CrmContactService
from realnex_form_helpers import build_contact_payload
import os

app = Flask(__name__, static_folder="static", template_folder="templates")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/create_contact", methods=["POST"])
def create_contact():
    data = request.json
    token = data.get("token")

    if not token:
        return jsonify({"error": "Missing RealNex token."}), 400

    try:
        client = RealNexClient(company_id=token)
        contact_service = CrmContactService(client)

        payload = build_contact_payload(data)
        response = contact_service.post_contact_async(request_body=payload)
        return jsonify({"message": "Contact created.", "contact_key": response.contact_key})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
