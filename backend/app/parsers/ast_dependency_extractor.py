"""
AST-based dependency extractor for Python and PHP
Uses built-in Python AST module for Python and improved regex for PHP
"""
import ast
import re
import logging
from typing import List, Dict, Set
from pathlib import Path

logger = logging.getLogger(__name__)


class ASTDependencyExtractor:
    """Extract dependencies using AST parsing (Python) and improved regex (PHP)"""
    
    def extract_dependencies(self, code: str, language: str, filepath: str = "") -> List[Dict]:
        """Extract dependencies from code
        
        Args:
            code: Source code
            language: 'python' or 'php'
            filepath: Optional file path for context
            
        Returns:
            List of dependencies with 'name' and 'type' keys
        """
        if language == 'python':
            return self._extract_python_ast_dependencies(code, filepath)
        elif language == 'php':
            return self._extract_php_dependencies(code)
        else:
            logger.warning(f"Unsupported language for AST extraction: {language}")
            return []
    
    def _extract_python_ast_dependencies(self, code: str, filepath: str) -> List[Dict]:
        """Extract dependencies from Python code using AST"""
        dependencies = []
        seen = set()  # Avoid duplicates
        
        try:
            # Remove leading indentation if code starts with indentation
            # This happens when extracting method/function code from classes
            lines = code.split('\n')
            if lines and lines[0].strip() and lines[0][0] in [' ', '\t']:
                # Code has leading indentation, remove it
                # Find minimum indentation (excluding empty lines)
                min_indent = float('inf')
                for line in lines:
                    if line.strip():  # Skip empty lines
                        indent = len(line) - len(line.lstrip())
                        min_indent = min(min_indent, indent)
                
                # Remove minimum indentation from all lines
                if min_indent > 0 and min_indent != float('inf'):
                    code = '\n'.join(line[min_indent:] if len(line) > min_indent else line for line in lines)
            
            tree = ast.parse(code, filename=filepath or '<string>')
            
            # Visitor to collect dependencies
            class DependencyVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.deps = []
                    self.seen = set()
                    self.current_class = None
                    self.current_method = None
                
                def visit_Import(self, node):
                    """Handle: import module"""
                    for alias in node.names:
                        dep_name = alias.name.split('.')[0]  # Get root module
                        key = ('import', dep_name)
                        if key not in self.seen:
                            self.seen.add(key)
                            self.deps.append({
                                'name': dep_name,
                                'type': 'import'
                            })
                
                def visit_ImportFrom(self, node):
                    """Handle: from module import ..."""
                    if node.module:
                        dep_name = node.module.split('.')[0]  # Get root module
                        key = ('import', dep_name)
                        if key not in self.seen:
                            self.seen.add(key)
                            self.deps.append({
                                'name': dep_name,
                                'type': 'import'
                            })
                        
                        # Also add specific imports
                        for alias in node.names:
                            if alias.name != '*':
                                full_name = f"{node.module}.{alias.name}" if node.module else alias.name
                                key = ('import', full_name)
                                if key not in self.seen:
                                    self.seen.add(key)
                                    self.deps.append({
                                        'name': full_name,
                                        'type': 'import'
                                    })
                
                def visit_ClassDef(self, node):
                    """Handle: class MyClass(Base1, Base2)"""
                    old_class = self.current_class
                    self.current_class = node.name
                    
                    # Extract base classes
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_name = base.id
                            key = ('extends', base_name)
                            if key not in self.seen:
                                self.seen.add(key)
                                self.deps.append({
                                    'name': base_name,
                                    'type': 'extends'
                                })
                        elif isinstance(base, ast.Attribute):
                            # Handle qualified names like SomeModule.BaseClass
                            base_name = self._get_qualified_name(base)
                            key = ('extends', base_name)
                            if key not in self.seen:
                                self.seen.add(key)
                                self.deps.append({
                                    'name': base_name,
                                    'type': 'extends'
                                })
                    
                    # Visit class body
                    self.generic_visit(node)
                    self.current_class = old_class
                
                def visit_FunctionDef(self, node):
                    """Track current method/function"""
                    old_method = self.current_method
                    self.current_method = node.name
                    self.generic_visit(node)
                    self.current_method = old_method
                
                def visit_Call(self, node):
                    """Handle: obj.method(), Class.method(), function()"""
                    # Extract function/method being called
                    if isinstance(node.func, ast.Name):
                        # Direct function call: func()
                        func_name = node.func.id
                        # Skip built-ins
                        if func_name not in ['print', 'len', 'str', 'int', 'float', 'bool', 'list', 'dict', 'set', 'tuple']:
                            key = ('calls', func_name)
                            if key not in self.seen:
                                self.seen.add(key)
                                self.deps.append({
                                    'name': func_name,
                                    'type': 'calls'
                                })
                    
                    elif isinstance(node.func, ast.Attribute):
                        # Method call: obj.method() or Class.method()
                        attr_name = node.func.attr
                        if isinstance(node.func.value, ast.Name):
                            obj_name = node.func.value.id
                            # Skip self, cls, super
                            if obj_name not in ['self', 'cls', 'super']:
                                full_name = f"{obj_name}.{attr_name}"
                                key = ('calls', full_name)
                                if key not in self.seen:
                                    self.seen.add(key)
                                    self.deps.append({
                                        'name': full_name,
                                        'type': 'calls'
                                    })
                        elif isinstance(node.func.value, ast.Attribute):
                            # Nested: obj.attr.method()
                            qualified = self._get_qualified_name(node.func.value)
                            full_name = f"{qualified}.{attr_name}"
                            key = ('calls', full_name)
                            if key not in self.seen:
                                self.seen.add(key)
                                self.deps.append({
                                    'name': full_name,
                                    'type': 'calls'
                                })
                    
                    self.generic_visit(node)
                
                def visit_Attribute(self, node):
                    """Handle attribute access: obj.attr (for static access)"""
                    # This is called for attribute access, but we mainly care about calls
                    self.generic_visit(node)
                
                def _get_qualified_name(self, node):
                    """Get fully qualified name from AST node"""
                    if isinstance(node, ast.Name):
                        return node.id
                    elif isinstance(node, ast.Attribute):
                        value = self._get_qualified_name(node.value)
                        return f"{value}.{node.attr}"
                    return ""
            
            visitor = DependencyVisitor()
            visitor.visit(tree)
            dependencies = visitor.deps
            
        except SyntaxError as e:
            logger.warning(f"Syntax error parsing Python code: {e}")
            # Fallback to regex-based extraction
            return self._extract_python_regex_fallback(code)
        except Exception as e:
            logger.error(f"Error extracting Python dependencies with AST: {e}", exc_info=True)
            # Fallback to regex-based extraction
            return self._extract_python_regex_fallback(code)
        
        return dependencies
    
    def _extract_python_regex_fallback(self, code: str) -> List[Dict]:
        """Fallback regex-based extraction for Python"""
        dependencies = []
        seen = set()
        
        # Import statements
        import_patterns = [
            r'^import\s+([^\s]+)',
            r'^from\s+([^\s]+)\s+import',
        ]
        for pattern in import_patterns:
            for match in re.finditer(pattern, code, re.MULTILINE):
                module_name = match.group(1).strip()
                key = ('import', module_name)
                if key not in seen:
                    seen.add(key)
                    dependencies.append({
                        'name': module_name,
                        'type': 'import'
                    })
        
        # Class inheritance
        class_pattern = r'class\s+\w+\s*\(([^)]+)\)'
        for match in re.finditer(class_pattern, code):
            bases = [b.strip() for b in match.group(1).split(',')]
            for base in bases:
                if base and base != 'object':
                    key = ('extends', base)
                    if key not in seen:
                        seen.add(key)
                        dependencies.append({
                            'name': base,
                            'type': 'extends'
                        })
        
        return dependencies
    
    def _extract_php_dependencies(self, code: str) -> List[Dict]:
        """Extract dependencies from PHP code using improved regex"""
        dependencies = []
        seen = set()
        
        # Extract use statements (namespaces)
        use_pattern = r'use\s+([^;]+);'
        for match in re.finditer(use_pattern, code):
            use_statement = match.group(1).strip()
            # Handle "use Namespace\Class as Alias"
            if ' as ' in use_statement:
                class_name = use_statement.split(' as ')[0].strip()
            else:
                class_name = use_statement.strip()
            
            key = ('import', class_name)
            if key not in seen:
                seen.add(key)
                dependencies.append({
                    'name': class_name,
                    'type': 'import'
                })
        
        # Extract extends
        extends_pattern = r'extends\s+([^\s{]+)'
        for match in re.finditer(extends_pattern, code):
            class_name = match.group(1).strip()
            key = ('extends', class_name)
            if key not in seen:
                seen.add(key)
                dependencies.append({
                    'name': class_name,
                    'type': 'extends'
                })
        
        # Extract implements
        implements_pattern = r'implements\s+([^{]+)'
        for match in re.finditer(implements_pattern, code):
            interfaces = [i.strip() for i in match.group(1).split(',')]
            for interface in interfaces:
                key = ('implements', interface)
                if key not in seen:
                    seen.add(key)
                    dependencies.append({
                        'name': interface,
                        'type': 'implements'
                    })
        
        # Extract method calls: $obj->method(), Class::method(), self::method()
        method_call_patterns = [
            r'\$(\w+)->(\w+)\s*\(',
            r'([A-Z]\w*(?:\\[A-Z]\w*)*)::(\w+)\s*\(',
            r'self::(\w+)\s*\(',
            r'static::(\w+)\s*\(',
            r'parent::(\w+)\s*\(',
        ]
        
        for pattern in method_call_patterns:
            for match in re.finditer(pattern, code):
                if '->' in match.group(0):
                    # $obj->method()
                    method_name = match.group(2)
                    key = ('calls', method_name)
                    if key not in seen:
                        seen.add(key)
                        dependencies.append({
                            'name': method_name,
                            'type': 'calls'
                        })
                elif '::' in match.group(0):
                    # Class::method() or self::method()
                    if len(match.groups()) >= 2:
                        class_name = match.group(1)
                        method_name = match.group(2)
                        full_name = f"{class_name}::{method_name}"
                        key = ('calls', full_name)
                        if key not in seen:
                            seen.add(key)
                            dependencies.append({
                                'name': full_name,
                                'type': 'calls'
                            })
                    else:
                        # self::method() or static::method()
                        method_name = match.group(1)
                        key = ('calls', method_name)
                        if key not in seen:
                            seen.add(key)
                            dependencies.append({
                                'name': method_name,
                                'type': 'calls'
                            })
        
        # Extract new Class() instantiations
        new_pattern = r'new\s+([A-Z]\w*(?:\\[A-Z]\w*)*)\s*\('
        for match in re.finditer(new_pattern, code):
            class_name = match.group(1).strip()
            key = ('import', class_name)
            if key not in seen:
                seen.add(key)
                dependencies.append({
                    'name': class_name,
                    'type': 'import'
                })
        
        return dependencies

