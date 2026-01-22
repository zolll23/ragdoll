"""
Static code metrics analyzer
Computes code quality metrics without LLM (LOC, cyclomatic complexity, etc.)
"""
import ast
import re
import logging
from typing import List, Dict, Optional, Tuple
from app.api.models.schemas import SecurityIssue, Severity

logger = logging.getLogger(__name__)


class StaticMetricsAnalyzer:
    """Analyze code to extract static metrics"""
    
    def __init__(self):
        pass
    
    def analyze(self, code: str, language: str, entity_type: str, dependencies: List[str] = None) -> Dict:
        """Analyze code and return all static metrics
        
        Args:
            code: Source code
            language: 'python' or 'php'
            entity_type: 'class', 'method', 'function', 'constant', 'enum', 'dict'
            dependencies: List of dependency names (for coupling calculation)
            
        Returns:
            Dictionary with all computed metrics
        """
        if dependencies is None:
            dependencies = []
        
        metrics = {
            # Size metrics
            'lines_of_code': self.calculate_loc(code),
            'cyclomatic_complexity': self.calculate_cyclomatic_complexity(code, language),
            'cognitive_complexity': self.calculate_cognitive_complexity(code, language),
            'max_nesting_depth': self.calculate_nesting_depth(code, language),
            'parameter_count': self.count_parameters(code, language, entity_type),
            
            # Coupling and cohesion
            'coupling_score': self.calculate_coupling(code, dependencies),
            'cohesion_score': self.calculate_cohesion(code, language),
            'afferent_coupling': len(dependencies),  # Incoming dependencies
            'efferent_coupling': self.count_outgoing_dependencies(code, language),  # Outgoing dependencies
            
            # Performance
            'n_plus_one_queries': self.detect_n_plus_one(code, language),
            'space_complexity': self.estimate_space_complexity(code, language),
            'hot_path_detected': False,  # Will be determined by usage statistics later
            
            # Security
            'security_issues': self.detect_security_issues(code, language),
            'hardcoded_secrets': self.detect_hardcoded_secrets(code, language),
            'insecure_dependencies': [],  # Will be checked against vulnerability DB later
            
            # Architecture
            'is_god_object': self.detect_god_object(code, language, entity_type),
            'feature_envy_score': self.calculate_feature_envy(code, language),
            'data_clumps': self.detect_data_clumps(code, language),
            'long_parameter_list': self.has_long_parameter_list(code, language),
        }
        
        return metrics
    
    def calculate_loc(self, code: str) -> int:
        """Calculate Lines of Code (excluding empty lines and comments)"""
        lines = code.split('\n')
        loc = 0
        for line in lines:
            stripped = line.strip()
            # Skip empty lines and comments
            if stripped and not stripped.startswith('#'):
                # For PHP, also skip // and /* */ comments
                if not stripped.startswith('//') and not stripped.startswith('/*'):
                    loc += 1
        return loc
    
    def calculate_cyclomatic_complexity(self, code: str, language: str) -> int:
        """Calculate cyclomatic complexity (base complexity = 1)"""
        if language == 'python':
            return self._calculate_cyclomatic_python(code)
        elif language == 'php':
            return self._calculate_cyclomatic_php(code)
        return 1
    
    def _calculate_cyclomatic_python(self, code: str) -> int:
        """Calculate cyclomatic complexity for Python using AST"""
        try:
            tree = ast.parse(code)
            complexity = 1  # Base complexity
            
            class ComplexityVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.complexity = 1
                
                def visit_If(self, node):
                    self.complexity += 1
                    self.generic_visit(node)
                
                def visit_For(self, node):
                    self.complexity += 1
                    self.generic_visit(node)
                
                def visit_While(self, node):
                    self.complexity += 1
                    self.generic_visit(node)
                
                def visit_With(self, node):
                    self.complexity += 1
                    self.generic_visit(node)
                
                def visit_Try(self, node):
                    self.complexity += 1
                    self.generic_visit(node)
                
                def visit_ExceptHandler(self, node):
                    self.complexity += 1
                    self.generic_visit(node)
                
                def visit_BoolOp(self, node):
                    # Each 'and'/'or' adds complexity
                    self.complexity += len(node.values) - 1
                    self.generic_visit(node)
            
            visitor = ComplexityVisitor()
            visitor.visit(tree)
            return visitor.complexity
        except SyntaxError:
            # Fallback to regex-based counting
            return self._calculate_cyclomatic_regex(code, 'python')
    
    def _calculate_cyclomatic_php(self, code: str) -> int:
        """Calculate cyclomatic complexity for PHP using regex"""
        return self._calculate_cyclomatic_regex(code, 'php')
    
    def _calculate_cyclomatic_regex(self, code: str, language: str) -> int:
        """Fallback regex-based cyclomatic complexity calculation"""
        complexity = 1  # Base complexity
        
        # Decision points that increase complexity
        patterns = [
            r'\bif\s*\(', r'\belseif\s*\(', r'\belse\b',
            r'\bfor\s*\(', r'\bforeach\s*\(', r'\bwhile\s*\(',
            r'\bswitch\s*\(', r'\bcase\s+',
            r'\bcatch\s*\(', r'\bthrow\s+',
            r'\?\s*',  # Ternary operator
        ]
        
        if language == 'python':
            patterns.extend([
                r'\btry\s*:', r'\bexcept\s+', r'\bwith\s+',
                r'\band\b', r'\bor\b',  # Boolean operators
            ])
        elif language == 'php':
            patterns.extend([
                r'\btry\s*\{', r'\bcatch\s*\(',
                r'\b&&\b', r'\b\|\|\b',  # Boolean operators
            ])
        
        for pattern in patterns:
            matches = re.findall(pattern, code, re.IGNORECASE)
            complexity += len(matches)
        
        return max(1, complexity)
    
    def calculate_cognitive_complexity(self, code: str, language: str) -> int:
        """Calculate cognitive complexity (simplified version)"""
        # Cognitive complexity is similar to cyclomatic but penalizes nesting more
        if language == 'python':
            return self._calculate_cognitive_python(code)
        else:
            # For PHP, use simplified version based on nesting
            nesting = self.calculate_nesting_depth(code, language)
            cyclomatic = self.calculate_cyclomatic_complexity(code, language)
            # Cognitive complexity = cyclomatic + nesting penalty
            return cyclomatic + (nesting - 1) * 2 if nesting > 1 else cyclomatic
    
    def _calculate_cognitive_python(self, code: str) -> int:
        """Calculate cognitive complexity for Python"""
        try:
            tree = ast.parse(code)
            complexity = 0
            nesting_level = 0
            
            class CognitiveVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.complexity = 0
                    self.nesting = 0
                
                def visit_If(self, node):
                    self.complexity += 1 + self.nesting
                    self.nesting += 1
                    self.generic_visit(node)
                    self.nesting -= 1
                
                def visit_For(self, node):
                    self.complexity += 1 + self.nesting
                    self.nesting += 1
                    self.generic_visit(node)
                    self.nesting -= 1
                
                def visit_While(self, node):
                    self.complexity += 1 + self.nesting
                    self.nesting += 1
                    self.generic_visit(node)
                    self.nesting -= 1
                
                def visit_Try(self, node):
                    self.complexity += 1 + self.nesting
                    self.nesting += 1
                    self.generic_visit(node)
                    self.nesting -= 1
                
                def visit_ExceptHandler(self, node):
                    self.complexity += 1 + self.nesting
                    self.generic_visit(node)
            
            visitor = CognitiveVisitor()
            visitor.visit(tree)
            return visitor.complexity
        except SyntaxError:
            # Fallback: use cyclomatic + nesting penalty
            nesting = self.calculate_nesting_depth(code, 'python')
            cyclomatic = self.calculate_cyclomatic_complexity(code, 'python')
            return cyclomatic + (nesting - 1) * 2 if nesting > 1 else cyclomatic
    
    def calculate_nesting_depth(self, code: str, language: str) -> int:
        """Calculate maximum nesting depth"""
        if language == 'python':
            return self._calculate_nesting_python(code)
        else:
            return self._calculate_nesting_php(code)
    
    def _calculate_nesting_python(self, code: str) -> int:
        """Calculate nesting depth for Python"""
        try:
            tree = ast.parse(code)
            max_depth = 0
            current_depth = 0
            
            class NestingVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.max_depth = 0
                    self.current_depth = 0
                
                def visit_FunctionDef(self, node):
                    self.current_depth += 1
                    self.max_depth = max(self.max_depth, self.current_depth)
                    self.generic_visit(node)
                    self.current_depth -= 1
                
                def visit_ClassDef(self, node):
                    self.current_depth += 1
                    self.max_depth = max(self.max_depth, self.current_depth)
                    self.generic_visit(node)
                    self.current_depth -= 1
                
                def visit_If(self, node):
                    self.current_depth += 1
                    self.max_depth = max(self.max_depth, self.current_depth)
                    self.generic_visit(node)
                    self.current_depth -= 1
                
                def visit_For(self, node):
                    self.current_depth += 1
                    self.max_depth = max(self.max_depth, self.current_depth)
                    self.generic_visit(node)
                    self.current_depth -= 1
                
                def visit_While(self, node):
                    self.current_depth += 1
                    self.max_depth = max(self.max_depth, self.current_depth)
                    self.generic_visit(node)
                    self.current_depth -= 1
                
                def visit_Try(self, node):
                    self.current_depth += 1
                    self.max_depth = max(self.max_depth, self.current_depth)
                    self.generic_visit(node)
                    self.current_depth -= 1
            
            visitor = NestingVisitor()
            visitor.visit(tree)
            return visitor.max_depth
        except SyntaxError:
            # Fallback: count indentation levels
            lines = code.split('\n')
            max_indent = 0
            for line in lines:
                if line.strip():
                    indent = len(line) - len(line.lstrip())
                    max_indent = max(max_indent, indent)
            # Approximate: 4 spaces = 1 level
            return max(1, max_indent // 4 + 1)
    
    def _calculate_nesting_php(self, code: str) -> int:
        """Calculate nesting depth for PHP"""
        max_depth = 0
        current_depth = 0
        
        for char in code:
            if char == '{':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == '}':
                current_depth = max(0, current_depth - 1)
        
        return max(1, max_depth)
    
    def count_parameters(self, code: str, language: str, entity_type: str) -> int:
        """Count function/method parameters"""
        if entity_type in ['constant', 'enum', 'dict']:
            return 0
        
        if language == 'python':
            return self._count_parameters_python(code)
        else:
            return self._count_parameters_php(code)
    
    def _count_parameters_python(self, code: str) -> int:
        """Count parameters in Python function/method"""
        try:
            tree = ast.parse(code)
            
            class ParamVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.param_count = 0
                
                def visit_FunctionDef(self, node):
                    # Count args, excluding self/cls
                    args = [arg for arg in node.args.args if arg.arg not in ['self', 'cls']]
                    self.param_count = len(args)
                    # Don't visit children to avoid counting nested functions
            
            visitor = ParamVisitor()
            visitor.visit(tree)
            return visitor.param_count
        except SyntaxError:
            # Fallback: regex
            match = re.search(r'def\s+\w+\s*\(([^)]*)\)', code)
            if match:
                params = match.group(1).strip()
                if not params:
                    return 0
                # Count parameters (simple split by comma)
                return len([p for p in params.split(',') if p.strip() and not p.strip().startswith('*')])
            return 0
    
    def _count_parameters_php(self, code: str) -> int:
        """Count parameters in PHP function/method"""
        # Match function/method definitions
        match = re.search(r'function\s+\w+\s*\(([^)]*)\)', code)
        if match:
            params = match.group(1).strip()
            if not params:
                return 0
            # Count parameters (split by comma, but handle type hints)
            params_list = [p.strip() for p in params.split(',') if p.strip()]
            return len(params_list)
        return 0
    
    def calculate_coupling(self, code: str, dependencies: List[str]) -> float:
        """Calculate coupling score (0.0-1.0, higher = more coupled)"""
        if not dependencies:
            return 0.0
        
        # Count unique dependencies used in code
        used_deps = 0
        code_lower = code.lower()
        for dep in dependencies:
            # Simple check: if dependency name appears in code
            dep_name = dep.split('.')[-1].split('::')[-1].lower()
            if dep_name in code_lower:
                used_deps += 1
        
        # Coupling score: ratio of used dependencies to total dependencies
        # Normalize to 0.0-1.0, but cap at reasonable level
        if len(dependencies) == 0:
            return 0.0
        
        coupling_ratio = used_deps / len(dependencies)
        # Higher coupling is worse, so we return the ratio directly
        return min(1.0, coupling_ratio)
    
    def calculate_cohesion(self, code: str, language: str) -> float:
        """Calculate cohesion score (0.0-1.0, higher = more cohesive)"""
        # Simplified cohesion: check if code is focused (few distinct operations)
        # This is a heuristic - true cohesion analysis requires semantic understanding
        
        lines = [l.strip() for l in code.split('\n') if l.strip() and not l.strip().startswith('#')]
        if len(lines) <= 1:
            return 1.0
        
        # Count distinct operations/patterns
        distinct_operations = set()
        for line in lines:
            # Extract operation type (simplified)
            if re.search(r'\b(if|for|while|return|assign|call)\b', line, re.IGNORECASE):
                distinct_operations.add('control_flow')
            if re.search(r'\b(import|from|use|require)\b', line, re.IGNORECASE):
                distinct_operations.add('import')
            if re.search(r'[=+\-*/]', line):
                distinct_operations.add('assignment')
        
        # Higher cohesion = fewer distinct operation types relative to code size
        # Simplified: cohesion decreases as we have more distinct operations
        operation_diversity = len(distinct_operations) / max(1, len(lines))
        cohesion = 1.0 - min(1.0, operation_diversity * 0.5)  # Scale down the penalty
        
        return max(0.0, min(1.0, cohesion))
    
    def count_outgoing_dependencies(self, code: str, language: str) -> int:
        """Count outgoing dependencies (classes/methods used in code)"""
        # This is a simplified version - full analysis would use AST
        # For now, count method calls and class instantiations
        
        if language == 'python':
            # Count method calls: obj.method() or Class.method()
            method_calls = len(re.findall(r'\w+\.\w+\s*\(', code))
            # Count class instantiations: Class()
            instantiations = len(re.findall(r'\b[A-Z]\w+\s*\(', code))
            return method_calls + instantiations
        else:  # PHP
            # Count method calls: $obj->method() or Class::method()
            method_calls = len(re.findall(r'->\w+\s*\(|::\w+\s*\(', code))
            # Count instantiations: new Class()
            instantiations = len(re.findall(r'new\s+\w+', code))
            return method_calls + instantiations
    
    def detect_n_plus_one(self, code: str, language: str) -> List[str]:
        """Detect N+1 query problems"""
        issues = []
        
        # Pattern: loop with database query inside
        if language == 'python':
            # Look for: for/while loop containing db.query() or similar
            # More precise pattern: find loop and its body
            lines = code.split('\n')
            in_loop = False
            loop_start = 0
            loop_indent = 0
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                # Detect loop start
                if re.match(r'(for|while)\s+', stripped):
                    in_loop = True
                    loop_start = i
                    loop_indent = len(line) - len(line.lstrip())
                    continue
                
                # Check if we're still in the loop (same or greater indent)
                if in_loop:
                    current_indent = len(line) - len(line.lstrip()) if line.strip() else loop_indent
                    # If indent is less than loop indent, we've exited the loop
                    if line.strip() and current_indent <= loop_indent and not stripped.startswith('#'):
                        # Check loop body for DB queries
                        loop_body = '\n'.join(lines[loop_start:i])
                        if re.search(r'(db\.(query|execute|fetch)|session\.(query|execute)|\.query\(|\.execute\()', loop_body, re.IGNORECASE):
                            issues.append(f"N+1 query detected in loop starting at line {loop_start + 1}")
                        in_loop = False
                    # Check current line for DB queries
                    elif re.search(r'(db\.(query|execute|fetch)|session\.(query|execute))', line, re.IGNORECASE):
                        issues.append(f"N+1 query detected in loop at line {i + 1}")
        else:  # PHP
            # Look for: foreach/for loop containing $db->query() or similar
            # Match loop with braces
            loop_pattern = r'(foreach|for)\s*\([^)]+\)\s*\{'
            loops = re.finditer(loop_pattern, code, re.IGNORECASE)
            for loop_match in loops:
                # Find matching closing brace
                start_pos = loop_match.end()
                brace_count = 1
                end_pos = start_pos
                
                for i, char in enumerate(code[start_pos:], start_pos):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = i
                            break
                
                if end_pos > start_pos:
                    loop_body = code[start_pos:end_pos]
                    # Check if loop body contains DB queries
                    if re.search(r'(\$db->(query|execute)|DB::(query|execute)|->query\(|->execute\()', loop_body, re.IGNORECASE):
                        line_num = code[:loop_match.start()].count('\n') + 1
                        issues.append(f"N+1 query detected in {loop_match.group(1)} loop starting at line {line_num}")
        
        return issues
    
    def estimate_space_complexity(self, code: str, language: str) -> str:
        """Estimate space complexity (simplified)"""
        # Look for patterns that indicate space usage
        # This is a heuristic - full analysis would require data flow analysis
        
        # Check for data structures that grow with input
        if re.search(r'(list|array|dict|set)\s*\(|\[\]|\[\s*\]', code, re.IGNORECASE):
            # Check if it's in a loop
            if re.search(r'(for|while|foreach)', code, re.IGNORECASE):
                return "O(n)"  # Likely O(n) space
            return "O(1)"  # Fixed size
        
        # Recursive calls might indicate O(n) or O(log n) space
        if re.search(r'\b\w+\s*\(.*\b\w+\s*\(', code):  # Nested function calls
            return "O(n)"  # Conservative estimate
        
        return "O(1)"  # Default: constant space
    
    def detect_security_issues(self, code: str, language: str) -> List[SecurityIssue]:
        """Detect security issues in code"""
        issues = []
        
        # SQL Injection detection
        sql_issues = self._detect_sql_injection(code, language)
        issues.extend(sql_issues)
        
        # XSS detection
        xss_issues = self._detect_xss(code, language)
        issues.extend(xss_issues)
        
        return issues
    
    def _detect_sql_injection(self, code: str, language: str) -> List[SecurityIssue]:
        """Detect potential SQL injection vulnerabilities"""
        issues = []
        
        if language == 'python':
            # Python patterns: string concatenation in SQL
            # Pattern 1: 'SELECT ...' + variable or variable + 'SELECT ...'
            patterns = [
                (r'["\']\s*SELECT.*?\s*["\']\s*\+\s*\w+', 'String concatenation after SQL'),
                (r'\w+\s*\+\s*["\']\s*SELECT', 'String concatenation before SQL'),
                (r'f["\'].*SELECT.*\{.*\}', 'f-string in SQL query'),
                (r'["\']\s*SELECT.*%s.*["\']\s*%\s*\w+', 'String formatting in SQL'),
            ]
        else:  # PHP
            # PHP patterns: string concatenation or interpolation in SQL
            patterns = [
                (r'["\']\s*SELECT.*?\s*["\']\s*\.\s*\$\w+', 'String concatenation in SQL'),
                (r'\$\w+\s*\.\s*["\']\s*SELECT', 'String concatenation before SQL'),
                (r'["\']\s*SELECT.*\$.*["\']', 'Variable interpolation in SQL'),
                (r'["\']\s*SELECT.*\{.*\}["\']', 'Variable interpolation in SQL (curly braces)'),
            ]
        
        for pattern, desc in patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE | re.DOTALL)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                match_text = match.group(0)[:80].replace('\n', ' ')
                issues.append(SecurityIssue(
                    type="sql_injection",
                    severity=Severity.HIGH,
                    description=f"Potential SQL injection: {desc}",
                    location=f"line {line_num}: {match_text}",
                    suggestion="Use parameterized queries or prepared statements"
                ))
        
        return issues
    
    def _detect_xss(self, code: str, language: str) -> List[SecurityIssue]:
        """Detect potential XSS vulnerabilities"""
        issues = []
        
        # Pattern: unescaped user input in output
        # Look for: echo/print with $_GET/$_POST/$_REQUEST (PHP) or direct output (Python)
        if language == 'php':
            # PHP: echo/print with $_GET, $_POST, $_REQUEST
            xss_pattern = r'(echo|print)\s+.*?(\$_GET|\$_POST|\$_REQUEST|\$_COOKIE)'
            matches = re.finditer(xss_pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                issues.append(SecurityIssue(
                    type="xss",
                    severity=Severity.HIGH,
                    description=f"Potential XSS: unescaped user input in output",
                    location=f"line {line_num}: {match.group(0)[:50]}",
                    suggestion="Use htmlspecialchars() or htmlentities() to escape output"
                ))
        else:  # Python
            # Python: direct output of request data (simplified)
            xss_pattern = r'(print|return)\s+.*?(request\.|form\.|GET|POST)'
            matches = re.finditer(xss_pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                issues.append(SecurityIssue(
                    type="xss",
                    severity=Severity.MEDIUM,
                    description=f"Potential XSS: unescaped user input in output",
                    location=f"line {line_num}: {match.group(0)[:50]}",
                    suggestion="Use template escaping or html.escape() to escape output"
                ))
        
        return issues
    
    def detect_hardcoded_secrets(self, code: str, language: str) -> List[str]:
        """Detect hardcoded secrets (API keys, passwords, etc.)"""
        secrets = []
        
        # Patterns for common secrets
        secret_patterns = [
            (r'api[_-]?key\s*[=:]\s*["\']([^"\']+)["\']', 'API key'),
            (r'password\s*[=:]\s*["\']([^"\']+)["\']', 'Password'),
            (r'secret\s*[=:]\s*["\']([^"\']+)["\']', 'Secret'),
            (r'token\s*[=:]\s*["\']([^"\']{20,})["\']', 'Token'),  # Long tokens
            (r'private[_-]?key\s*[=:]\s*["\']([^"\']+)["\']', 'Private key'),
        ]
        
        for pattern, secret_type in secret_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                # Don't include the actual secret value, just the location
                secrets.append(f"{secret_type} found at line {line_num}")
        
        return secrets
    
    def detect_god_object(self, code: str, language: str, entity_type: str) -> bool:
        """Detect if entity is a 'God Object' (too many responsibilities)"""
        if entity_type != 'class':
            return False
        
        # Heuristics for God Object:
        # 1. Many methods (count method definitions)
        # 2. High cyclomatic complexity
        # 3. Many dependencies
        
        method_count = len(re.findall(r'(def\s+\w+|function\s+\w+)', code, re.IGNORECASE))
        complexity = self.calculate_cyclomatic_complexity(code, language)
        loc = self.calculate_loc(code)
        
        # Thresholds (can be adjusted)
        is_god = (
            method_count > 20 or  # Too many methods
            complexity > 50 or    # Very high complexity
            loc > 500             # Very large class
        )
        
        return is_god
    
    def calculate_feature_envy(self, code: str, language: str) -> float:
        """Calculate feature envy score (0.0-1.0, higher = more envy)"""
        # Feature envy: method uses more data from other classes than its own
        # Simplified: count external method calls vs internal
        
        if language == 'python':
            # Count self.method() vs other.method()
            self_calls = len(re.findall(r'self\.\w+\s*\(', code))
            other_calls = len(re.findall(r'(?<!self\.)\b\w+\.\w+\s*\(', code))
        else:  # PHP
            # Count $this->method() vs $obj->method() or Class::method()
            self_calls = len(re.findall(r'\$this->\w+\s*\(', code))
            other_calls = len(re.findall(r'(?<!\$this->)\$\w+->\w+\s*\(|::\w+\s*\(', code))
        
        total_calls = self_calls + other_calls
        if total_calls == 0:
            return 0.0
        
        # Feature envy = ratio of external calls to total calls
        return other_calls / total_calls
    
    def detect_data_clumps(self, code: str, language: str) -> List[str]:
        """Detect data clumps (groups of data that always appear together)"""
        # This is a simplified heuristic
        # Full analysis would require tracking parameter groups across methods
        
        clumps = []
        
        # Look for common patterns: multiple related parameters
        # Pattern: method(param1, param2, param3) where params are related
        # This is hard to detect statically, so we use a simple heuristic
        
        # For now, return empty list - this would require more sophisticated analysis
        # Could be enhanced with semantic analysis or pattern matching
        
        return clumps
    
    def has_long_parameter_list(self, code: str, language: str) -> bool:
        """Check if function has too many parameters"""
        param_count = self.count_parameters(code, language, 'method')
        # Threshold: more than 5 parameters is considered "long"
        return param_count > 5

