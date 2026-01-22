<?php

namespace App\Models;

/**
 * User model representing a user entity
 * This class demonstrates various metrics
 */
class User
{
    private int $id;
    private string $name;
    private string $email;
    private array $roles;
    
    // Constants
    const STATUS_ACTIVE = 'active';
    const STATUS_INACTIVE = 'inactive';
    const MAX_LOGIN_ATTEMPTS = 5;
    
    public function __construct(int $id, string $name, string $email)
    {
        $this->id = $id;
        $this->name = $name;
        $this->email = $email;
        $this->roles = [];
    }
    
    /**
     * Get user ID
     * Simple getter - O(1) complexity
     */
    public function getId(): int
    {
        return $this->id;
    }
    
    /**
     * Get user name
     */
    public function getName(): string
    {
        return $this->name;
    }
    
    /**
     * Validate user email
     * Demonstrates cyclomatic complexity
     */
    public function isValidEmail(): bool
    {
        if (empty($this->email)) {
            return false;
        }
        
        if (!filter_var($this->email, FILTER_VALIDATE_EMAIL)) {
            return false;
        }
        
        $parts = explode('@', $this->email);
        if (count($parts) !== 2) {
            return false;
        }
        
        return true;
    }
    
    /**
     * Check if user has role
     * O(n) complexity - linear search
     */
    public function hasRole(string $role): bool
    {
        foreach ($this->roles as $userRole) {
            if ($userRole === $role) {
                return true;
            }
        }
        return false;
    }
    
    /**
     * Add role to user
     * Simple operation
     */
    public function addRole(string $role): void
    {
        if (!$this->hasRole($role)) {
            $this->roles[] = $role;
        }
    }
}


