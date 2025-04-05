<?php
/*
Plugin Name: RealNex Web Lead Form
Description: A contact form plugin that submits leads to RealNex using a stored token.
Version: 2.0
Author: Your Name
*/

if (!defined('ABSPATH')) exit;

class RealNex_Lead_Form {
    private $options;
    
    public function __construct() {
        // Initialize plugin
        add_action('admin_menu', array($this, 'add_admin_menu'));
        add_action('admin_init', array($this, 'register_settings'));
        add_action('wp_enqueue_scripts', array($this, 'enqueue_scripts'));
        
        // Register shortcode
        add_shortcode('realnex_lead_form', array($this, 'render_form'));
        
        // Form processing
        add_action('init', array($this, 'process_form_submission'));
        
        // Load options
        $this->options = get_option('realnex_lead_form_options', array(
            'token' => '',
            'recaptcha_site_key' => '',
            'recaptcha_secret_key' => '',
            'success_message' => 'Thank you! Your information has been submitted successfully.',
            'field_settings' => array(
                'first_name' => array('show' => 1, 'required' => 1),
                'last_name' => array('show' => 1, 'required' => 1),
                'email' => array('show' => 1, 'required' => 1),
                'phone' => array('show' => 1, 'required' => 0),
                'company' => array('show' => 1, 'required' => 0),
                'address' => array('show' => 1, 'required' => 0),
                'comments' => array('show' => 1, 'required' => 0)
            )
        ));
    }
    
    // === Admin Methods ===
    
    public function add_admin_menu() {
        add_options_page(
            'RealNex Lead Form Settings',
            'RealNex Lead Form',
            'manage_options',
            'realnex-lead-form',
            array($this, 'render_settings_page')
        );
    }
    
    public function register_settings() {
        register_setting('realnex_lead_form', 'realnex_lead_form_options', array($this, 'sanitize_options'));
        
        add_settings_section(
            'realnex_api_section',
            'API Settings',
            null,
            'realnex-lead-form'
        );
        
        add_settings_field(
            'realnex_token',
            'RealNex API Token',
            array($this, 'token_field_callback'),
            'realnex-lead-form',
            'realnex_api_section'
        );
        
        add_settings_field(
            'recaptcha_settings',
            'reCAPTCHA Settings',
            array($this, 'recaptcha_fields_callback'),
            'realnex-lead-form',
            'realnex_api_section'
        );
        
        add_settings_field(
            'success_message',
            'Success Message',
            array($this, 'success_message_callback'),
            'realnex-lead-form',
            'realnex_api_section'
        );
        
        add_settings_section(
            'realnex_field_section',
            'Form Fields Settings',
            null,
            'realnex-lead-form'
        );
        
        $fields = array(
            'first_name' => 'First Name',
            'last_name' => 'Last Name',
            'email' => 'Email',
            'phone' => 'Phone',
            'company' => 'Company',
            'address' => 'Address',
            'comments' => 'Comments'
        );
        
        foreach ($fields as $key => $label) {
            add_settings_field(
                "realnex_field_{$key}",
                $label,
                array($this, 'field_settings_callback'),
                'realnex-lead-form',
                'realnex_field_section',
                array('key' => $key, 'label' => $label)
            );
        }
    }
    
    public function sanitize_options($input) {
        $sanitary_values = array();
        
        if (isset($input['token'])) {
            $sanitary_values['token'] = sanitize_text_field($input['token']);
        }
        
        if (isset($input['recaptcha_site_key'])) {
            $sanitary_values['recaptcha_site_key'] = sanitize_text_field($input['recaptcha_site_key']);
        }
        
        if (isset($input['recaptcha_secret_key'])) {
            $sanitary_values['recaptcha_secret_key'] = sanitize_text_field($input['recaptcha_secret_key']);
        }
        
        if (isset($input['success_message'])) {
            $sanitary_values['success_message'] = wp_kses_post($input['success_message']);
        }
        
        if (isset($input['field_settings'])) {
            $sanitary_values['field_settings'] = array();
            foreach ($input['field_settings'] as $key => $settings) {
                $sanitary_values['field_settings'][$key] = array(
                    'show' => isset($settings['show']) ? 1 : 0,
                    'required' => isset($settings['required']) ? 1 : 0
                );
            }
        }
        
        return $sanitary_values;
    }
    
    public function token_field_callback() {
        $value = isset($this->options['token']) ? esc_attr($this->options['token']) : '';
        echo '<input type="text" name="realnex_lead_form_options[token]" value="' . $value . '" class="regular-text">';
        echo '<p class="description">Enter your RealNex API token</p>';
    }
    
    public function recaptcha_fields_callback() {
        $site_key = isset($this->options['recaptcha_site_key']) ? esc_attr($this->options['recaptcha_site_key']) : '';
        $secret_key = isset($this->options['recaptcha_secret_key']) ? esc_attr($this->options['recaptcha_secret_key']) : '';
        
        echo '<label>Site Key:<br />';
        echo '<input type="text" name="realnex_lead_form_options[recaptcha_site_key]" value="' . $site_key . '" class="regular-text"></label>';
        echo '<br /><br />';
        echo '<label>Secret Key:<br />';
        echo '<input type="text" name="realnex_lead_form_options[recaptcha_secret_key]" value="' . $secret_key . '" class="regular-text"></label>';
        echo '<p class="description">Enter your Google reCAPTCHA v2 keys. Leave empty to disable reCAPTCHA.</p>';
    }
    
    public function success_message_callback() {
        $value = isset($this->options['success_message']) ? esc_attr($this->options['success_message']) : '';
        echo '<textarea name="realnex_lead_form_options[success_message]" class="large-text" rows="3">' . $value . '</textarea>';
        echo '<p class="description">Message to display after successful form submission</p>';
    }
    
    public function field_settings_callback($args) {
        $key = $args['key'];
        $settings = isset($this->options['field_settings'][$key]) ? $this->options['field_settings'][$key] : array('show' => 0, 'required' => 0);
        
        $show = isset($settings['show']) && $settings['show'] ? 'checked' : '';
        $required = isset($settings['required']) && $settings['required'] ? 'checked' : '';
        
        echo '<label><input type="checkbox" name="realnex_lead_form_options[field_settings][' . $key . '][show]" value="1" ' . $show . '> Show</label> ';
        echo '<label><input type="checkbox" name="realnex_lead_form_options[field_settings][' . $key . '][required]" value="1" ' . $required . '> Required</label>';
    }
    
    public function render_settings_page() {
        ?>
        <div class="wrap">
            <h1>RealNex Lead Form Settings</h1>
            <form method="post" action="options.php">
                <?php
                settings_fields('realnex_lead_form');
                do_settings_sections('realnex-lead-form');
                submit_button();
                ?>
            </form>
        </div>
        <?php
    }
    
    // === Frontend Methods ===
    
    public function enqueue_scripts() {
        wp_enqueue_style('realnex-form-styles', plugins_url('css/form.css', __FILE__));
        
        // Only load reCAPTCHA if configured
        if (!empty($this->options['recaptcha_site_key'])) {
            wp_enqueue_script('google-recaptcha', 'https://www.google.com/recaptcha/api.js', array(), null, true);
        }
    }
    
    public function render_form() {
        // Create nonce for security
        $nonce = wp_create_nonce('realnex_lead_form_nonce');
        
        $field_settings = isset($this->options['field_settings']) ? $this->options['field_settings'] : array();
        $recaptcha_site_key = isset($this->options['recaptcha_site_key']) ? $this->options['recaptcha_site_key'] : '';
        
        // Check for form submission result messages
        $form_message = '';
        if (isset($_GET['realnex_status'])) {
            if ($_GET['realnex_status'] === 'success') {
                $message = isset($this->options['success_message']) ? $this->options['success_message'] : 'Thank you! Your information has been submitted.';
                $form_message = '<div class="realnex-form-message realnex-success">' . esc_html($message) . '</div>';
            } elseif ($_GET['realnex_status'] === 'error') {
                $error_message = isset($_GET['message']) ? urldecode($_GET['message']) : 'There was an error submitting your information.';
                $form_message = '<div class="realnex-form-message realnex-error">' . esc_html($error_message) . '</div>';
            }
        }
        
        // Start building the form HTML
        ob_start();
        ?>
        <div class="realnex-form-container">
            <?php echo $form_message; ?>
            
            <form id="realnex-lead-form" method="post" class="realnex-form">
                <input type="hidden" name="realnex_form_submitted" value="1">
                <input type="hidden" name="realnex_nonce" value="<?php echo $nonce; ?>">
                
                <div class="realnex-form-fields">
                    <?php if (!empty($field_settings['first_name']['show'])): ?>
                        <div class="realnex-form-field">
                            <input type="text" name="realnex_first_name" placeholder="First Name" <?php echo !empty($field_settings['first_name']['required']) ? 'required' : ''; ?>>
                        </div>
                    <?php endif; ?>
                    
                    <?php if (!empty($field_settings['last_name']['show'])): ?>
                        <div class="realnex-form-field">
                            <input type="text" name="realnex_last_name" placeholder="Last Name" <?php echo !empty($field_settings['last_name']['required']) ? 'required' : ''; ?>>
                        </div>
                    <?php endif; ?>
                    
                    <?php if (!empty($field_settings['email']['show'])): ?>
                        <div class="realnex-form-field">
                            <input type="email" name="realnex_email" placeholder="Email" <?php echo !empty($field_settings['email']['required']) ? 'required' : ''; ?>>
                        </div>
                    <?php endif; ?>
                    
                    <?php if (!empty($field_settings['phone']['show'])): ?>
                        <div class="realnex-form-field">
                            <input type="tel" name="realnex_phone" placeholder="Phone" <?php echo !empty($field_settings['phone']['required']) ? 'required' : ''; ?>>
                        </div>
                    <?php endif; ?>
                    
                    <?php if (!empty($field_settings['company']['show'])): ?>
                        <div class="realnex-form-field">
                            <input type="text" name="realnex_company" placeholder="Company" <?php echo !empty($field_settings['company']['required']) ? 'required' : ''; ?>>
                        </div>
                    <?php endif; ?>
                    
                    <?php if (!empty($field_settings['address']['show'])): ?>
                        <div class="realnex-form-field">
                            <input type="text" name="realnex_address" placeholder="Address" <?php echo !empty($field_settings['address']['required']) ? 'required' : ''; ?>>
                        </div>
                    <?php endif; ?>
                    
                    <?php if (!empty($field_settings['comments']['show'])): ?>
                        <div class="realnex-form-field">
                            <textarea name="realnex_comments" placeholder="Comments" <?php echo !empty($field_settings['comments']['required']) ? 'required' : ''; ?>></textarea>
                        </div>
                    <?php endif; ?>
                    
                    <?php if (!empty($recaptcha_site_key)): ?>
                        <div class="realnex-form-field realnex-recaptcha">
                            <div class="g-recaptcha" data-sitekey="<?php echo esc_attr($recaptcha_site_key); ?>"></div>
                        </div>
                    <?php endif; ?>
                    
                    <div class="realnex-form-field realnex-submit">
                        <button type="submit" name="realnex_submit">Submit</button>
                    </div>
                </div>
            </form>
        </div>
        <?php
        return ob_get_clean();
    }
    
    // === Form Processing ===
    
    public function process_form_submission() {
        if (!isset($_POST['realnex_form_submitted']) || !isset($_POST['realnex_nonce'])) {
            return;
        }
        
        // Verify nonce
        if (!wp_verify_nonce($_POST['realnex_nonce'], 'realnex_lead_form_nonce')) {
            $this->redirect_with_error('Security verification failed.');
            return;
        }
        
        // Get options
        $token = isset($this->options['token']) ? $this->options['token'] : '';
        $recaptcha_secret = isset($this->options['recaptcha_secret_key']) ? $this->options['recaptcha_secret_key'] : '';
        
        if (empty($token)) {
            $this->redirect_with_error('API token not configured.');
            return;
        }
        
        // Verify reCAPTCHA if enabled
        if (!empty($recaptcha_secret)) {
            $recaptcha_response = isset($_POST['g-recaptcha-response']) ? $_POST['g-recaptcha-response'] : '';
            
            if (empty($recaptcha_response)) {
                $this->redirect_with_error('Please complete the reCAPTCHA.');
                return;
            }
            
            $recaptcha_verify = wp_remote_post('https://www.google.com/recaptcha/api/siteverify', array(
                'body' => array(
                    'secret' => $recaptcha_secret,
                    'response' => $recaptcha_response
                )
            ));
            
            if (is_wp_error($recaptcha_verify)) {
                $this->redirect_with_error('reCAPTCHA verification failed.');
                return;
            }
            
            $recaptcha_result = json_decode(wp_remote_retrieve_body($recaptcha_verify), true);
            
            if (!isset($recaptcha_result['success']) || !$recaptcha_result['success']) {
                $this->redirect_with_error('reCAPTCHA verification failed.');
                return;
            }
        }
        
        // Sanitize form data
        $form_data = array(
            'first_name' => sanitize_text_field($_POST['realnex_first_name'] ?? ''),
            'last_name' => sanitize_text_field($_POST['realnex_last_name'] ?? ''),
            'email' => sanitize_email($_POST['realnex_email'] ?? ''),
            'phone' => sanitize_text_field($_POST['realnex_phone'] ?? ''),
            'company' => sanitize_text_field($_POST['realnex_company'] ?? ''),
            'address' => sanitize_text_field($_POST['realnex_address'] ?? ''),
            'comments' => sanitize_textarea_field($_POST['realnex_comments'] ?? '')
        );
        
        // Basic validation
        if (empty($form_data['email']) || !is_email($form_data['email'])) {
            $this->redirect_with_error('Please provide a valid email address.');
            return;
        }
        
        // Send data to RealNex API
        $headers = array(
            'Authorization' => 'Bearer ' . $token,
            'Content-Type' => 'application/json'
        );
        
        // First check if contact exists
        $contact_key = null;
        $search_url = 'https://sync.realnex.com/api/v1/Crm/contacts?email=' . urlencode($form_data['email']);
        
        $search_response = wp_remote_get($search_url, array(
            'headers' => $headers
        ));
        
        if (!is_wp_error($search_response)) {
            $search_body = json_decode(wp_remote_retrieve_body($search_response), true);
            
            if (isset($search_body['items']) && is_array($search_body['items'])) {
                foreach ($search_body['items'] as $contact) {
                    if (strtolower($contact['firstName']) == strtolower($form_data['first_name']) && 
                        strtolower($contact['lastName']) == strtolower($form_data['last_name'])) {
                        $contact_key = $contact['key'];
                        break;
                    }
                }
            }
        }
        
        // Create contact if not found
        if (!$contact_key) {
            $contact_payload = array(
                'firstName' => $form_data['first_name'],
                'lastName' => $form_data['last_name'],
                'email' => $form_data['email'],
                'phones' => !empty($form_data['phone']) ? array(array('number' => $form_data['phone'])) : array()
            );
            
            $contact_response = wp_remote_post('https://sync.realnex.com/api/v1/Crm/contact', array(
                'headers' => $headers,
                'body' => json_encode($contact_payload)
            ));
            
            if (!is_wp_error($contact_response)) {
                $contact_body = json_decode(wp_remote_retrieve_body($contact_response), true);
                if (isset($contact_body['contact']['key'])) {
                    $contact_key = $contact_body['contact']['key'];
                }
            }
        }
        
        // Create company if provided
        $company_key = null;
        if (!empty($form_data['company'])) {
            $company_payload = array(
                'name' => $form_data['company'],
                'address1' => $form_data['address']
            );
            
            $company_response = wp_remote_post('https://sync.realnex.com/api/v1/Crm/company', array(
                'headers' => $headers,
                'body' => json_encode($company_payload)
            ));
            
            if (!is_wp_error($company_response)) {
                $company_body = json_decode(wp_remote_retrieve_body($company_response), true);
                if (isset($company_body['company']['key'])) {
                    $company_key = $company_body['company']['key'];
                }
            }
        }
        
        // Create history note
        if ($contact_key) {
            $history_payload = array(
                'subject' => 'Weblead',
                'notes' => !empty($form_data['comments']) ? $form_data['comments'] : 'Submitted via web form',
                'linkedContactKeys' => array($contact_key),
                'linkedCompanyKeys' => $company_key ? array($company_key) : array(),
                'eventType' => 'Note'
            );
            
            $history_response = wp_remote_post('https://sync.realnex.com/api/v1/Crm/history', array(
                'headers' => $headers,
                'body' => json_encode($history_payload)
            ));
            
            if (is_wp_error($history_response)) {
                $this->redirect_with_error('Error creating history note.');
                return;
            }
        } else {
            $this->redirect_with_error('Failed to create or find contact.');
            return;
        }
        
        // Redirect to success page
        $redirect_url = add_query_arg('realnex_status', 'success', wp_get_referer());
        wp_redirect($redirect_url);
        exit;
    }
    
    private function redirect_with_error($message) {
        $redirect_url = add_query_arg(
            array(
                'realnex_status' => 'error',
                'message' => urlencode($message)
            ),
            wp_get_referer()
        );
        
        wp_redirect($redirect_url);
        exit;
    }
}

// CSS file content for the form
function realnex_create_css_file() {
    $css_dir = plugin_dir_path(__FILE__) . 'css';
    
    if (!file_exists($css_dir)) {
        mkdir($css_dir, 0755, true);
    }
    
    $css_file = $css_dir . '/form.css';
    
    if (!file_exists($css_file)) {
        $css_content = "
        .realnex-form-container {
            font-family: Arial, sans-serif;
            max-width: 500px;
            margin: 0 auto;
            padding: 20px;
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        
        .realnex-form {
            width: 100%;
        }
        
        .realnex-form-field {
            margin-bottom: 15px;
        }
        
        .realnex-form input[type='text'],
        .realnex-form input[type='email'],
        .realnex-form input[type='tel'],
        .realnex-form textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-sizing: border-box;
            font-size: 14px;
        }
        
        .realnex-form textarea {
            height: 100px;
            resize: vertical;
        }
        
        .realnex-form button {
            width: 100%;
            padding: 12px;
            border: none;
            background-color: #007BFF;
            color: white;
            font-size: 16px;
            font-weight: bold;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        
        .realnex-form button:hover {
            background-color: #0056b3;
        }
        
        .realnex-recaptcha {
            margin-bottom: 20px;
        }
        
        .realnex-form-message {
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
        }
        
        .realnex-success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .realnex-error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        ";
        
        file_put_contents($css_file, $css_content);
    }
}

// Initialize plugin
function realnex_lead_form_init() {
    $realnex_form = new RealNex_Lead_Form();
    
    // Register activation hook
    register_activation_hook(__FILE__, 'realnex_create_css_file');
}

realnex_lead_form_init();