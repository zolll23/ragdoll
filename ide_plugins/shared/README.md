# CodeRAG IDE API Client

Shared API client for IDE plugins (PhpStorm, PyCharm) to interact with CodeRAG backend.

## API Base URL

Default: `http://localhost:8000`

Can be configured via environment variable or plugin settings.

## Endpoints

### Health Check
```
GET /api/ide/health
```

### List Projects
```
GET /api/ide/projects
```

Response:
```json
[
  {
    "id": 1,
    "name": "My Project",
    "path": "/path/to/project",
    "language": "python",
    "total_files": 100,
    "indexed_files": 95,
    "total_entities": 500,
    "is_indexing": false,
    "progress_percent": 95.0
  }
]
```

### Find Entity by Location
```
POST /api/ide/find-entity
Content-Type: application/json

{
  "project_id": 1,
  "file_path": "src/services/user.py",
  "line_number": 42
}
```

Response:
```json
{
  "entity": {
    "id": 123,
    "name": "get_user",
    "type": "method",
    "file_path": "src/services/user.py",
    "start_line": 40,
    "end_line": 50,
    "code": "..."
  },
  "analysis": {
    "description": "...",
    "complexity": "O(n)",
    ...
  },
  "dependencies": [...],
  "metrics": {...}
}
```

### Analyze Entity
```
POST /api/ide/analyze
Content-Type: application/json

{
  "entity_id": 123
}
// OR
{
  "project_id": 1,
  "file_path": "src/services/user.py",
  "entity_name": "get_user"
}
// OR
{
  "project_id": 1,
  "file_path": "src/services/user.py",
  "line_number": 42
}
```

### Search Code
```
POST /api/ide/search
Content-Type: application/json

{
  "query": "find methods for sending messages",
  "project_id": 1,
  "limit": 20
}
```

### Get Refactoring Suggestions
```
POST /api/ide/refactoring
Content-Type: application/json

{
  "entity_id": 123,
  "include_similar_code": true,
  "similarity_threshold": 0.7
}
```

Response:
```json
{
  "entity_id": 123,
  "entity_name": "get_user",
  "file_path": "src/services/user.py",
  "suggestions": [
    {
      "type": "solid_violation",
      "principle": "Single Responsibility Principle",
      "description": "...",
      "severity": "medium",
      "suggestion": "...",
      "location": {
        "file_path": "src/services/user.py",
        "start_line": 40,
        "end_line": 50
      }
    }
  ],
  "similar_code": []
}
```

### Get Entity Metrics
```
GET /api/ide/entity/{entity_id}/metrics
```

Response:
```json
{
  "entity_id": 123,
  "entity_name": "get_user",
  "metrics": {
    "size": {
      "lines_of_code": 25,
      "parameter_count": 2
    },
    "complexity": {
      "cyclomatic": 5,
      "cognitive": 8,
      "max_nesting_depth": 3,
      "asymptotic": "O(n)",
      "space": "O(1)"
    },
    "coupling": {
      "coupling_score": 0.3,
      "cohesion_score": 0.8,
      "afferent_coupling": 2,
      "efferent_coupling": 3
    },
    "quality": {
      "is_testable": true,
      "testability_score": 0.85,
      "is_god_object": false,
      "feature_envy_score": 0.2,
      "long_parameter_list": false
    },
    "issues": {
      "security_issues_count": 0,
      "n_plus_one_queries_count": 0,
      "solid_violations_count": 1
    }
  }
}
```

## Error Responses

All endpoints return standard HTTP status codes:
- `200 OK` - Success
- `404 Not Found` - Entity/Project not found
- `500 Internal Server Error` - Server error

Error response format:
```json
{
  "detail": "Error message"
}
```

