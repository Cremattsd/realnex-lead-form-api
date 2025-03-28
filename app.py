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
