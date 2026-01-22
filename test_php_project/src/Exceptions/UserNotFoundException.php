<?php

namespace App\Exceptions;

use Exception;

/**
 * User not found exception
 */
class UserNotFoundException extends Exception
{
    public function __construct(int $userId)
    {
        parent::__construct("User with ID {$userId} not found");
    }
}



