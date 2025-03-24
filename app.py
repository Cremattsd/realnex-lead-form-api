from flask import Flask, request, jsonify
from real_nex_sync_api_data_facade.sdk import RealNexClient

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

        client = RealNexClient(token=token)

        # Match or create contact
        contact = client.find_contact(email=data['email'])
        if not contact:
            contact = client.create_contact({
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'email': data['email'],
                'phone': data['phone']
            })

        # Add history record
        client.add_history({
            'contact_id': contact['id'],
            'event_type': 'Lead Web Form',
            'notes': data['comments']
        })

        return jsonify({'status': 'success'}), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
