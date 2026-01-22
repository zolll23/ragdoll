<?php

namespace App\Repositories;

use App\Models\User;
use PDO;

/**
 * User repository for database operations
 * Demonstrates N+1 queries, SQL injection risks, and coupling
 */
class UserRepository
{
    private PDO $db;
    
    public function __construct(PDO $db)
    {
        $this->db = $db;
    }
    
    /**
     * Find user by ID
     * Safe - uses prepared statements
     */
    public function findById(int $id): ?User
    {
        $stmt = $this->db->prepare("SELECT * FROM users WHERE id = :id");
        $stmt->execute(['id' => $id]);
        $data = $stmt->fetch(PDO::FETCH_ASSOC);
        
        if (!$data) {
            return null;
        }
        
        return new User($data['id'], $data['name'], $data['email']);
    }
    
    /**
     * Find users by name - VULNERABLE to SQL injection
     * Demonstrates security issue
     */
    public function findByNameUnsafe(string $name): array
    {
        // SECURITY ISSUE: Direct string interpolation
        $query = "SELECT * FROM users WHERE name = '$name'";
        $stmt = $this->db->query($query);
        return $stmt->fetchAll(PDO::FETCH_ASSOC);
    }
    
    /**
     * Find users with roles - N+1 query problem
     * Demonstrates N+1 query detection
     */
    public function findUsersWithRoles(array $userIds): array
    {
        $users = [];
        
        // N+1 Problem: Query for each user
        foreach ($userIds as $userId) {
            $user = $this->findById($userId);
            if ($user) {
                // Another query for roles (N+1)
                $stmt = $this->db->prepare("SELECT role FROM user_roles WHERE user_id = :id");
                $stmt->execute(['id' => $userId]);
                $roles = $stmt->fetchAll(PDO::FETCH_COLUMN);
                
                foreach ($roles as $role) {
                    $user->addRole($role);
                }
                
                $users[] = $user;
            }
        }
        
        return $users;
    }
    
    /**
     * Find users with roles - OPTIMIZED
     * Single query with JOIN
     */
    public function findUsersWithRolesOptimized(array $userIds): array
    {
        $placeholders = implode(',', array_fill(0, count($userIds), '?'));
        $query = "SELECT u.*, ur.role 
                  FROM users u 
                  LEFT JOIN user_roles ur ON u.id = ur.user_id 
                  WHERE u.id IN ($placeholders)";
        
        $stmt = $this->db->prepare($query);
        $stmt->execute($userIds);
        
        $users = [];
        $userMap = [];
        
        while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
            if (!isset($userMap[$row['id']])) {
                $user = new User($row['id'], $row['name'], $row['email']);
                $userMap[$row['id']] = $user;
                $users[] = $user;
            }
            
            if ($row['role']) {
                $userMap[$row['id']]->addRole($row['role']);
            }
        }
        
        return $users;
    }
    
    /**
     * Save user - demonstrates transaction
     */
    public function save(User $user): bool
    {
        try {
            $this->db->beginTransaction();
            
            $stmt = $this->db->prepare(
                "INSERT INTO users (name, email) VALUES (:name, :email)"
            );
            $stmt->execute([
                'name' => $user->getName(),
                'email' => $user->getEmail()
            ]);
            
            $this->db->commit();
            return true;
        } catch (\Exception $e) {
            $this->db->rollBack();
            return false;
        }
    }
}



