from flask import Flask, request, render_template_string, jsonify
from real_nex_sync_api_data_facade import RealNexSyncApiDataFacade
from real_nex_sync_api_data_facade.models import CreateContact

app = Flask(__name__)

HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>Test RealNex Lead Form</title>
    <style>
        body { font-family: Arial; padding: 2rem; background: #f9f9f9; }
        form { max-width: 400px; margin: auto; background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        input, button { width: 100%; padding: 0.75rem; margin: 0.5rem 0; border: 1px solid #ccc; border-radius: 5px; }
        button { background-color: #007BFF; color: white; border: none; }
    </style>
</head>
<body>
    <form method="POST">
        <h2>Submit a Lead</h2>
        <input type="text" name="token" placeholder="Your RealNex Token" required />
        <input type="text" name="first_name" placeholder="First Name" required />
        <input type="text" name="last_name" placeholder="Last Name" required />
        <input type="email" name="email" placeholder="Email Address" required />
        <button type="submit">Submit</button>
    </form>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def form():
    if request.method == "POST":
        try:
            token = request.form['token']

            # 🔧 If RealNex expects "Authorization: Bearer {token}", try this:
            api_client = RealNexSyncApiDataFacade(
                api_key=f"Bearer {token}",
                api_key_header="Authorization",  # RealNex might use this header
                base_url="https://sync.realnex.com"
            )

            new_contact = CreateContact(
                first_name=request.form['first_name'],
                last_name=request.form['last_name'],
                email=request.form['email']
            )

            response = api_client.crm_contact.post_contact_async(new_contact)
            return jsonify({"status": "success", "contact": response.dict()})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})

    return render_template_string(HTML_FORM)

if __name__ == "__main__":
    app.run(debug=True)
