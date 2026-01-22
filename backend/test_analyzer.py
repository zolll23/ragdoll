"""
Test script for code analyzer
Run: docker-compose exec backend python test_analyzer.py
"""
import sys
sys.path.insert(0, '/app')

from app.agents.analyzer import CodeAnalyzer
from app.core.config import settings
from app.models.database import Entity
from app.core.database import SessionLocal

# Get real code from database
db = SessionLocal()
entity = db.query(Entity).filter(Entity.code.isnot(None)).first()
if entity:
    test_code = entity.code
    test_language = "php" if ".php" in entity.file.path else "python"
    test_name = entity.name
    test_type = entity.type
    print(f"Using real code from: {entity.file.path}")
    print(f"Entity: {test_name} ({test_type})")
else:
    # Fallback sample code
    test_code = """
class UserService {
    public function createUser($name, $email) {
        $user = new User();
        $user->setName($name);
        $user->setEmail($email);
        
        $this->db->save($user);
        
        return $user;
    }
}
"""
    test_language = "php"
    test_name = "UserService"
    test_type = "class"
db.close()

print(f"\nTesting analyzer with provider: {settings.LLM_PROVIDER}, model: {settings.LLM_MODEL}")
print(f"Ollama URL: {settings.OLLAMA_URL}")
print("-" * 60)

try:
    analyzer = CodeAnalyzer()
    
    print("Analyzing code...")
    result, tokens_used = analyzer.analyze_code(
        code=test_code,
        language=test_language,
        entity_type=test_type,
        entity_name=test_name,
        context=None,
        ui_language="RU"
    )
    
    print(f"\nCode being analyzed (first 200 chars):")
    print(test_code[:200])
    print(f"\nCode length: {len(test_code)} chars")
    print("\n" + "=" * 60)
    print("ANALYSIS RESULT:")
    print("=" * 60)
    print(f"Tokens used: {tokens_used}")
    print(f"Description: {result.description}")
    print(f"Complexity: {result.complexity}")
    print(f"Complexity Explanation: {result.complexity_explanation}")
    print(f"Design Patterns: {result.design_patterns}")
    print(f"DDD Role: {result.ddd_role}")
    print(f"MVC Role: {result.mvc_role}")
    print(f"Is Testable: {result.is_testable}")
    print(f"Testability Score: {result.testability_score}")
    print(f"SOLID Violations: {len(result.solid_violations)}")
    for v in result.solid_violations:
        print(f"  - {v.principle}: {v.description[:50]}...")
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
