import os
import re
from typing import List, Dict, Optional
from pathlib import Path
import logging

from app.parsers.ast_dependency_extractor import ASTDependencyExtractor

logger = logging.getLogger(__name__)


class CodeParser:
    """Parser for PHP and Python code using regex-based approach (Tree-sitter can be added later)"""
    
    def __init__(self):
        self.language_parsers = {
            'python': self._parse_python,
            'php': self._parse_php
        }
        self.ast_extractor = ASTDependencyExtractor()
    
    def parse_file(self, filepath: str, language: str) -> List[Dict]:
        """Parse file and extract all entities"""
        
        if language not in self.language_parsers:
            raise ValueError(f"Unsupported language: {language}")
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
        except Exception as e:
            logger.error(f"Error reading file {filepath}: {e}")
            return []
        
        parser_func = self.language_parsers[language]
        entities = parser_func(code, filepath)
        
        return entities
    
    def _parse_python(self, code: str, filepath: str) -> List[Dict]:
        """Extract classes, methods, functions from Python code"""
        entities = []
        lines = code.split('\n')
        
        current_class = None
        class_start = None
        
        for i, line in enumerate(lines, 1):
            # Class definition
            class_match = re.match(r'^\s*(class\s+(\w+))', line)
            if class_match:
                if current_class:
                    # Close previous class
                    entities.append({
                        'type': 'class',
                        'name': current_class['name'],
                        'start_line': current_class['start'],
                        'end_line': i - 1,
                        'code': '\n'.join(lines[current_class['start']-1:i-1]),
                        'visibility': 'public',
                        'full_qualified_name': current_class['name']
                    })
                
                current_class = {
                    'name': class_match.group(2),
                    'start': i
                }
                continue
            
            # Method or function definition
            method_match = re.match(r'^\s*(def\s+(\w+)\s*\([^)]*\)\s*:?)', line)
            if method_match:
                method_name = method_match.group(2)
                
                # Find method end
                end_line = self._find_block_end(lines, i, 'python')
                
                method_code = '\n'.join(lines[i-1:end_line])
                
                # Determine if it's a method or function
                is_method = current_class is not None
                
                # Determine visibility
                visibility = 'private' if method_name.startswith('__') and not method_name.endswith('__') else \
                            'protected' if method_name.startswith('_') else 'public'
                
                full_name = f"{current_class['name']}.{method_name}" if is_method else method_name
                
                entities.append({
                    'type': 'method' if is_method else 'function',
                    'name': method_name,
                    'start_line': i,
                    'end_line': end_line,
                    'code': method_code,
                    'visibility': visibility,
                    'full_qualified_name': full_name
                })
        
        # Add last class if exists
        if current_class:
            # Find the actual end of the class by finding the matching closing brace or dedent
            class_end_line = self._find_block_end(lines, current_class['start'], 'python')
            entities.append({
                'type': 'class',
                'name': current_class['name'],
                'start_line': current_class['start'],
                'end_line': class_end_line,
                'code': '\n'.join(lines[current_class['start']-1:class_end_line]),
                'visibility': 'public',
                'full_qualified_name': current_class['name']
            })
        
        # Track which lines are inside classes to avoid extracting class-level constants as module-level
        class_lines = set()
        for entity in entities:
            if entity['type'] == 'class':
                for line_num in range(entity['start_line'], entity['end_line'] + 1):
                    class_lines.add(line_num)
        
        # Extract constants and dicts (module-level only, not inside classes)
        for i, line in enumerate(lines, 1):
            if i in class_lines:
                continue  # Skip lines inside classes
            
            # Match: CONSTANT_NAME = value (simple constants)
            const_match = re.match(r'^\s*([A-Z][A-Z0-9_]+)\s*=\s*(.+)$', line)
            if const_match:
                const_name = const_match.group(1)
                const_value = const_match.group(2).strip()
                
                # Check if it's a dict (starts with {)
                if const_value.startswith('{'):
                    # This is a dict, handle it separately
                    dict_name = const_name
                    # Find matching closing brace
                    brace_count = 0
                    end_line = i
                    for j in range(i - 1, len(lines)):
                        for char in lines[j]:
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end_line = j + 1
                                    break
                        if brace_count == 0:
                            break
                    
                    dict_code = '\n'.join(lines[i-1:end_line])
                    entities.append({
                        'type': 'constant',  # Treat dicts as constants
                        'name': dict_name,
                        'start_line': i,
                        'end_line': end_line,
                        'code': dict_code,
                        'visibility': 'public',
                        'full_qualified_name': dict_name
                    })
                else:
                    # Simple constant
                    # Get full constant definition (may span multiple lines for complex values)
                    end_line = i
                    if const_value.endswith('\\') or (const_value.startswith('[') and not const_value.endswith(']')):
                        # Multi-line constant, find end
                        for j in range(i, len(lines)):
                            if j + 1 in class_lines:
                                break  # Stop if we hit a class
                            if lines[j].strip() and not lines[j].strip().startswith('#'):
                                if ']' in lines[j] or not lines[j].strip().endswith('\\'):
                                    end_line = j + 1
                                    break
                    
                    const_code = '\n'.join(lines[i-1:end_line])
                    entities.append({
                        'type': 'constant',
                        'name': const_name,
                        'start_line': i,
                        'end_line': end_line,
                        'code': const_code,
                        'visibility': 'public',
                        'full_qualified_name': const_name
                    })
        
        return entities
    
    def _parse_php(self, code: str, filepath: str) -> List[Dict]:
        """Extract classes, methods, functions from PHP code"""
        entities = []
        lines = code.split('\n')
        
        current_class = None
        current_namespace = None
        
        # Extract namespace
        namespace_match = re.search(r'namespace\s+([^;]+)', code)
        if namespace_match:
            current_namespace = namespace_match.group(1).strip()
        
        for i, line in enumerate(lines, 1):
            # Class definition
            class_match = re.match(r'^\s*(class\s+(\w+))', line)
            if class_match:
                if current_class:
                    entities.append({
                        'type': 'class',
                        'name': current_class['name'],
                        'start_line': current_class['start'],
                        'end_line': i - 1,
                        'code': '\n'.join(lines[current_class['start']-1:i-1]),
                        'visibility': 'public',
                        'full_qualified_name': f"{current_namespace}\\{current_class['name']}" if current_namespace else current_class['name']
                    })
                
                current_class = {
                    'name': class_match.group(2),
                    'start': i
                }
                continue
            
            # Method definition
            # Match: (public|private|protected)? (static)? function methodName(...)
            method_match = re.match(r'^\s*(public|private|protected)?\s*(static)?\s*function\s+(\w+)\s*\([^)]*\)', line)
            if method_match:
                visibility = method_match.group(1) or 'public'
                method_name = method_match.group(3)  # Group 3 is the method name
                
                # Find method end
                end_line = self._find_block_end(lines, i, 'php')
                
                method_code = '\n'.join(lines[i-1:end_line])
                
                full_name = f"{current_namespace}\\{current_class['name']}::{method_name}" if current_class and current_namespace else \
                           f"{current_class['name']}::{method_name}" if current_class else method_name
                
                entities.append({
                    'type': 'method',
                    'name': method_name,
                    'start_line': i,
                    'end_line': end_line,
                    'code': method_code,
                    'visibility': visibility,
                    'full_qualified_name': full_name
                })
        
        # Add last class if exists
        if current_class:
            # Find the actual end of the class by finding the matching closing brace
            class_end_line = self._find_block_end(lines, current_class['start'], 'php')
            entities.append({
                'type': 'class',
                'name': current_class['name'],
                'start_line': current_class['start'],
                'end_line': class_end_line,
                'code': '\n'.join(lines[current_class['start']-1:class_end_line]),
                'visibility': 'public',
                'full_qualified_name': f"{current_namespace}\\{current_class['name']}" if current_namespace else current_class['name']
            })
        
        # Track which lines are inside classes to properly associate constants with classes
        # We need to build this map AFTER extracting classes but BEFORE extracting constants
        class_lines = {}
        for entity in entities:
            if entity['type'] == 'class':
                class_full_name = entity['full_qualified_name']
                for line_num in range(entity['start_line'], entity['end_line'] + 1):
                    class_lines[line_num] = class_full_name
        
        # Extract constants (const CONSTANT_NAME = value or define('CONSTANT_NAME', value))
        for i, line in enumerate(lines, 1):
            # Match: const CONSTANT_NAME = value;
            const_match = re.match(r'^\s*const\s+([A-Z][A-Z0-9_]+)\s*=\s*(.+?);', line)
            if const_match:
                const_name = const_match.group(1)
                const_value = const_match.group(2).strip()
                
                # Check if constant is inside a class
                class_name = class_lines.get(i)
                if class_name:
                    # Constant is inside a class, use ClassName::CONSTANT_NAME format
                    full_name = f"{class_name}::{const_name}"
                else:
                    # Module-level constant
                    full_name = f"{current_namespace}\\{const_name}" if current_namespace else const_name
                
                # Extract comments before the constant (docblock or single-line)
                comment_lines = []
                j = i - 1
                while j > 0:
                    prev_line = lines[j - 1].strip()
                    # Match docblock comment /** ... */
                    if prev_line.startswith('/**') or prev_line.startswith('*'):
                        comment_lines.insert(0, prev_line)
                        if prev_line.startswith('/**'):
                            break
                    # Match single-line comment //
                    elif prev_line.startswith('//'):
                        comment_lines.insert(0, prev_line)
                        break
                    # Match single-line comment #
                    elif prev_line.startswith('#'):
                        comment_lines.insert(0, prev_line)
                        break
                    # Stop if we hit non-comment, non-empty line
                    elif prev_line and not prev_line.startswith('*'):
                        break
                    j -= 1
                
                # Combine comment and constant code
                code_with_comment = '\n'.join(comment_lines + [line.strip()]) if comment_lines else line.strip()
                
                entities.append({
                    'type': 'constant',
                    'name': const_name,
                    'start_line': max(1, i - len(comment_lines)) if comment_lines else i,
                    'end_line': i,
                    'code': code_with_comment,
                    'visibility': 'public',
                    'full_qualified_name': full_name,
                    'const_value': const_value  # Store value for better search
                })
            
            # Match: define('CONSTANT_NAME', value);
            define_match = re.match(r"^\s*define\s*\(\s*['\"]([A-Z][A-Z0-9_]+)['\"]\s*,\s*(.+?)\s*\);", line)
            if define_match:
                const_name = define_match.group(1)
                const_value = define_match.group(2).strip()
                full_name = f"{current_namespace}\\{const_name}" if current_namespace else const_name
                
                # Extract comments before the constant
                comment_lines = []
                j = i - 1
                while j > 0:
                    prev_line = lines[j - 1].strip()
                    if prev_line.startswith('/**') or prev_line.startswith('*'):
                        comment_lines.insert(0, prev_line)
                        if prev_line.startswith('/**'):
                            break
                    elif prev_line.startswith('//'):
                        comment_lines.insert(0, prev_line)
                        break
                    elif prev_line.startswith('#'):
                        comment_lines.insert(0, prev_line)
                        break
                    elif prev_line and not prev_line.startswith('*'):
                        break
                    j -= 1
                
                code_with_comment = '\n'.join(comment_lines + [line.strip()]) if comment_lines else line.strip()
                
                entities.append({
                    'type': 'constant',
                    'name': const_name,
                    'start_line': max(1, i - len(comment_lines)) if comment_lines else i,
                    'end_line': i,
                    'code': code_with_comment,
                    'visibility': 'public',
                    'full_qualified_name': full_name
                })
        
        # Extract Enum values (PHP 8.1+)
        current_enum = None
        for i, line in enumerate(lines, 1):
            # Match: enum EnumName { or enum EnumName: Type { or enum EnumName: Type\n{
            # Handle both single-line and multi-line enum declarations
            enum_match = re.match(r'^\s*enum\s+(\w+)(?::\s*\w+)?\s*\{?', line)
            if enum_match and not current_enum:
                # Check if opening brace is on same line or next line
                enum_name = enum_match.group(1)
                if '{' in line:
                    # Opening brace on same line
                    current_enum = {
                        'name': enum_name,
                        'start': i
                    }
                else:
                    # Opening brace should be on next line
                    # Check next line for opening brace
                    if i < len(lines) and '{' in lines[i]:
                        current_enum = {
                            'name': enum_name,
                            'start': i
                        }
            elif current_enum and '{' in line and current_enum['start'] == i - 1:
                # Opening brace on next line after enum declaration
                # Update start to include the brace line
                current_enum['start'] = i
                continue
            elif current_enum and enum_match:
                # New enum found, close previous one
                entities.append({
                    'type': 'class',  # Treat enum as class-like
                    'name': current_enum['name'],
                    'start_line': current_enum['start'],
                    'end_line': i - 1,
                    'code': '\n'.join(lines[current_enum['start']-1:i-1]),
                    'visibility': 'public',
                    'full_qualified_name': f"{current_namespace}\\{current_enum['name']}" if current_namespace else current_enum['name']
                })
                
                if '{' in line:
                    current_enum = {
                        'name': enum_match.group(1),
                        'start': i
                    }
                else:
                    current_enum = {
                        'name': enum_match.group(1),
                        'start': i
                    }
                continue
            
            # Match: case EnumValue; or case EnumValue = 'value'; (inside enum)
            if current_enum:
                case_match = re.match(r'^\s*case\s+(\w+)(?:\s*=\s*[^;]+)?\s*;', line)
                if case_match:
                    case_name = case_match.group(1)
                    full_name = f"{current_namespace}\\{current_enum['name']}::{case_name}" if current_namespace else f"{current_enum['name']}::{case_name}"
                    
                    # Extract comments before the enum case
                    comment_lines = []
                    j = i - 1
                    while j > 0:
                        prev_line = lines[j - 1].strip()
                        if prev_line.startswith('/**') or prev_line.startswith('*'):
                            comment_lines.insert(0, prev_line)
                            if prev_line.startswith('/**'):
                                break
                        elif prev_line.startswith('//'):
                            comment_lines.insert(0, prev_line)
                            break
                        elif prev_line.startswith('#'):
                            comment_lines.insert(0, prev_line)
                            break
                        elif prev_line and not prev_line.startswith('*'):
                            break
                        j -= 1
                    
                    code_with_comment = '\n'.join(comment_lines + [line.strip()]) if comment_lines else line.strip()
                    
                    entities.append({
                        'type': 'constant',  # Enum cases are like constants
                        'name': case_name,
                        'start_line': max(1, i - len(comment_lines)) if comment_lines else i,
                        'end_line': i,
                        'code': code_with_comment,
                        'visibility': 'public',
                        'full_qualified_name': full_name
                    })
        
        # Add last enum if exists
        if current_enum:
            # Find the actual end of the enum by finding the matching closing brace
            enum_end_line = self._find_block_end(lines, current_enum['start'], 'php')
            entities.append({
                'type': 'class',
                'name': current_enum['name'],
                'start_line': current_enum['start'],
                'end_line': enum_end_line,
                'code': '\n'.join(lines[current_enum['start']-1:enum_end_line]),
                'visibility': 'public',
                'full_qualified_name': f"{current_namespace}\\{current_enum['name']}" if current_namespace else current_enum['name']
            })
        
        return entities
    
    def extract_dependencies(self, code: str, language: str, entity_code: str) -> List[Dict]:
        """Extract dependencies (classes, methods, functions) used in code
        Uses AST-based extractor for better accuracy (no LLM needed)
        """
        # Use AST-based extractor for better accuracy
        return self.ast_extractor.extract_dependencies(entity_code, language, code)
    
    def _extract_php_dependencies(self, code: str) -> List[Dict]:
        """Extract dependencies from PHP code"""
        dependencies = []
        
        # Extract use/import statements
        use_pattern = r'use\s+([^;]+);'
        for match in re.finditer(use_pattern, code):
            class_name = match.group(1).strip()
            # Remove 'as' alias if present
            if ' as ' in class_name:
                class_name = class_name.split(' as ')[0].strip()
            dependencies.append({
                'name': class_name,
                'type': 'import'
            })
        
        # Extract extends/implements
        extends_pattern = r'extends\s+([^\s{]+)'
        for match in re.finditer(extends_pattern, code):
            class_name = match.group(1).strip()
            dependencies.append({
                'name': class_name,
                'type': 'extends'
            })
        
        implements_pattern = r'implements\s+([^{]+)'
        for match in re.finditer(implements_pattern, code):
            interfaces = [i.strip() for i in match.group(1).split(',')]
            for interface in interfaces:
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
                    # $obj->method() - we can't determine class, but we know method name
                    method_name = match.group(2)
                    dependencies.append({
                        'name': method_name,
                        'type': 'calls'
                    })
                elif '::' in match.group(0):
                    # Class::method() or self::method()
                    if match.lastindex >= 2:
                        class_name = match.group(1)
                        method_name = match.group(2)
                        dependencies.append({
                            'name': f"{class_name}::{method_name}",
                            'type': 'calls'
                        })
                    else:
                        # self::method() or static::method()
                        method_name = match.group(1)
                        dependencies.append({
                            'name': method_name,
                            'type': 'calls'
                        })
        
        # Extract new Class() instantiations
        new_pattern = r'new\s+([A-Z]\w*(?:\\[A-Z]\w*)*)\s*\('
        for match in re.finditer(new_pattern, code):
            class_name = match.group(1).strip()
            dependencies.append({
                'name': class_name,
                'type': 'import'
            })
        
        # Extract ::class references (PHP 5.5+)
        class_ref_pattern = r'([A-Z]\w*(?:\\[A-Z]\w*)*)::class'
        for match in re.finditer(class_ref_pattern, code):
            class_name = match.group(1).strip()
            dependencies.append({
                'name': class_name,
                'type': 'import'
            })
        
        # Extract static property access: Class::$property
        static_prop_pattern = r'([A-Z]\w*(?:\\[A-Z]\w*)*)::\$(\w+)'
        for match in re.finditer(static_prop_pattern, code):
            class_name = match.group(1).strip()
            dependencies.append({
                'name': class_name,
                'type': 'import'
            })
        
        return dependencies
    
    def _extract_python_dependencies(self, code: str) -> List[Dict]:
        """Extract dependencies from Python code"""
        dependencies = []
        
        # Extract import statements
        import_patterns = [
            r'import\s+([^\s]+)',
            r'from\s+([^\s]+)\s+import',
        ]
        
        for pattern in import_patterns:
            for match in re.finditer(pattern, code):
                module_name = match.group(1).strip()
                dependencies.append({
                    'name': module_name,
                    'type': 'import'
                })
        
        # Extract class inheritance
        class_pattern = r'class\s+\w+\s*\(([^)]+)\)'
        for match in re.finditer(class_pattern, code):
            bases = [b.strip() for b in match.group(1).split(',')]
            for base in bases:
                if base and base != 'object':
                    dependencies.append({
                        'name': base,
                        'type': 'extends'
                    })
        
        # Extract method calls: obj.method(), Class.method(), self.method()
        method_call_patterns = [
            r'(\w+)\.(\w+)\s*\(',
            r'([A-Z]\w+)\.(\w+)\s*\(',
        ]
        
        for pattern in method_call_patterns:
            for match in re.finditer(pattern, code):
                obj_name = match.group(1)
                method_name = match.group(2)
                # Skip if it's a built-in or common pattern
                if obj_name not in ['self', 'super', 'cls']:
                    dependencies.append({
                        'name': f"{obj_name}.{method_name}",
                        'type': 'calls'
                    })
        
        return dependencies
    
    def _find_block_end(self, lines: List[str], start_line: int, language: str) -> int:
        """Find the end of a code block"""
        indent_level = len(lines[start_line - 1]) - len(lines[start_line - 1].lstrip())
        i = start_line
        
        while i < len(lines):
            line = lines[i]
            if not line.strip():
                i += 1
                continue
            
            current_indent = len(line) - len(line.lstrip())
            
            # For Python: same or less indent means end of block
            if language == 'python':
                if current_indent <= indent_level and line.strip():
                    return i
            # For PHP: look for closing brace
            elif language == 'php':
                if line.strip() == '}':
                    # Check if it's the matching brace
                    open_count = '\n'.join(lines[start_line - 1:i + 1]).count('{')
                    close_count = '\n'.join(lines[start_line - 1:i + 1]).count('}')
                    if close_count >= open_count:
                        return i + 1
            
            i += 1
        
        return len(lines)

