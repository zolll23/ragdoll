<?php

namespace App\Services;

use App\Models\User;

/**
 * Email service - demonstrates cohesion
 */
class EmailService
{
    /**
     * Email sending timeout in seconds
     * Maximum time to wait for email delivery before considering it failed
     * Default: 30 seconds
     */
    const EMAIL_SEND_TIMEOUT = 30;
    
    /**
     * Maximum retry attempts for failed email sends
     * Number of times to retry sending an email if it fails
     */
    const MAX_EMAIL_RETRIES = 3;
    
    /**
     * SMTP connection timeout in seconds
     * Time to wait when connecting to SMTP server
     */
    const SMTP_CONNECTION_TIMEOUT = 10;
    
    /**
     * Maximum email body size in bytes
     * Emails larger than this will be rejected
     * Default: 10485760 bytes (10 MB)
     */
    const MAX_EMAIL_SIZE = 10485760; // 10 MB
    
    /**
     * Send welcome email
     * Simple method - high cohesion
     */
    public function sendWelcomeEmail(User $user): bool
    {
        $subject = "Welcome, {$user->getName()}!";
        $body = "Thank you for registering.";
        
        return $this->sendEmail($user->getEmail(), $subject, $body);
    }
    
    /**
     * Send email - VULNERABLE to XSS if used in HTML context
     */
    public function sendEmail(string $to, string $subject, string $body): bool
    {
        // SECURITY ISSUE: No HTML escaping if used in HTML emails
        // $body could contain <script> tags
        
        // In real implementation, would use mail() or SMTP
        return true;
    }
    
    /**
     * Send email with HTML - safe version
     */
    public function sendHtmlEmail(string $to, string $subject, string $htmlBody): bool
    {
        // Safe: HTML is properly escaped
        $safeBody = htmlspecialchars($htmlBody, ENT_QUOTES, 'UTF-8');
        
        return $this->sendEmail($to, $subject, $safeBody);
    }
}


