"""
Example usage of CodeRAG Python client
"""
from python_client import CodeRAGClient

def main():
    # Initialize client
    client = CodeRAGClient(base_url="http://localhost:8000")
    
    # 1. Health check
    print("=== Health Check ===")
    health = client.health_check()
    print(f"Status: {health['status']}")
    print()
    
    # 2. List projects
    print("=== Projects ===")
    projects = client.list_projects()
    for project in projects:
        print(f"  {project['name']} ({project['language']}) - {project['indexed_files']}/{project['total_files']} files")
    print()
    
    if not projects:
        print("No projects found. Please index a project first.")
        return
    
    project_id = projects[0]['id']
    project_name = projects[0]['name']
    
    # 3. Search code
    print(f"=== Search in {project_name} ===")
    results = client.search_code(
        query="find methods for sending messages",
        project_id=project_id,
        limit=5
    )
    print(f"Found {len(results)} results:")
    for result in results:
        print(f"  - {result['name']} ({result['type']}) in {result['file_path']}:{result['start_line']}")
        if result['description']:
            print(f"    {result['description'][:80]}...")
    print()
    
    if not results:
        print("No search results found.")
        return
    
    # 4. Get entity details
    entity_id = results[0]['entity_id']
    print(f"=== Entity Details (ID: {entity_id}) ===")
    entity = client.analyze_entity(entity_id=entity_id)
    print(f"Name: {entity['entity']['name']}")
    print(f"Type: {entity['entity']['type']}")
    print(f"File: {entity['entity']['file_path']}")
    print(f"Lines: {entity['entity']['start_line']}-{entity['entity']['end_line']}")
    if entity['analysis']:
        print(f"Description: {entity['analysis']['description'][:100]}...")
        print(f"Complexity: {entity['analysis']['complexity']}")
    print()
    
    # 5. Get metrics
    print(f"=== Metrics (ID: {entity_id}) ===")
    metrics = client.get_entity_metrics(entity_id)
    print(f"Lines of Code: {metrics['metrics']['size']['lines_of_code']}")
    print(f"Cyclomatic Complexity: {metrics['metrics']['complexity']['cyclomatic']}")
    print(f"Cognitive Complexity: {metrics['metrics']['complexity']['cognitive']}")
    print(f"Security Issues: {metrics['metrics']['issues']['security_issues_count']}")
    print(f"N+1 Queries: {metrics['metrics']['issues']['n_plus_one_queries_count']}")
    print()
    
    # 6. Get refactoring suggestions
    print(f"=== Refactoring Suggestions (ID: {entity_id}) ===")
    suggestions = client.get_refactoring_suggestions(entity_id)
    print(f"Found {len(suggestions['suggestions'])} suggestions:")
    for suggestion in suggestions['suggestions']:
        print(f"  [{suggestion['severity'].upper()}] {suggestion['type']}")
        print(f"    {suggestion['description']}")
        if suggestion.get('suggestion'):
            print(f"    Suggestion: {suggestion['suggestion']}")
    print()
    
    # 7. Find entity by location
    if entity['entity']['file_path']:
        print(f"=== Find Entity by Location ===")
        found = client.find_entity(
            project_id=project_id,
            file_path=entity['entity']['file_path'],
            line_number=entity['entity']['start_line']
        )
        print(f"Found: {found['entity']['name']} (ID: {found['entity']['id']})")
        print()

if __name__ == "__main__":
    main()



