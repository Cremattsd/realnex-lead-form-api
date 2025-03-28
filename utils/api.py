import requests

def create_contact(token, form_data):
    url = "https://sync.realnex.com/api/v1/Crm/contact"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "firstName": form_data.get("first_name"),
        "lastName": form_data.get("last_name"),
        "email": form_data.get("email"),
        "doNotEmail": False
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            return {"status": "success", "data": response.json()}
        return {"status": "error", "message": response.text}
    except Exception as e:
        return {"status": "error", "message": str(e)}
