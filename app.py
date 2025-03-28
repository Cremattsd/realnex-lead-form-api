from flask import Flask, jsonify, request
from flask_cors import CORS
from real_nex_sync_api_data_facade import RealNexSyncApiDataFacade
from real_nex_sync_api_data_facade.models import CreateContact

app = Flask(__name__)
CORS(app)

# Replace these with your actual API URL and Token
API_URL = "https://api.realnex.com"  # Example endpoint
API_TOKEN = "YOUR_API_TOKEN"  # Securely injected per user in final version

# Initialize RealNex SDK client
api_client = RealNexSyncApiDataFacade(API_URL, API_TOKEN)

@app.route("/", methods=["GET"])
def index():
    return jsonify({"message": "RealNex Lead Form API is running!"})

@app.route('/get_contacts', methods=['GET'])
def get_contacts():
    try:
        contacts = api_client.crm_contact.get_all()
        return jsonify(contacts), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/create_contact', methods=['POST'])
def create_contact():
    data = request.get_json()

    try:
        contact = CreateContact(
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            email=data.get("email")
        )
        created_contact = api_client.crm_contact.post_contact_async(contact)
        return jsonify(created_contact), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/update_contact', methods=['PUT'])
def update_contact():
    data = request.get_json()

    try:
        contact_id = data.get("contact_id")
        updated_data = {
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
            "email": data.get("email")
        }
        updated_contact = api_client.crm_contact.update(contact_id, updated_data)
        return jsonify(updated_contact), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/delete_contact', methods=['DELETE'])
def delete_contact():
    data = request.get_json()

    try:
        contact_id = data.get("contact_id")
        api_client.crm_contact.delete_contact_async(contact_id)
        return jsonify({"message": "Contact deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
