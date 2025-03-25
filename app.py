from flask import Flask, jsonify, request
from flask_cors import CORS
from real_nex_sync_api_data_facade.services.crm_contact import CrmContactService

app = Flask(__name__)
CORS(app)

# Dummy config — you can replace this with real logic
REALNEX_BASE_URL = "https://api.realnex.com"
REALNEX_TOKEN = "your_token_here"

# Initialize the service
contact_service = CrmContactService(base_url=REALNEX_BASE_URL, token=REALNEX_TOKEN)


@app.route("/")
def index():
    return jsonify({"message": "RealNex Lead Form API is running"}), 200


@app.route("/contact/<contact_key>", methods=["GET"])
def get_contact(contact_key):
    try:
        contact = contact_service.get_contact_async(contact_key)
        return jsonify(contact), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/contact", methods=["POST"])
def create_contact():
    try:
        data = request.json
        contact = contact_service.post_contact_async(request_body=data)
        return jsonify(contact), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
