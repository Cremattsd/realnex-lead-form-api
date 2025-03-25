from flask import Flask, request, jsonify, render_template
from real_nex_sync_api_data_facade.services.crm_contact import CrmContactService
from real_nex_sync_api_data_facade.models import CreateContact

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("form.html")

@app.route("/submit-lead", methods=["POST"])
def submit_lead():
    try:
        data = request.get_json()

        token = data.get("token")
        if not token:
            return jsonify({"error": "Missing RealNex token"}), 400

        contact = CreateContact(
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            email=data.get("email"),
            phone=data.get("phone"),
            comments=data.get("comments")
        )

        contact_service = CrmContactService(
            base_url="https://api.realnex.com/",
            token=token
        )

        response = contact_service.post_contact_async(request_body=contact)
        return jsonify({"success": True, "contact_key": response.key})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
