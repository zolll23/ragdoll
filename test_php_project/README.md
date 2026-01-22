# Test PHP Project for CodeRAG Metrics

This is a compact test PHP project designed to validate all CodeRAG metrics collection.

## Structure

- **Models/**: Domain entities (User)
- **Repositories/**: Data access layer (UserRepository with N+1 examples)
- **Services/**: Business logic (UserService - God Object example)
- **Controllers/**: MVC controllers
- **Utils/**: Utility classes with various complexity levels
- **DesignPatterns/**: Design pattern examples
- **Exceptions/**: Custom exceptions

## Metrics Covered

### Complexity Metrics
- **O(1)**: Simple getters, Calculator::add()
- **O(n)**: Linear search, Calculator::sum()
- **O(log n)**: Binary search, Calculator::binarySearch()
- **O(n²)**: Nested loops, Calculator::findDuplicates(), Calculator::findAllPairs(), Calculator::multiplyMatrices()
- **O(n!)**: All permutations, Calculator::generateAllPermutations() ⚠️
- **O(n) space**: Recursive factorial

### Cyclomatic Complexity
- Low: Simple methods (1-2)
- Medium: Methods with conditionals (3-5)
- High: Complex switch/if chains (6+)

### Cognitive Complexity
- Nested conditionals in `processUserAction()`
- Multiple responsibilities in `registerUser()`

### Security Issues
- **SQL Injection**: `findByNameUnsafe()` - direct string interpolation
- **XSS**: `sendEmail()` - unescaped HTML
- **Hardcoded Secrets**: `$apiKey` in UserService

### N+1 Queries
- **Bad**: `findUsersWithRoles()` - queries in loop
- **Good**: `findUsersWithRolesOptimized()` - single JOIN query

### Architecture Metrics
- **God Object**: UserService (too many responsibilities)
- **Feature Envy**: `getUserInfo()` accesses many User methods
- **Long Parameter List**: `createUserWithManyParams()`
- **Data Clumps**: Multiple address parameters

### SOLID Violations
- **SRP**: UserService does registration, validation, email, notifications
- **OCP**: Hard to extend without modification
- **DIP**: Direct dependencies on concrete classes

### Design Patterns
- **Singleton**: Singleton class
- **Factory**: UserFactory
- **Repository**: UserRepository

### DDD/MVC Roles
- **Model**: User (domain entity)
- **Repository**: UserRepository (data access)
- **Service**: UserService (business logic)
- **Controller**: UserController (MVC controller)

## Usage

This project is designed to be indexed by CodeRAG to test all metric collection features.

## Documentation

See [METRICS_DOCUMENTATION.md](./METRICS_DOCUMENTATION.md) for detailed documentation on:
- How to find each type of metric
- What problems each metric indicates
- Examples of good and bad code
- How to search for metrics in CodeRAG

## New Complexity Examples

### O(n²) Examples
- `Calculator::findDuplicates()` - finds duplicates using nested loops
- `Calculator::findAllPairs()` - generates all pairs from array
- `Calculator::multiplyMatrices()` - matrix multiplication (O(n³) for square matrices)

### O(n!) Example
- `Calculator::generateAllPermutations()` - generates all permutations of array
  - **WARNING**: Factorial complexity! For n=10, this is 3,628,800 operations
  - Use with caution, only for small arrays

