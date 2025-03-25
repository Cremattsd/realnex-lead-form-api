from flask import Flask, request, jsonify, render_template
from real_nex_sync_api_data_facade.services.crm_contact import CrmContactService
from real_nex_sync_api_data_facade.models import CreateContact

app = Flask(__name__)

REALNEX_BASE_URL = "https://api.realnex.com"

@app.route('/')
def index():
    return render_template('form.html')

@app.route('/submit-lead', methods=['POST'])
def submit_lead():
    try:
        data = request.get_json()

        token = data.get('token')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        phone = data.get('phone')
        comments = data.get('comments')

        if not token:
            return jsonify({"error": "Missing RealNex token"}), 400

        contact_service = CrmContactService(
            base_url=REALNEX_BASE_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )

        contact_data = CreateContact(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            notes=comments
        )

        created_contact = contact_service.post_contact_async(request_body=contact_data)

        return jsonify({
            "status": "success",
            "contact_key": getattr(created_contact, 'key', None),
            "name": f"{first_name} {last_name}"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
