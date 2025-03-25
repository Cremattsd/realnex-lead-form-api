from flask import Flask, request, jsonify
from flask-cors import CORS

from real_nex_sync_api_data_facade.services.crm_contact import ContactService
from real_nex_sync_api_data_facade.services.crm_company import CompanyService
from real_nex_sync_api_data_facade.services.crm_history import HistoryService

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/')
def index():
    return '✅ RealNex Lead Form API is running.'

@app.route('/submit-lead', methods=['POST'])
def submit_lead():
    try:
        data = request.get_json()
        print("📥 Incoming data:", data)

        token = data.get('token')
        if not token:
            print("❌ Missing token")
            return jsonify({'error': 'Missing token'}), 400

        print("🔐 Token received: " + token[:10] + "...")

        # Initialize services
        contact_service = ContactService(token)
        company_service = CompanyService(token)
        history_service = HistoryService(token)

        # Try to find the contact by email
        contact = contact_service.find_by_email(data['email'])
        print("🔍 Contact found:", contact)

        # If not found, create a new one
        if not contact:
            contact_payload = {
                'first_name': data.get('first_name'),
                'last_name': data.get('last_name'),
                'email': data.get('email'),
                'phone': data.get('phone')
            }

            # You can use company_service here if needed
            contact = contact_service.create(contact_payload)
            print("🆕 Contact created:", contact)

        # Add a history record
        history_payload = {
            'contact_id': contact['id'],
            'event_type': 'Lead Web Form',
            'notes': data.get('comments', '')
        }

        history_service.create(history_payload)
        print("📘 History added for contact:", contact['id'])

        return jsonify({'status': 'success'}), 200

    except Exception as e:
        print("🔥 Exception:", str(e))
        return jsonify({'status': 'error', 'message': str(e)}), 500
