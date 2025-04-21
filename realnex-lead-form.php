<?php
/*
Plugin Name: RealNex Lead Form
Description: Embeds RealNex lead forms in WordPress using iframe snippets.
Version: 1.0
Author: Your Name
*/

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

// Register shortcode
function realnex_lead_form_shortcode($atts) {
    $atts = shortcode_atts(
        array(
            'token' => '',
            'company_id' => '',
            'type' => 'contact_us',
        ),
        $atts,
        'realnex_lead_form'
    );

    // Get default settings
    $default_token = get_option('realnex_default_token', '');
    $default_company_id = get_option('realnex_default_company_id', '');
    $token = !empty($atts['token']) ? $atts['token'] : $default_token;
    $company_id = !empty($atts['company_id']) ? $atts['company_id'] : $default_company_id;

    // Validate inputs
    if (empty($token)) {
        return '<p>Error: RealNex token is required.</p>';
    }
    if ($atts['type'] === 'listings_contact_us' && empty($company_id)) {
        return '<p>Error: Company ID is required for Listings + Contact Us.</p>';
    }

    // Build iframe URL
    $iframe_url = 'https://realnex-lead-form-api.onrender.com/snippet?snippet_type=' . ($atts['type'] === 'contact_us' ? 'contact' : 'listing');
    $iframe_url .= '&token=' . esc_attr($token);
    if ($atts['type'] === 'listings_contact_us' && $company_id) {
        $iframe_url .= '&company_id=' . esc_attr($company_id);
    }

    // Return iframe
    return '<iframe src="' . esc_url($iframe_url) . '" width="100%" height="600" frameborder="0" style="border:0;"></iframe>';
}
add_shortcode('realnex_lead_form', 'realnex_lead_form_shortcode');

// Add settings page
function realnex_register_settings() {
    add_options_page(
        'RealNex Lead Form Settings',
        'RealNex Lead Form',
        'manage_options',
        'realnex-lead-form',
        'realnex_settings_page'
    );
}
add_action('admin_menu', 'realnex_register_settings');

function realnex_settings_page() {
    ?>
    <div class="wrap">
        <h1>RealNex Lead Form Settings</h1>
        <form method="post" action="options.php">
            <?php
            settings_fields('realnex_settings');
            do_settings_sections('realnex_settings');
            ?>
            <table class="form-table">
                <tr>
                    <th><label for="realnex_default_token">Default Token</label></th>
                    <td><input type="text" name="realnex_default_token" value="<?php echo esc_attr(get_option('realnex_default_token')); ?>" class="regular-text"></td>
                </tr>
                <tr>
                    <th><label for="realnex_default_company_id">Default Company ID</label></th>
                    <td><input type="text" name="realnex_default_company_id" value="<?php echo esc_attr(get_option('realnex_default_company_id')); ?>" class="regular-text"></td>
                </tr>
            </table>
            <?php submit_button(); ?>
        </form>
    </div>
    <?php
}

function realnex_register_options() {
    register_setting('realnex_settings', 'realnex_default_token', 'sanitize_text_field');
    register_setting('realnex_settings', 'realnex_default_company_id', 'sanitize_text_field');
}
add_action('admin_init', 'realnex_register_options');
