from flask import Flask, request, jsonify
from real_nex_sync_api_data_facade.services.crm_contact import ContactService
from real_nex_sync_api_data_facade.services.crm_company import CompanyService
from real_nex_sync_api_data_facade.services.crm_history import HistoryService

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

        # Init services with token
        contact_service = ContactService(token)
        company_service = CompanyService(token)
        history_service = HistoryService(token)

        # 1. Try to match an existing contact
        contact = contact_service.find_by_email(data['email'])

        # 2. If not found, create a new contact
        if not contact:
            contact_payload = {
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'email': data['email'],
                'phone': data['phone']
            }

            # Optional: add company association logic here using CompanyService
            contact = contact_service.create(contact_payload)

        # 3. Add history event to the contact
        history_payload = {
            'contact_id': contact['id'],
            'event_type': 'Lead Web Form',
            'notes': data.get('comments', '')
        }

        history_service.create(history_payload)

        return jsonify({'status': 'success'}), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
