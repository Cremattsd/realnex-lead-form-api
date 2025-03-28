from flask import Flask, render_template, request, jsonify, redirect, url_for
import uuid, json, os
from utils.api import create_contact

app = Flask(__name__)

TOKENS_FILE = "tokens/tokens.json"
if not os.path.exists("tokens"):
    os.makedirs("tokens")
if not os.path.exists(TOKENS_FILE):
    with open(TOKENS_FILE, "w") as f:
        json.dump({}, f)

@app.route("/", methods=["GET", "POST"])
def generator():
    if request.method == "POST":
        token = request.form["token"]
        color = request.form.get("color", "#007BFF")
        form_id = str(uuid.uuid4())

        with open(TOKENS_FILE, "r+") as f:
            tokens = json.load(f)
            tokens[form_id] = {"token": token, "color": color}
            f.seek(0)
            json.dump(tokens, f, indent=2)
            f.truncate()

        return render_template("success.html", snippet=f'<iframe src="{request.host_url}form/{form_id}" width="100%" height="500px" style="border:none;"></iframe>')
    
    return render_template("generator.html")

@app.route("/form/<form_id>", methods=["GET", "POST"])
def render_form(form_id):
    with open(TOKENS_FILE) as f:
        tokens = json.load(f)
    config = tokens.get(form_id)
    if not config:
        return "Invalid form", 404

    if request.method == "POST":
        result = create_contact(config["token"], request.form)
        return jsonify(result)
    
    return render_template("lead_form.html", color=config["color"])

if __name__ == "__main__":
    app.run(debug=True)
