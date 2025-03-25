import os
from flask import Flask, request, jsonify
from realnex_sdk import RealNexSyncApiDataFacade  # Import the SDK for RealNex integration

app = Flask(__name__)

# Access GITHUB_TOKEN environment variable (in case it's needed for SDK access)
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

@app.route('/submit-lead', methods=['POST'])
def submit_lead():
    # Retrieve data from the form submission
    data = request.get_json()
    token = data.get('token')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = data.get('email')
    phone = data.get('phone')
    comments = data.get('comments')
    
    # Initialize the RealNex API client
    try:
        # This assumes your RealNexSyncApiDataFacade has a method that allows integration
        # If the token is being used to interact with RealNex, you can pass it here
        realnex_api = RealNexSyncApiDataFacade(base_url="https://api.realnex.com/", token=token)

        # Add lead or relevant data to RealNex CRM (this depends on the actual SDK functionality)
        response = realnex_api.submit_lead(first_name, last_name, email, phone, comments)

        # Respond with a success message and the API response from RealNex
        return jsonify({"status": "success", "message": "Lead submitted to RealNex", "realnex_response": response})
    
    except Exception as e:
        # Handle any exceptions that occur during the API call
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    # Running the Flask app in debug mode
    app.run(debug=True)
