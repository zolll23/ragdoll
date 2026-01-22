"""
Python API Client for CodeRAG IDE Integration
For use in PyCharm plugins
"""
import requests
from typing import Optional, List, Dict, Any
import json


class CodeRAGClient:
    """Client for CodeRAG IDE API"""
    
    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 30):
        """
        Initialize CodeRAG client
        
        Args:
            base_url: Base URL of CodeRAG API
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request"""
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault('timeout', self.timeout)
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health"""
        return self._request('GET', '/api/ide/health')
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """List all indexed projects"""
        return self._request('GET', '/api/ide/projects')
    
    def find_entity(
        self,
        project_id: int,
        file_path: str,
        line_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Find entity by file location
        
        Args:
            project_id: Project ID
            file_path: File path relative to project root
            line_number: Optional line number (finds entity containing this line)
        """
        data = {
            "project_id": project_id,
            "file_path": file_path
        }
        if line_number is not None:
            data["line_number"] = line_number
        
        return self._request('POST', '/api/ide/find-entity', json=data)
    
    def analyze_entity(
        self,
        entity_id: Optional[int] = None,
        project_id: Optional[int] = None,
        file_path: Optional[str] = None,
        entity_name: Optional[str] = None,
        line_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analyze entity by various criteria
        
        Args:
            entity_id: Entity ID (if known)
            project_id: Project ID (required if using file_path)
            file_path: File path relative to project root
            entity_name: Name of entity
            line_number: Line number in file
        """
        data = {}
        if entity_id:
            data["entity_id"] = entity_id
        if project_id:
            data["project_id"] = project_id
        if file_path:
            data["file_path"] = file_path
        if entity_name:
            data["entity_name"] = entity_name
        if line_number is not None:
            data["line_number"] = line_number
        
        return self._request('POST', '/api/ide/analyze', json=data)
    
    def search_code(
        self,
        query: str,
        project_id: Optional[int] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search code using natural language query
        
        Args:
            query: Natural language search query
            project_id: Optional project ID to filter
            limit: Maximum number of results (default: 20, max: 100)
        """
        data = {
            "query": query,
            "limit": min(limit, 100)
        }
        if project_id:
            data["project_id"] = project_id
        
        return self._request('POST', '/api/ide/search', json=data)
    
    def get_refactoring_suggestions(
        self,
        entity_id: int,
        include_similar_code: bool = True,
        similarity_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Get refactoring suggestions for an entity
        
        Args:
            entity_id: Entity ID
            include_similar_code: Include similar code patterns
            similarity_threshold: Minimum similarity score (0.0-1.0)
        """
        data = {
            "entity_id": entity_id,
            "include_similar_code": include_similar_code,
            "similarity_threshold": similarity_threshold
        }
        return self._request('POST', '/api/ide/refactoring', json=data)
    
    def get_entity_metrics(self, entity_id: int) -> Dict[str, Any]:
        """
        Get all metrics for an entity
        
        Args:
            entity_id: Entity ID
        """
        return self._request('GET', f'/api/ide/entity/{entity_id}/metrics')


# Example usage
if __name__ == "__main__":
    client = CodeRAGClient()
    
    # Health check
    print("Health:", client.health_check())
    
    # List projects
    projects = client.list_projects()
    print(f"Projects: {len(projects)}")
    
    if projects:
        project_id = projects[0]["id"]
        
        # Search code
        results = client.search_code("find methods for sending messages", project_id=project_id)
        print(f"Search results: {len(results)}")
        
        if results:
            entity_id = results[0]["entity_id"]
            
            # Get metrics
            metrics = client.get_entity_metrics(entity_id)
            print(f"Metrics: {metrics['metrics']['complexity']}")
            
            # Get refactoring suggestions
            suggestions = client.get_refactoring_suggestions(entity_id)
            print(f"Suggestions: {len(suggestions['suggestions'])}")

