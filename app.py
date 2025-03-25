import os
import pip
from flask import Flask, request, jsonify
from realnex_sdk import RealNexSyncApiDataFacade  # Import the SDK for RealNex integration

# Check installed packages
installed_packages = pip.get_installed_distributions()
print("Installed packages:")
for package in installed_packages:
    print(package)

app = Flask(__name__)

# RealNex Base URL
REALNEX_BASE_URL = os.getenv('REALNEX_BASE_URL', 'https://api.realnex.com/')

# Set your API token here
REALNEX_TOKEN = os.getenv('REALNEX_TOKEN', '')

# Initialize the RealNexSyncApiDataFacade with the base URL and token
realnex_client = RealNexSyncApiDataFacade(base_url=REALNEX_BASE_URL, token=REALNEX_TOKEN)


@app.route('/')
def home():
    return "RealNex Lead Form API"


@app.route('/submit-lead', methods=['POST'])
def submit_lead():
    try:
        # Get lead data from the request
        data = request.json

        # Extract data from the request
        token = data.get('token', '')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        email = data.get('email', '')
        phone = data.get('phone', '')
        comments = data.get('comments', '')

        # You can implement logic to process this data (e.g., save to database or send to RealNex API)
        
        # Example: Create a new contact in RealNex CRM (modify this as per your requirements)
        contact_data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
            'comments': comments
        }

        # Create the contact in RealNex using the SDK
        realnex_client.create_contact(contact_data)

        return jsonify({"message": "Lead submitted successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
