from flask import Flask, request, render_template_string, jsonify
import requests

app = Flask(__name__)

HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>Submit a Lead</title>
    <style>
        body { font-family: Arial; background-color: #f5f5f5; padding: 2rem; }
        form { max-width: 400px; margin: auto; background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        input, button { width: 100%; padding: 0.75rem; margin: 0.5rem 0; border: 1px solid #ccc; border-radius: 5px; }
        button { background-color: #007BFF; color: white; border: none; }
    </style>
</head>
<body>
    <form method="POST">
        <h2>RealNex Lead Form</h2>
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
        token = request.form['token']
        contact_data = {
            "firstName": request.form['first_name'],
            "lastName": request.form['last_name'],
            "email": request.form['email']
        }

        try:
            response = requests.post(
                "https://sync.realnex.com/api/v1/Crm/contact",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json=contact_data
            )

            if response.status_code == 200:
                return jsonify({"status": "success", "contact": response.json()})
            else:
                return jsonify({"status": "error", "message": f"{response.status_code} - {response.text}"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})

    return render_template_string(HTML_FORM)

if __name__ == "__main__":
    app.run(debug=True)
