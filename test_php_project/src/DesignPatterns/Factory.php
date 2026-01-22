<?php

namespace App\DesignPatterns;

use App\Models\User;

/**
 * Factory pattern for creating users
 * Demonstrates Factory design pattern
 */
class UserFactory
{
    /**
     * Create user from array data
     */
    public static function create(array $data): User
    {
        return new User(
            $data['id'] ?? 0,
            $data['name'] ?? '',
            $data['email'] ?? ''
        );
    }
    
    /**
     * Create admin user
     */
    public static function createAdmin(string $name, string $email): User
    {
        $user = new User(0, $name, $email);
        $user->addRole('admin');
        return $user;
    }
}



