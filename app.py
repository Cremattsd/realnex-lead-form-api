from flask import Flask, render_template, request, jsonify
from real_nex_sync_api_data_facade import RealNexSyncApiDataFacade

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"message": "RealNex Lead Form API is running!"})

@app.route("/lead-form")
def lead_form():
    token = request.args.get("token")
    if not token:
        return "Missing token", 400
    return render_template("lead_form.html", token=token)

@app.route("/submit-lead", methods=["POST"])
def submit_lead():
    token = request.form.get("token")
    if not token:
        return "Token missing", 400

    data = {
        "first_name": request.form.get("first_name"),
        "last_name": request.form.get("last_name"),
        "email": request.form.get("email"),
        "message": request.form.get("message"),
    }

    try:
        rn = RealNexSyncApiDataFacade(api_key=token)
        contact = rn.crm_contact.create(data)
        return render_template("thank_you.html")
    except Exception as e:
        return f"Error: {e}", 500

if __name__ == "__main__":
    app.run(debug=True)
