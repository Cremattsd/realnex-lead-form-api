from flask import Flask, jsonify, request
from real_nex_sync_api_data_facade import RealNexSyncApiDataFacade

app = Flask(__name__)

# Replace with actual API base URL and token
API_URL = "https://api.realnex.com"  # Update as needed
API_TOKEN = "YOUR_REALNEX_API_KEY"  # Replace with your token

# Initialize RealNex SDK properly
api_client = RealNexSyncApiDataFacade(api_key=API_TOKEN, base_url=API_URL)

# Simple root route to confirm app is running
@app.route("/", methods=["GET"])
def index():
    return jsonify({"message": "RealNex Lead Form API is running!"}), 200

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
        contact_data = {
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
            "email": data.get("email")
        }
        created_contact = api_client.crm_contact.create(contact_data)
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
        api_client.crm_contact.delete(contact_id)
        return jsonify({"message": "Contact deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
