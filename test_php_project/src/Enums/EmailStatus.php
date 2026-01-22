<?php

namespace App\Enums;

/**
 * Email delivery status enumeration
 * Represents the current state of an email in the delivery process
 */
enum EmailStatus: string
{
    /**
     * Email is queued and waiting to be sent
     * Initial state when email is created
     */
    case PENDING = 'pending';
    
    /**
     * Email is currently being sent
     * In progress state during SMTP transmission
     */
    case SENDING = 'sending';
    
    /**
     * Email was successfully delivered
     * Final state indicating successful delivery to recipient
     */
    case DELIVERED = 'delivered';
    
    /**
     * Email delivery failed
     * Final state indicating failure (bounce, timeout, etc.)
     */
    case FAILED = 'failed';
    
    /**
     * Email delivery was cancelled
     * User or system cancelled the email before sending
     */
    case CANCELLED = 'cancelled';
}


