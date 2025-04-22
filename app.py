from flask import Flask, request, jsonify, render_template
import requests
import sqlite3
import os
from datetime import datetime
import logging
import urllib.parse
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
V2_API_URL = 'https://sync.realnex.com/api/v2'
V1_API_URL = 'https://sync.realnex.com/api/v1'
DB_PATH = 'matts_widget.db'
BASE_URL = 'https://your-flask-app.com'  # Replace with your Flask app URL
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USER = 'your-email@gmail.com'  # Replace with your email
SMTP_PASSWORD = 'your-app-password'  # Replace with app-specific password

# Setup logging
logging.basicConfig(filename='matts_api.log', level=logging.INFO, 
                    format='%(asctime)s - %(message)s')

# Initialize SQLite database
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS clients
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         token TEXT NOT NULL,
                         company_id TEXT,
                         widget_type TEXT NOT NULL,
                         iframe_code TEXT NOT NULL,
                         created_at TEXT NOT NULL)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS api_logs
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         endpoint TEXT NOT NULL,
                         request_data TEXT,
                         response_code INTEGER NOT NULL,
                         response_data TEXT,
                         created_at TEXT NOT NULL)''')

if not os.path.exists(DB_PATH):
    init_db()

# Log API call
def log_api_call(endpoint, request_data, response_code, response_data):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('INSERT INTO api_logs (endpoint, request_data, response_code, response_data, created_at) VALUES (?, ?, ?, ?, ?)',
                     (endpoint, str(request_data), response_code, str(response_data), datetime.utcnow().isoformat()))
    logging.info(f'API Call: {endpoint}, Code: {response_code}')

# Send email notification
def send_no_project_email(email, property_address):
    msg = MIMEText(f"No project found for address '{property_address}'. Please create a project in RealNex to add leads and enhance your CRM experience!")
    msg['Subject'] = 'Create a Project for Your Leads'
    msg['From'] = SMTP_USER
    msg['To'] = email

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        logging.error(f'Email failed: {str(e)}')

# CRM operations
def handle_crm_logic(token, company_id, name, email, message, property_address=None):
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    # Check if contact exists
    contact_url = f'{V1_API_URL}/Crm/contacts?email={urllib.parse.quote(email)}'
    contact_response = requests.get(contact_url, headers=headers)
    log_api_call(contact_url, {'email': email}, contact_response.status_code, contact_response.text)
    
    contact_key = None
    if contact_response.status_code == 200 and contact_response.json():
        contact_key = contact_response.json()[0].get('key')
    else:
        # Create contact
        contact_data = {'name': name, 'email': email}
        contact_url = f'{V1_API_URL}/Crm/contacts'
        contact_response = requests.post(contact_url, json=contact_data, headers=headers)
        log_api_call(contact_url, contact_data, contact_response.status_code, contact_response.text)
        if contact_response.status_code == 200:
            contact_key = contact_response.json().get('key')
        else:
            return {'error': 'Failed to create contact', 'details': contact_response.text}

    # Create company if needed (simplified, assumes companyId is company key)
    company_url = f'{V1_API_URL}/Crm/companies/{company_id}'
    company_response = requests.get(company_url, headers=headers)
    log_api_call(company_url, {'companyId': company_id}, company_response.status_code, company_response.text)
    
    if company_response.status_code != 200:
        company_data = {'name': f'Company for {company_id}', 'key': company_id}
        company_url = f'{V1_API_URL}/Crm/companies'
        company_response = requests.post(company_url, json=company_data, headers=headers)
        log_api_call(company_url, company_data, company_response.status_code, company_response.text)
        if company_response.status_code != 200:
            return {'error': 'Failed to create company', 'details': company_response.text}

    # Link contact to company
    relationship_url = f'{V1_API_URL}/Crm/companies/{company_id}/contacts'
    relationship_data = {'contactKey': contact_key}
    relationship_response = requests.post(relationship_url, json=relationship_data, headers=headers)
    log_api_call(relationship_url, relationship_data, relationship_response.status_code, relationship_response.text)

    # Create lead
    lead_data = {
        'contactKey': contact_key,
        'companyId': company_id,
        'source': "Matt's Widget",
        'status': 'Prospect',
        'notes': message,
        'history': [{'subject': "Lead created by Matt's widget", 'createdAt': datetime.utcnow().isoformat()}]
    }
    lead_url = f'{V1_API_URL}/Crm/leads'
    lead_response = requests.post(lead_url, json=lead_data, headers=headers)
    log_api_call(lead_url, lead_data, lead_response.status_code, lead_response.text)
    
    if lead_response.status_code != 200:
        return {'error': 'Failed to create lead', 'details': lead_response.text}
    
    lead_key = lead_response.json().get('key')

    # Search for project
    if property_address:
        project_url = f'{V1_API_URL}/Crm/projects?search={urllib.parse.quote(property_address)}'
        project_response = requests.get(project_url, headers=headers)
        log_api_call(project_url, {'search': property_address}, project_response.status_code, project_response.text)
        
        if project_response.status_code == 200 and project_response.json():
            project_key = project_response.json()[0].get('key')
            # Attach lead to project
            attach_url = f'{V1_API_URL}/Crm/projects/{project_key}/leads'
            attach_response = requests.post(attach_url, json={'leadKey': lead_key}, headers=headers)
            log_api_call(attach_url, {'leadKey': lead_key}, attach_response.status_code, attach_response.text)
        else:
            send_no_project_email(email, property_address)

    return {'success': True, 'leadKey': lead_key}

# Landing page
@app.route('/')
def landing():
    return render_template('landing.html')

# Generate iframe code
@app.route('/generate', methods=['POST'])
def generate():
    token = request.form.get('token')
    company_id = request.form.get('company_id')
    widget_type = request.form.get('widget_type')

    if not token or (widget_type == 'listings' and not company_id):
        return jsonify({'error': 'Missing token or company ID'}), 400

    # Generate iframe code
    iframe_code = f'<iframe border="0" src="{BASE_URL}/render?type={widget_type}&token={token}'
    if widget_type == 'listings':
        iframe_code += f'&companyId={company_id}'
    iframe_code += f'" width="100%" height="{900 if widget_type == 'listings' else 400}" data-embed="true"></iframe>'

    # Store client data
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('INSERT INTO clients (token, company_id, widget_type, iframe_code, created_at) VALUES (?, ?, ?, ?, ?)',
                     (token, company_id, widget_type, iframe_code, datetime.utcnow().isoformat()))

    return render_template('success.html', iframe_code=iframe_code, widget_type=widget_type)

# Render widget
@app.route('/render')
def render():
    token = request.args.get('token')
    company_id = request.args.get('companyId')
    render_type = request.args.get('type')
    listing_id = request.args.get('listingId')
    page = int(request.args.get('page', 1))
    size = int(request.args.get('size', 16))  # 4x4 grid

    if not token:
        return jsonify({'error': 'Missing token'}), 400

    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}

    if render_type == 'listings':
        if not company_id:
            return jsonify({'error': 'Missing company ID'}), 400
        url = f'{V2_API_URL}/Listing?companyId={company_id}&PageNumber={page}&PageSize={size}'
        response = requests.get(url, headers=headers)
        log_api_call(url, {'method': 'GET', 'companyId': company_id}, response.status_code, response.text)
        
        if response.status_code != 200:
            return jsonify({'error': 'Failed to fetch listings'}), response.status_code
        
        data = response.json()
        return render_template('listings.html', data=data, company_id=company_id, token=token, size=size)

    elif render_type == 'listing' and listing_id:
        if not company_id:
            return jsonify({'error': 'Missing company ID'}), 400
        url = f'{V2_API_URL}/Listing/{listing_id}?companyId={company_id}'
        response = requests.get(url, headers=headers)
        log_api_call(url, {'method': 'GET', 'companyId': company_id, 'listingId': listing_id}, response.status_code, response.text)
        
        if response.status_code != 200:
            return jsonify({'error': 'Listing not found'}), response.status_code
        
        return render_template('listing.html', listing=response.json(), company_id=company_id, token=token)

    elif render_type == 'contact':
        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            message = request.form.get('message')
            property_address = request.form.get('property_address')

            result = handle_crm_logic(token, company_id, name, email, message, property_address)
            if 'error' in result:
                return jsonify(result), 500
            
            return render_template('contact_success.html')
        
        return render_template('contact.html', company_id=company_id, token=token)

    return jsonify({'error': 'Invalid render type'}), 400

if __name__ == '__main__':
    app.run(debug=True)