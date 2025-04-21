import sqlite3
from flask import Flask, render_template, request, send_file, flash, redirect, url_for, Response, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Regexp
import requests
import uuid
import json
from datetime import datetime, timedelta
from urllib.parse import urlparse, quote
import html
from flask_cors import CORS  # Added for CORS support
from dotenv import load_dotenv  # Added for loading .env file
import os

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')  # Load from .env, fallback to default
CORS(app)  # Enable CORS for all routes

# Configuration
API_BASE_URL_V1 = "https://sync.realnex.com/api/v1"  # For CRM endpoints (V1 API)
API_BASE_URL_V2 = "https://sync.realnex.com/api/v1"  # For Listings endpoint (V2 API)
EMBED_URL = "https://realnex-lead-form-api.onrender.com"

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('db/credentials.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS credentials
                 (unique_id TEXT PRIMARY KEY, snippet_type TEXT, company_id TEXT, token TEXT,
                  custom_style_url TEXT, theme TEXT, expires TIMESTAMP)''')
    conn.commit()
    conn.close()

# Clean up expired credentials
def cleanup_expired_credentials():
    conn = sqlite3.connect('db/credentials.db')
    c = conn.cursor()
    c.execute("DELETE FROM credentials WHERE expires < ?", (datetime.now(),))
    conn.commit()
    conn.close()

init_db()

# Flask-WTF Form for Snippet Generation
class SnippetForm(FlaskForm):
    snippet_type = SelectField('Snippet Type', choices=[
        ('contact', 'Contact Us'),
        ('listings', 'Listings + Contact Us')
    ], validators=[DataRequired()])
    company_id = StringField('Company ID', validators=[Regexp(r'^[a-zA-Z0-9\-]+$')])
    token = PasswordField('CRM API Token', validators=[DataRequired()])
    custom_style_url = StringField('Custom Style URL (optional)', validators=[Regexp(r'^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$', message="Please enter a valid URL")])
    theme = SelectField('Theme (optional)', choices=[
        ('', 'Default (Light)'),
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('modern', 'Modern')
    ])
    submit = SubmitField('Generate Snippet')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/snippet', methods=['GET', 'POST'])
def generate_snippet():
    form = SnippetForm()
    
    if request.method == 'GET' and 'snippet_type' in request.args:
        form.snippet_type.data = request.args.get('snippet_type')
    
    if form.validate_on_submit():
        snippet_type = form.snippet_type.data
        company_id = form.company_id.data.strip() if form.company_id.data else ''
        token = form.token.data.strip()
        custom_style_url = form.custom_style_url.data.strip() if form.custom_style_url.data else ''
        theme = form.theme.data if form.theme.data else 'light'
        
        # Validate credentials (using a V1 endpoint for validation)
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        if company_id:
            headers['X-Company-ID'] = company_id
        
        try:
            endpoint = '/Crm/contacts' if snippet_type == 'contact' else '/Crm/listings'
            base_url = API_BASE_URL_V1 if snippet_type == 'contact' else API_BASE_URL_V2
            response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=5)
            
            if response.status_code == 200:
                # Generate a unique ID for this snippet
                unique_id = str(uuid.uuid4())
                
                # Store credentials in SQLite with expiration (24 hours)
                expires = datetime.now() + timedelta(hours=24)
                conn = sqlite3.connect('db/credentials.db')
                c = conn.cursor()
                c.execute("INSERT INTO credentials (unique_id, snippet_type, company_id, token, custom_style_url, theme, expires) VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (unique_id, snippet_type, company_id, token, custom_style_url, theme, expires))
                conn.commit()
                conn.close()
                
                # Generate the embed snippet
                script_url = f"{EMBED_URL}/embed.js?type={snippet_type}&id={unique_id}"
                if custom_style_url:
                    script_url += f"&style_url={quote(custom_style_url)}"
                if theme:
                    script_url += f"&theme={theme}"
                embed_snippet = f"""<div id="realnex-form-{unique_id}"></div>
<script src="{script_url}"></script>"""
                
                # Generate a mock preview with the selected theme
                preview_class = f"theme-{theme}" if theme else "theme-light"
                preview = f"""
                <div class="{preview_class}" style="font-family: system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 20px; border: 1px solid #ccc; border-radius: 8px;">
                    <h3>Contact Us</h3>
                    <form>
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">First Name</label>
                            <input type="text" style="width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 8px;" placeholder="First Name">
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">Last Name</label>
                            <input type="text" style="width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 8px;" placeholder="Last Name">
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">Email</label>
                            <input type="email" style="width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 8px;" placeholder="Email">
                        </div>
                        <button type="submit" style="width: 100%; padding: 12px; background-color: #007BFF; color: white; border: none; border-radius: 8px;">Submit</button>
                    </form>
                </div>
                """ if snippet_type == 'contact' else f"""
                <div class="{preview_class}" style="font-family: system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; border: 1px solid #ccc; border-radius: 8px;">
                    <h3>Sample Property Listing</h3>
                    <p>Modern office space in downtown area.</p>
                    <p><strong>Address:</strong> 123 Main St, City, State</p>
                    <form>
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">First Name</label>
                            <input type="text" style="width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 8px;" placeholder="First Name">
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">Email</label>
                            <input type="email" style="width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 8px;" placeholder="Email">
                        </div>
                        <button type="submit" style="width: 100%; padding: 12px; background-color: #007BFF; color: white; border: none; border-radius: 8px;">Inquire</button>
                    </form>
                </div>
                """
                
                return render_template('success.html', shortcode=embed_snippet, preview=preview, theme=theme)
            else:
                flash(f"Invalid credentials: {response.json().get('message', 'Unknown error')}", 'error')
        except requests.RequestException as e:
            flash(f"API validation failed: {str(e)}", 'error')
    
    return render_template('snippet.html', form=form)

@app.route('/embed.js')
def serve_embed_js():
    snippet_type = request.args.get('type')
    unique_id = request.args.get('id')
    custom_style_url = request.args.get('style_url', '')
    theme = request.args.get('theme', 'light')
    
    # Clean up expired credentials
    cleanup_expired_credentials()
    
    # Retrieve credentials from SQLite
    conn = sqlite3.connect('db/credentials.db')
    c = conn.cursor()
    c.execute("SELECT * FROM credentials WHERE unique_id = ?", (unique_id,))
    creds = c.fetchone()
    conn.close()
    
    if not snippet_type or not unique_id or not creds:
        return Response(
            """document.getElementById('realnex-form-""" + unique_id + """').innerHTML = '<p role="alert" style="color: red;">Error: Invalid parameters or expired session. Please generate a new embed code.</p>';""",
            mimetype='application/javascript'
        )
    
    # Check expiration
    expires = datetime.strptime(creds[6], '%Y-%m-%d %H:%M:%S.%f')
    if expires < datetime.now():
        conn = sqlite3.connect('db/credentials.db')
        c = conn.cursor()
        c.execute("DELETE FROM credentials WHERE unique_id = ?", (unique_id,))
        conn.commit()
        conn.close()
        return Response(
            """document.getElementById('realnex-form-""" + unique_id + """').innerHTML = '<p role="alert" style="color: red;">Error: Session expired. Please generate a new embed code.</p>';""",
            mimetype='application/javascript'
        )
    
    token = creds[3]
    company_id = creds[2]
    
    # Render the form or listings
    html_content = ""
    if snippet_type == 'contact':
        html_content = render_template('contact_form.html', embed_url=EMBED_URL, unique_id=unique_id)
    else:
        # Fetch listings using V2 API
        listings = []
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        if company_id:
            headers['X-Company-ID'] = company_id
        else:
            return Response(
                """document.getElementById('realnex-form-""" + unique_id + """').innerHTML = '<p role="alert" style="color: red;">Error: Company ID is required for listings.</p>';""",
                mimetype='application/javascript'
            )
        
        try:
            response = requests.get(f"{API_BASE_URL_V2}/Crm/listings", headers=headers, timeout=5)
            if response.status_code == 200:
                response_data = response.json()
                listings = response_data.get('data', response_data.get('items', []))
                for listing in listings:
                    listing['key'] = listing.get('id', listing.get('key', ''))
                    listing['title'] = listing.get('name', listing.get('title', 'Untitled Listing'))
                    listing['description'] = listing.get('details', listing.get('description', 'No description available.'))
                    listing['address'] = listing.get('location', listing.get('address', 'N/A'))
                    # Additional fields for detailed view
                    listing['price'] = listing.get('price', 'N/A')
                    listing['squareFootage'] = listing.get('squareFootage', 'N/A')
                    # Handle images
                    listing['images'] = listing.get('images', [])
                    if listing['images'] and isinstance(listing['images'], list):
                        listing['thumbnail'] = listing['images'][0].get('url', '')
                    else:
                        listing['thumbnail'] = ''
                    # Sanitize strings to prevent XSS
                    for key in listing:
                        if isinstance(listing[key], str):
                            listing[key] = html.escape(listing[key])
        except requests.RequestException as e:
            error_message = f"Failed to fetch listings: {str(e)}"
            return Response(
                f"""document.getElementById('realnex-form-{unique_id}').innerHTML = '<p role="alert" style="color: red;">{error_message}</p>';""",
                mimetype='application/javascript'
            )
        
        if not listings:
            html_content = "<p>No listings found.</p>"
        else:
            listings_html = render_template('listing_form.html', embed_url=EMBED_URL, unique_id=unique_id, listings=listings)
            html_content = f'<div class="realnex-listings-container">{listings_html}</div>'
    
    # Determine theme CSS file
    theme_css = f"theme-{theme}.css" if theme in ['light', 'dark', 'modern'] else "theme-light.css"
    
    # Handle custom styles
    custom_style_script = ""
    if custom_style_url:
        try:
            result = urlparse(custom_style_url)
            if all([result.scheme in ['http', 'https'], result.netloc]):
                custom_style_script = f"""
                var customLink = document.createElement('link');
                customLink.rel = 'stylesheet';
                customLink.href = '{custom_style_url}';
                document.head.appendChild(customLink);
                """
            else:
                custom_style_script = "console.warn('RealNex Embed: Invalid custom style URL');"
        except Exception:
            custom_style_script = "console.warn('RealNex Embed: Invalid custom style URL');"
    
    # JavaScript to inject the HTML, load styles, and handle form submission and navigation
    js_content = f"""
    (function() {{
        var container = document.getElementById('realnex-form-{unique_id}');
        if (!container) {{
            console.error('RealNex Embed: Container not found');
            return;
        }}
        
        // Load theme styles
        var themeLink = document.createElement('link');
        themeLink.rel = 'stylesheet';
        themeLink.href = '{EMBED_URL}/static/css/{theme_css}';
        document.head.appendChild(themeLink);
        
        // Load custom styles if provided
        {custom_style_script}
        
        // Inject HTML
        container.innerHTML = `{html_content.replace('`', '\\`').replace('\n', ' ')}`;
        
        // Handle tile clicks to show detailed view
        var tiles = container.querySelectorAll('.realnex-listing-tile');
        var currentView = 'tile'; // Track current view (tile or detail)
        var currentListing = null; // Track currently displayed listing
        
        tiles.forEach(function(tile) {{
            tile.addEventListener('click', function() {{
                var listingId = tile.getAttribute('data-listing-id');
                var listing = JSON.parse(decodeURIComponent(tile.getAttribute('data-listing')));
                
                // Hide tile view
                container.querySelector('.realnex-tile-view').style.display = 'none';
                
                // Show detailed view
                var detailedView = container.querySelector('.realnex-detailed-view-' + listingId);
                if (detailedView) {{
                    detailedView.style.display = 'block';
                }}
                
                currentView = 'detail';
                currentListing = listingId;
                
                // Initialize carousel
                var carouselImages = detailedView.querySelectorAll('.carousel-image');
                var currentIndex = 0;
                
                function updateCarousel() {{
                    carouselImages.forEach(function(img, index) {{
                        img.style.display = index === currentIndex ? 'block' : 'none';
                    }});
                    detailedView.querySelector('.carousel-prev').style.display = carouselImages.length > 1 ? 'block' : 'none';
                    detailedView.querySelector('.carousel-next').style.display = carouselImages.length > 1 ? 'block' : 'none';
                }}
                
                detailedView.querySelector('.carousel-prev').addEventListener('click', function() {{
                    currentIndex = (currentIndex - 1 + carouselImages.length) % carouselImages.length;
                    updateCarousel();
                }});
                
                detailedView.querySelector('.carousel-next').addEventListener('click', function() {{
                    currentIndex = (currentIndex + 1) % carouselImages.length;
                    updateCarousel();
                }});
                
                updateCarousel();
            }});
        }});
        
        // Handle back button to return to tile view
        var backButtons = container.querySelectorAll('.back-to-tiles');
        backButtons.forEach(function(button) {{
            button.addEventListener('click', function() {{
                // Hide all detailed views
                container.querySelectorAll('.realnex-detailed-view').forEach(function(view) {{
                    view.style.display = 'none';
                }});
                
                // Show tile view
                container.querySelector('.realnex-tile-view').style.display = 'grid';
                
                currentView = 'tile';
                currentListing = null;
            }});
        }});
        
        // Handle form submissions with AJAX
        var forms = container.querySelectorAll('.realnex-form');
        forms.forEach(function(form) {{
            form.addEventListener('submit', function(event) {{
                event.preventDefault();
                
                // Show loading spinner
                var submitButton = form.querySelector('button[type="submit"]');
                var originalButtonText = submitButton.innerHTML;
                submitButton.innerHTML = '<span class="spinner"></span> Submitting...';
                submitButton.disabled = true;
                
                var formData = new FormData(form);
                fetch('{EMBED_URL}/submit', {{
                    method: 'POST',
                    body: formData
                }})
                .then(response => response.text())
                .then(data => {{
                    var messageDiv = document.createElement('div');
                    messageDiv.className = 'realnex-message';
                    messageDiv.setAttribute('role', 'alert');
                    if (response.ok) {{
                        messageDiv.className += ' success';
                        messageDiv.innerHTML = data;
                        form.style.display = 'none'; // Hide form on success
                    }} else {{
                        messageDiv.className += ' error';
                        messageDiv.innerHTML = data;
                    }}
                    form.parentNode.insertBefore(messageDiv, form.nextSibling);
                }})
                .catch(error => {{
                    var messageDiv = document.createElement('div');
                    messageDiv.className = 'realnex-message error';
                    messageDiv.setAttribute('role', 'alert');
                    messageDiv.innerHTML = 'An unexpected error occurred. Please try again.';
                    form.parentNode.insertBefore(messageDiv, form.nextSibling);
                }})
                .finally(() => {{
                    submitButton.innerHTML = originalButtonText;
                    submitButton.disabled = false;
                }});
            }});
        }});
    }})();
    """
    return Response(js_content, mimetype='application/javascript')

@app.route('/submit', methods=['POST'])
def submit_form():
    unique_id = request.form.get('unique_id')
    
    # Clean up expired credentials
    cleanup_expired_credentials()
    
    # Retrieve credentials from SQLite
    conn = sqlite3.connect('db/credentials.db')
    c = conn.cursor()
    c.execute("SELECT * FROM credentials WHERE unique_id = ?", (unique_id,))
    creds = c.fetchone()
    conn.close()
    
    if not unique_id or not creds:
        return "Invalid or expired session", 400
    
    expires = datetime.strptime(creds[6], '%Y-%m-%d %H:%M:%S.%f')
    if expires < datetime.now():
        conn = sqlite3.connect('db/credentials.db')
        c = conn.cursor()
        c.execute("DELETE FROM credentials WHERE unique_id = ?", (unique_id,))
        conn.commit()
        conn.close()
        return "Session expired", 400
    
    token = creds[3]
    company_id = creds[2]
    
    # Sanitize form data
    form_data = {
        'first_name': html.escape(request.form.get('realnex_first_name', '').strip()),
        'last_name': html.escape(request.form.get('realnex_last_name', '').strip()),
        'email': html.escape(request.form.get('realnex_email', '').strip()),
        'phone': html.escape(request.form.get('realnex_phone', '').strip()),
        'company': html.escape(request.form.get('realnex_company', '').strip()),
        'address': html.escape(request.form.get('realnex_address', '').strip()),
        'comments': html.escape(request.form.get('realnex_comments', '').strip()),
        'listing_key': html.escape(request.form.get('listing_key', '')),
        'listing_title': html.escape(request.form.get('listing_title', '')),
        'listing_address': html.escape(request.form.get('listing_address', ''))
    }
    
    # Validate required fields
    errors = []
    required_fields = ['first_name', 'last_name', 'email']
    for field in required_fields:
        if not form_data[field]:
            errors.append(f"{field.replace('_', ' ').title()} is required.")
    
    if not form_data['email'] or '@' not in form_data['email']:
        errors.append("Please provide a valid email address.")
    
    if errors:
        return " ".join(errors), 400
    
    # Use V1 API for CRM operations
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    if company_id:
        headers['X-Company-ID'] = company_id
    
    # Match the listing address to a project in the CRM
    project_key = None
    if form_data['listing_address']:
        try:
            response = requests.get(f"{API_BASE_URL_V1}/Crm/listings", headers=headers, timeout=5)
            if response.status_code == 200:
                projects = response.json().get('items', [])
                for project in projects:
                    project_address = project.get('address', '').lower()
                    if project_address and form_data['listing_address'].lower() in project_address:
                        project_key = project.get('key')
                        break
        except requests.RequestException as e:
            pass  # If we can't fetch projects, proceed without linking to a project
    
    # Check if contact exists
    contact_key = None
    search_url = f"{API_BASE_URL_V1}/Crm/contacts?email={form_data['email']}"
    try:
        search_response = requests.get(search_url, headers=headers, timeout=5)
        if search_response.status_code == 200:
            contacts = search_response.json().get('items', [])
            for contact in contacts:
                if (contact.get('firstName', '').lower() == form_data['first_name'].lower() and
                    contact.get('lastName', '').lower() == form_data['last_name'].lower()):
                    contact_key = contact['key']
                    break
        else:
            return f"API error searching contacts: {search_response.json().get('message', 'Unknown error')}", 500
    except requests.RequestException as e:
        return f"API request failed while searching contacts: {str(e)}", 500
    
    # Create contact if not found
    if not contact_key:
        contact_payload = {
            'firstName': form_data['first_name'],
            'lastName': form_data['last_name'],
            'email': form_data['email'],
            'phones': [{'number': form_data['phone']}] if form_data['phone'] else []
        }
        try:
            contact_response = requests.post(f"{API_BASE_URL_V1}/Crm/contact", headers=headers, json=contact_payload, timeout=5)
            if contact_response.status_code == 201:
                contact_key = contact_response.json().get('contact', {}).get('key')
            else:
                return f"API error creating contact: {contact_response.json().get('message', 'Unknown error')}", 500
        except requests.RequestException as e:
            return f"API request failed while creating contact: {str(e)}", 500
    
    # Create company if provided
    company_key = None
    if form_data['company']:
        company_payload = {
            'name': form_data['company'],
            'address1': form_data['address']
        }
        try:
            company_response = requests.post(f"{API_BASE_URL_V1}/Crm/company", headers=headers, json=company_payload, timeout=5)
            if company_response.status_code == 201:
                company_key = company_response.json().get('company', {}).get('key')
        except requests.RequestException:
            pass  # Company creation is optional
    
    # Create history note and link to project
    if contact_key:
        linked_listing_keys = [project_key] if project_key else [form_data['listing_key']] if form_data['listing_key'] else []
        history_payload = {
            'subject': f"{'Listing Inquiry: ' + form_data['listing_title'] if form_data['listing_key'] else 'Weblead'}",
            'notes': form_data['comments'] or 'Submitted via web form',
            'linkedContactKeys': [contact_key],
            'linkedCompanyKeys': [company_key] if company_key else [],
            'linkedListingKeys': linked_listing_keys,
            'eventType': 'Note'
        }
        try:
            history_response = requests.post(f"{API_BASE_URL_V1}/Crm/history", headers=headers, json=history_payload, timeout=5)
            if history_response.status_code != 201:
                return f"API error creating history note: {history_response.json().get('message', 'Unknown error')}", 500
        except requests.RequestException as e:
            return f"API request failed while creating history note: {str(e)}", 500
    
    return "Thank you! Your information has been submitted successfully.", 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
