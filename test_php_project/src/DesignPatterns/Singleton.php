<?php

namespace App\DesignPatterns;

/**
 * Singleton pattern implementation
 * Demonstrates design pattern detection
 */
class Singleton
{
    private static ?Singleton $instance = null;
    
    private function __construct()
    {
        // Private constructor
    }
    
    /**
     * Get singleton instance
     */
    public static function getInstance(): Singleton
    {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        
        return self::$instance;
    }
    
    /**
     * Prevent cloning
     */
    private function __clone() {}
    
    /**
     * Prevent unserialization
     */
    public function __wakeup()
    {
        throw new \Exception("Cannot unserialize singleton");
    }
}



