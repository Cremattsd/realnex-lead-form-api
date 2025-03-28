from flask import render_template, request

@app.route("/lead-form")
def lead_form():
    token = request.args.get("token")
    if not token:
        return "Missing token", 400

    return render_template("lead_form.html", token=token)
