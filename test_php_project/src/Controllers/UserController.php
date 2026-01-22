<?php

namespace App\Controllers;

use App\Services\UserService;
use App\Models\User;

/**
 * User controller - MVC role: Controller
 * Demonstrates controller pattern and dependency injection
 */
class UserController
{
    private UserService $userService;
    
    public function __construct(UserService $userService)
    {
        $this->userService = $userService;
    }
    
    /**
     * Create user endpoint
     * MVC: Controller method
     */
    public function create(array $requestData): array
    {
        $name = $requestData['name'] ?? '';
        $email = $requestData['email'] ?? '';
        $password = $requestData['password'] ?? '';
        
        $user = $this->userService->registerUser($name, $email, $password);
        
        if ($user) {
            return [
                'success' => true,
                'user' => [
                    'id' => $user->getId(),
                    'name' => $user->getName()
                ]
            ];
        }
        
        return ['success' => false, 'error' => 'Failed to create user'];
    }
    
    /**
     * Get user endpoint
     */
    public function show(int $userId): array
    {
        $userInfo = $this->userService->getUserInfo($userId);
        
        return [
            'success' => true,
            'user' => $userInfo
        ];
    }
    
    /**
     * Update user action
     */
    public function update(int $userId, array $requestData): array
    {
        $action = $requestData['action'] ?? '';
        $params = $requestData['params'] ?? [];
        
        $result = $this->userService->processUserAction($userId, $action, $params);
        
        return [
            'success' => $result
        ];
    }
}



