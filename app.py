import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from real_nex_sync_api_data_facade.sdk import RealNexSyncApiDataFacade  # Adjusted import

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing for the app

# Initialize the RealNex API client
REALNEX_BASE_URL = 'https://api.realnex.com'  # Replace with the correct base URL
REALNEX_TOKEN = os.getenv('REALNEX_TOKEN')  # Get the RealNex token from environment variables
contact_service = RealNexSyncApiDataFacade(base_url=REALNEX_BASE_URL, token=REALNEX_TOKEN)

@app.route('/')
def index():
    return "RealNex Lead Form API is running!"

@app.route('/submit-lead', methods=['POST'])
def submit_lead():
    # Get the data from the incoming form submission
    lead_data = request.json
    token = lead_data.get('token')

    if token != REALNEX_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401

    first_name = lead_data.get('first_name')
    last_name = lead_data.get('last_name')
    email = lead_data.get('email')
    phone = lead_data.get('phone')
    comments = lead_data.get('comments')

    # Create contact in RealNex CRM using the provided data
    try:
        contact_service.create_contact({
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
            'comments': comments
        })
        return jsonify({"message": "Lead submitted successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
