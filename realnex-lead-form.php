<?php
/*
Plugin Name: RealNex Web Lead Form
Description: A contact form plugin that submits leads to RealNex using a stored token.
Version: 1.1
Author: Your Name
*/

if (!defined('ABSPATH')) exit;

// === Admin Settings ===
add_action('admin_menu', function () {
    add_options_page('RealNex Lead Form Settings', 'RealNex Lead Form', 'manage_options', 'realnex-lead-form', 'realnex_lead_form_settings_page');
});

function realnex_lead_form_settings_page() {
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

add_action('admin_init', function () {
    register_setting('realnex_lead_form', 'realnex_token');
    register_setting('realnex_lead_form', 'realnex_field_settings');

    add_settings_section('realnex_section', 'Form Settings', null, 'realnex-lead-form');

    add_settings_field('realnex_token', 'RealNex Token', function () {
        $value = esc_attr(get_option('realnex_token'));
        echo "<input type='text' name='realnex_token' value='$value' class='regular-text' />";
    }, 'realnex-lead-form', 'realnex_section');

    $fields = ['first_name' => 'First Name', 'last_name' => 'Last Name', 'email' => 'Email', 'phone' => 'Phone', 'comments' => 'Comments'];
    $settings = get_option('realnex_field_settings', []);

    foreach ($fields as $key => $label) {
        add_settings_field("realnex_{$key}", "$label Field", function () use ($key, $label, $settings) {
            $show = isset($settings[$key]['show']) ? 'checked' : '';
            $required = isset($settings[$key]['required']) ? 'checked' : '';
            echo "<label><input type='checkbox' name='realnex_field_settings[$key][show]' value='1' $show /> Show</label> ";
            echo "<label><input type='checkbox' name='realnex_field_settings[$key][required]' value='1' $required /> Required</label>";
        }, 'realnex-lead-form', 'realnex_section');
    }
});

// === Shortcode ===
add_shortcode('realnex_lead_form', function () {
    $settings = get_option('realnex_field_settings', []);
    ob_start();
    ?>
    <form method="post">
        <?php if (!empty($settings['first_name']['show'])): ?>
            <input name="realnex_first_name" placeholder="First Name" <?php echo !empty($settings['first_name']['required']) ? 'required' : ''; ?>><br>
        <?php endif; ?>
        <?php if (!empty($settings['last_name']['show'])): ?>
            <input name="realnex_last_name" placeholder="Last Name" <?php echo !empty($settings['last_name']['required']) ? 'required' : ''; ?>><br>
        <?php endif; ?>
        <?php if (!empty($settings['email']['show'])): ?>
            <input name="realnex_email" placeholder="Email" type="email" <?php echo !empty($settings['email']['required']) ? 'required' : ''; ?>><br>
        <?php endif; ?>
        <?php if (!empty($settings['phone']['show'])): ?>
            <input name="realnex_phone" placeholder="Phone" <?php echo !empty($settings['phone']['required']) ? 'required' : ''; ?>><br>
        <?php endif; ?>
        <?php if (!empty($settings['comments']['show'])): ?>
            <textarea name="realnex_comments" placeholder="Comments" <?php echo !empty($settings['comments']['required']) ? 'required' : ''; ?>></textarea><br>
        <?php endif; ?>
        <input type="submit" name="realnex_submit" value="Submit">
    </form>
    <?php
    return ob_get_clean();
});

// === Form Handler ===
add_action('init', function () {
    if (isset($_POST['realnex_submit'])) {
        $token = get_option('realnex_token');
        if (!$token) return;

        $data = [
            'token' => $token,
            'first_name' => sanitize_text_field($_POST['realnex_first_name'] ?? ''),
            'last_name' => sanitize_text_field($_POST['realnex_last_name'] ?? ''),
            'email' => sanitize_email($_POST['realnex_email'] ?? ''),
            'phone' => sanitize_text_field($_POST['realnex_phone'] ?? ''),
            'comments' => sanitize_textarea_field($_POST['realnex_comments'] ?? ''),
        ];

        $response = wp_remote_post('https://realnex-lead-form-api.onrender.com/submit-lead', [
            'headers' => ['Content-Type' => 'application/json'],
            'body'    => json_encode($data),
            'method'  => 'POST',
            'data_format' => 'body'
        ]);

        if (is_wp_error($response)) {
            error_log('RealNex API error: ' . $response->get_error_message());
        } else {
            $code = wp_remote_retrieve_response_code($response);
            if ($code == 200) {
                add_action('wp_footer', function () {
                    echo "<script>alert('Your information has been submitted!');</script>";
                });
            } else {
                error_log('RealNex API error: ' . wp_remote_retrieve_body($response));
            }
        }
    }
});
