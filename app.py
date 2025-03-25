from flask import Flask, request, jsonify
from real_nex_sync_api_data_facade.services.crm_contact import ContactCRM
from real_nex_sync_api_data_facade.services.crm_company import CompanyCRM
from real_nex_sync_api_data_facade.services.crm_history import HistoryCRM

app = Flask(__name__)

@app.route('/')
def home():
    return 'RealNex Lead Form API is running.'

@app.route('/submit-lead', methods=['POST'])
def submit_lead():
    try:
        data = request.get_json()
        token = data.get('token')
        if not token:
            return jsonify({'error': 'Missing token'}), 400

        # Initialize SDK service classes
        contact_service = ContactCRM(token)
        company_service = CompanyCRM(token)
        history_service = HistoryCRM(token)

        # Try to find existing contact
        contact = contact_service.find_by_email(data['email'])

        # If not found, create contact
        if not contact:
            contact_payload = {
                'first_name': data.get('first_name', ''),
                'last_name': data.get('last_name', ''),
                'email': data.get('email', ''),
                'phone': data.get('phone', '')
            }
            contact = contact_service.create(contact_payload)

        # Add a history entry
        history_payload = {
            'contact_id': contact['id'],
            'event_type': 'Lead Web Form',
            'notes': data.get('comments', '')
        }
        history_service.create(history_payload)

        return jsonify({'status': 'success'}), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500