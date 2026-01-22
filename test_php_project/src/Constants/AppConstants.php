<?php

namespace App\Constants;

/**
 * Application-wide constants
 * Centralized configuration values used throughout the application
 */
class AppConstants
{
    /**
     * Default session timeout in seconds
     * How long a user session remains active without activity
     * Default: 3600 seconds (1 hour)
     */
    const SESSION_TIMEOUT = 3600;
    
    /**
     * Maximum login attempts before account lockout
     * Number of failed login attempts allowed before temporary lockout
     */
    const MAX_LOGIN_ATTEMPTS = 5;
    
    /**
     * Account lockout duration in seconds
     * How long an account is locked after exceeding max login attempts
     * Default: 1800 seconds (30 minutes)
     */
    const LOCKOUT_DURATION = 1800;
    
    /**
     * Password minimum length requirement
     * Minimum number of characters required for user passwords
     */
    const MIN_PASSWORD_LENGTH = 8;
    
    /**
     * API rate limit per minute
     * Maximum number of API requests allowed per minute per user
     */
    const API_RATE_LIMIT = 60;
    
    /**
     * File upload maximum size in bytes
     * Maximum size for uploaded files (10 MB)
     */
    const MAX_UPLOAD_SIZE = 10485760;
    
    /**
     * Cache TTL (Time To Live) in seconds
     * How long cached data remains valid before refresh
     * Default: 300 seconds (5 minutes)
     */
    const CACHE_TTL = 300;
}


