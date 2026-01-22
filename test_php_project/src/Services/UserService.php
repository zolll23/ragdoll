<?php

namespace App\Services;

use App\Models\User;
use App\Repositories\UserRepository;
use App\Services\EmailService;
use App\Services\NotificationService;

/**
 * User service - demonstrates coupling, cohesion, and SOLID violations
 * This is a "God Object" - does too many things
 */
class UserService
{
    private UserRepository $userRepository;
    private EmailService $emailService;
    private NotificationService $notificationService;
    
    // Hardcoded secret - SECURITY ISSUE
    private string $apiKey = 'sk_live_1234567890abcdef';
    
    public function __construct(
        UserRepository $userRepository,
        EmailService $emailService,
        NotificationService $notificationService
    ) {
        $this->userRepository = $userRepository;
        $this->emailService = $emailService;
        $this->notificationService = $notificationService;
    }
    
    /**
     * Register new user
     * High complexity - multiple responsibilities
     */
    public function registerUser(
        string $name,
        string $email,
        string $password,
        array $roles = [],
        bool $sendWelcomeEmail = true,
        bool $notifyAdmin = false
    ): ?User {
        // Validate input
        if (empty($name) || empty($email) || empty($password)) {
            return null;
        }
        
        // Create user
        $user = new User(0, $name, $email);
        
        // Validate email
        if (!$user->isValidEmail()) {
            return null;
        }
        
        // Save to database
        if (!$this->userRepository->save($user)) {
            return null;
        }
        
        // Add roles
        foreach ($roles as $role) {
            $user->addRole($role);
        }
        
        // Send welcome email
        if ($sendWelcomeEmail) {
            $this->emailService->sendWelcomeEmail($user);
        }
        
        // Notify admin
        if ($notifyAdmin) {
            $this->notificationService->notifyAdmin($user);
        }
        
        return $user;
    }
    
    /**
     * Complex method with high cyclomatic complexity
     * Demonstrates nesting depth and cognitive complexity
     */
    public function processUserAction(int $userId, string $action, array $params = []): bool
    {
        $user = $this->userRepository->findById($userId);
        
        if (!$user) {
            return false;
        }
        
        switch ($action) {
            case 'activate':
                if ($user->hasRole('admin')) {
                    if (isset($params['force'])) {
                        return $this->activateUser($user, true);
                    } else {
                        return $this->activateUser($user, false);
                    }
                } else {
                    if (isset($params['approval'])) {
                        return $this->requestApproval($user);
                    } else {
                        return false;
                    }
                }
                break;
                
            case 'deactivate':
                if ($user->hasRole('admin')) {
                    return $this->deactivateUser($user);
                } else {
                    return false;
                }
                break;
                
            case 'update':
                if (isset($params['name'])) {
                    if (strlen($params['name']) > 0) {
                        if (strlen($params['name']) <= 100) {
                            return $this->updateUserName($user, $params['name']);
                        }
                    }
                }
                break;
                
            default:
                return false;
        }
        
        return false;
    }
    
    /**
     * Feature Envy - uses too many methods from User
     */
    public function getUserInfo(int $userId): array
    {
        $user = $this->userRepository->findById($userId);
        
        // Feature Envy: accessing many User properties/methods
        return [
            'id' => $user->getId(),
            'name' => $user->getName(),
            'hasAdminRole' => $user->hasRole('admin'),
            'hasUserRole' => $user->hasRole('user'),
            'isValidEmail' => $user->isValidEmail(),
        ];
    }
    
    /**
     * Long parameter list - code smell
     */
    public function createUserWithManyParams(
        string $firstName,
        string $lastName,
        string $email,
        string $phone,
        string $address,
        string $city,
        string $country,
        string $zipCode,
        array $preferences,
        bool $newsletter,
        bool $marketing
    ): ?User {
        $name = "$firstName $lastName";
        return $this->registerUser($name, $email, 'default_password');
    }
    
    private function activateUser(User $user, bool $force): bool
    {
        // Implementation
        return true;
    }
    
    private function deactivateUser(User $user): bool
    {
        // Implementation
        return true;
    }
    
    private function requestApproval(User $user): bool
    {
        // Implementation
        return true;
    }
    
    private function updateUserName(User $user, string $name): bool
    {
        // Implementation
        return true;
    }
}



