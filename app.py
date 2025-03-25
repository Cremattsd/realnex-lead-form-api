from flask import Flask, request, render_template_string, jsonify
from real_nex_sync_api_data_facade.services.crm_contact import CrmContactService
from real_nex_sync_api_data_facade.models import CreateContact

app = Flask(__name__)

form_html = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>RealNex Lead Form</title>
  <style>
    body { font-family: 'Segoe UI', sans-serif; background: #f1f5f9; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
    .form-container { background: white; padding: 2rem; border-radius: 1rem; box-shadow: 0 10px 20px rgba(0,0,0,0.1); width: 100%; max-width: 500px; }
    input, button { width: 100%; padding: 0.75rem; margin-top: 0.5rem; border-radius: 0.5rem; border: 1px solid #ccc; font-size: 1rem; }
    button { background-color: #2563eb; color: white; border: none; font-weight: 600; cursor: pointer; }
    button:hover { background-color: #1d4ed8; }
    h2 { text-align: center; margin-bottom: 1rem; }
  </style>
</head>
<body>
  <div class="form-container">
    <h2>RealNex Lead Form</h2>
    <form method="POST" action="/create_contact">
      <input type="text" name="first_name" placeholder="First Name" required />
      <input type="text" name="last_name" placeholder="Last Name" required />
      <input type="email" name="email" placeholder="Email" required />
      <input type="tel" name="phone" placeholder="Phone Number" />
      <input type="text" name="token" placeholder="RealNex Token" required />
      <button type="submit">Submit</button>
    </form>
  </div>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(form_html)

@app.route("/create_contact", methods=["POST"])
def create_contact():
    try:
        token = request.form["token"]
        contact_data = CreateContact(
            first_name=request.form["first_name"],
            last_name=request.form["last_name"],
            email=request.form["