from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from real_nex_sync_api_data_facade.services.crm_contact import CrmContactService
from real_nex_sync_api_data_facade.models import CreateContact

app = Flask(__name__)
CORS(app)

REALNEX_BASE_URL = "https://api.realnex.com"

@app.route('/')
def index():
    return render_template('form.html')


@app.route('/submit-lead', methods=['POST'])
def submit_lead():
    data = request.get_json()
    
    if not data or 'token' not in data:
        return jsonify({'error': 'Missing API token'}), 400

    token = data['token']

    try:
        # Initialize service and set token
        contact_service = CrmContactService(base_url=REALNEX_BASE_URL)
        contact_service.set_token(token)

        # Map incoming data to CreateContact model
        contact = CreateContact(
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            email=data.get('email'),
            phone=data.get('phone'),
            notes=data.get('comments', '')
        )

        # Create contact in RealNex
        result = contact_service.post_contact_async(contact)
        return jsonify({'status': 'success', 'contact_key': result.key})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
