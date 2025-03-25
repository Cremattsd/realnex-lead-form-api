from flask import Flask, request, jsonify
from realnex_sdk import RealNexSyncApiDataFacade  # Import your SDK
import os

app = Flask(__name__)

# Use your real base URL and RealNex token
REALNEX_BASE_URL = "https://api.realnex.com"  # Set this to your actual API base URL
REALNEX_TOKEN = os.environ.get('REALNEX_TOKEN', 'your_realnex_token_here')  # Make sure this is your actual token

# Initialize the SDK instance
realnex_sdk = RealNexSyncApiDataFacade(
    api_key=REALNEX_TOKEN, 
    base_url=REALNEX_BASE_URL
)

@app.route('/submit-lead', methods=['POST'])
def submit_lead():
    data = request.json
    token = data.get('token')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = data.get('email')
    phone = data.get('phone')
    comments = data.get('comments')

    if token != REALNEX_TOKEN:
        return jsonify({"error": "Invalid token"}), 400

    try:
        # Example API Call: Fetching contact details (Replace with your actual logic)
        contact_service = realnex_sdk.crm_contact
        contact = contact_service.get_contact_async(contact_key=first_name)  # Adjust as needed

        return jsonify({"message": "Lead submitted successfully!", "contact": contact}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
