from flask import Flask, jsonify, request
from real_nex_sync_api_data_facade import RealNexSyncApiDataFacade

app = Flask(__name__)

# Replace these with your actual API URL and Token
API_URL = "YOUR_API_URL"  # Example: "https://api.realnex.com"
API_TOKEN = "YOUR_API_TOKEN"  # Replace with your RealNex API token

# Initialize RealNex SDK client
api_client = RealNexSyncApiDataFacade(API_URL, API_TOKEN)

@app.route('/get_contacts', methods=['GET'])
def get_contacts():
    try:
        # Using crm_contact to fetch all contacts
        contacts = api_client.crm_contact.get_all()  # This method needs to exist in your SDK
        return jsonify(contacts), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/create_contact', methods=['POST'])
def create_contact():
    data = request.get_json()

    try:
        # Assuming your API expects name and email
        contact_data = {
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
            "email": data.get("email")
        }

        # Using crm_contact to create a new contact
        created_contact = api_client.crm_contact.create(contact_data)  # This method needs to exist
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

        # Using crm_contact to update a contact
        updated_contact = api_client.crm_contact.update(contact_id, updated_data)  # This method needs to exist
        return jsonify(updated_contact), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/delete_contact', methods=['DELETE'])
def delete_contact():
    data = request.get_json()

    try:
        contact_id = data.get("contact_id")

        # Using crm_contact to delete a contact
        api_client.crm_contact.delete(contact_id)  # This method needs to exist
        return jsonify({"message": "Contact deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
