from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from real_nex_sync_api_data_facade.services.crm_contact import CrmContactService

REALNEX_TOKEN = os.environ.get("REALNEX_TOKEN")
REALNEX_BASE_URL = "https://api.realnex.com"

app = Flask(__name__)
CORS(app)

# Set up the Contact Service without passing token in constructor
contact_service = CrmContactService()

# Manually configure the base URL and headers with token
contact_service.base_url = REALNEX_BASE_URL
contact_service._default_headers = {
    "Authorization": f"Bearer {REALNEX_TOKEN}",
    "Content-Type": "application/json"
}

@app.route("/test-contact", methods=["GET"])
def test_contact():
    try:
        # Replace with a valid contactKey for testing
        contact_key = request.args.get("contact_key", "SOME_CONTACT_KEY")
        result = contact_service.get_contact_async(contact_key)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def home():
    return "✅ RealNex Lead Form API is live and ready!"

if __name__ == "__main__":
    app.run(debug=True)
