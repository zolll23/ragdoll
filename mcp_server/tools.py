"""
MCP Tools for CodeRAG
Provides code search, analysis, and refactoring tools
"""
import logging
import os
import sys
from typing import Any, Dict, List, Optional
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.core.database import SessionLocal
from app.services.search_service import SearchService
from app.models.database import Entity, Analysis, File, Project
from sqlalchemy import func

logger = logging.getLogger(__name__)


class CodeRAGTools:
    """Tools for code analysis and search"""
    
    def __init__(self):
        self.search_service = SearchService()
    
    async def get_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools"""
        return [
            {
                "name": "search_code",
                "description": "Search code using natural language query. Finds methods, classes, functions that match the query.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language search query (e.g., 'find methods for sending messages', 'classes with O(n^2) complexity')"
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Project ID to search in (optional, searches all projects if not specified)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 10, max: 50)",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "analyze_method",
                "description": "Get detailed analysis of a specific method, class, or function by entity ID or file path and name.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "integer",
                            "description": "Entity ID (if you know it)"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "File path (relative to project root)"
                        },
                        "entity_name": {
                            "type": "string",
                            "description": "Name of the method/class/function"
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Project ID (required if using file_path)"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "get_refactoring_suggestions",
                "description": "Get refactoring suggestions for a method or class, including similar code patterns and SOLID violations.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "integer",
                            "description": "Entity ID to analyze"
                        },
                        "similarity_threshold": {
                            "type": "number",
                            "description": "Minimum similarity score for similar code (0.0-1.0, default: 0.7)",
                            "default": 0.7,
                            "minimum": 0.0,
                            "maximum": 1.0
                        }
                    },
                    "required": ["entity_id"]
                }
            },
            {
                "name": "get_similar_code",
                "description": "Find similar code patterns for refactoring opportunities.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "integer",
                            "description": "Entity ID to find similar code for"
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Project ID to search in (optional, searches all projects if not specified)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of similar code blocks (default: 5, max: 20)",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 20
                        }
                    },
                    "required": ["entity_id"]
                }
            },
            {
                "name": "get_entity_details",
                "description": "Get full details about an entity including code, analysis, dependencies, and metrics.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "integer",
                            "description": "Entity ID"
                        }
                    },
                    "required": ["entity_id"]
                }
            },
            {
                "name": "list_projects",
                "description": "List all indexed projects with their status and statistics. Use this to see what projects are available and their details (ID, name, path, language, file counts, entity counts).",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_project_info",
                "description": "Get detailed information about a specific project by ID, including path, language, indexing status, and statistics.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "integer",
                            "description": "Project ID"
                        }
                    },
                    "required": ["project_id"]
                }
            },
            {
                "name": "get_capabilities",
                "description": "Get information about available capabilities, tools, and what questions can be answered. Use this when user asks about what you can do, your capabilities, available features, or help.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_entity_schema",
                "description": "Get detailed schema of Entity and Analysis data structures. This describes all available fields, metrics, and how to search by them. Use this to understand what data is available and how to formulate search queries.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """Call a tool by name with arguments"""
        db = SessionLocal()
        try:
            if name == "search_code":
                return await self._search_code(db, arguments)
            elif name == "analyze_method":
                return await self._analyze_method(db, arguments)
            elif name == "get_refactoring_suggestions":
                return await self._get_refactoring_suggestions(db, arguments)
            elif name == "get_similar_code":
                return await self._get_similar_code(db, arguments)
            elif name == "get_entity_details":
                return await self._get_entity_details(db, arguments)
            elif name == "list_projects":
                return await self._list_projects(db)
            elif name == "get_project_info":
                return await self._get_project_info(db, arguments)
            elif name == "get_capabilities":
                return await self._get_capabilities()
            elif name == "get_entity_schema":
                return await self._get_entity_schema()
            else:
                raise ValueError(f"Unknown tool: {name}")
        finally:
            db.close()
    
    async def _search_code(self, db, args: Dict[str, Any]) -> str:
        """Search code"""
        query = args.get("query", "")
        project_id = args.get("project_id")
        limit = min(args.get("limit", 10), 50)
        
        if not query:
            return json.dumps({"error": "Query is required"}, indent=2)
        
        results = self.search_service.search(
            db=db,
            query=query,
            project_id=project_id,
            limit=limit
        )
        
        formatted_results = []
        for result in results:
            entity = result.entity
            analysis = result.analysis
            
            formatted_results.append({
                "entity_id": entity.id,
                "name": entity.name,
                "type": entity.type,
                "file_path": entity.file_path,
                "start_line": entity.start_line,
                "end_line": entity.end_line,
                "description": analysis.description if analysis else "No analysis available",
                "complexity": analysis.complexity if analysis else None,
                "score": result.score,
                "match_type": result.match_type
            })
        
        return json.dumps({
            "query": query,
            "total": len(formatted_results),
            "results": formatted_results
        }, indent=2)
    
    async def _analyze_method(self, db, args: Dict[str, Any]) -> str:
        """Analyze a method/class/function"""
        entity_id = args.get("entity_id")
        file_path = args.get("file_path")
        entity_name = args.get("entity_name")
        project_id = args.get("project_id")
        
        entity = None
        
        if entity_id:
            entity = db.query(Entity).filter(Entity.id == entity_id).first()
        elif file_path and entity_name and project_id:
            # Find entity by file path and name
            file = db.query(File).join(Project).filter(
                File.path == file_path,
                Project.id == project_id
            ).first()
            if file:
                entity = db.query(Entity).filter(
                    Entity.file_id == file.id,
                    Entity.name == entity_name
                ).first()
        
        if not entity:
            return json.dumps({"error": "Entity not found"}, indent=2)
        
        file = db.query(File).filter(File.id == entity.file_id).first()
        analysis = db.query(Analysis).filter(Analysis.entity_id == entity.id).first()
        
        result = {
            "entity": {
                "id": entity.id,
                "name": entity.name,
                "type": entity.type,
                "file_path": file.path if file else "",
                "start_line": entity.start_line,
                "end_line": entity.end_line,
                "code": entity.code
            }
        }
        
        if analysis:
            result["analysis"] = {
                "description": analysis.description,
                "complexity": analysis.complexity,
                "complexity_explanation": analysis.complexity_explanation,
                "solid_violations": analysis.solid_violations or [],
                "design_patterns": analysis.design_patterns or [],
                "ddd_role": analysis.ddd_role,
                "mvc_role": analysis.mvc_role,
                "is_testable": analysis.is_testable,
                "testability_score": analysis.testability_score,
                "testability_issues": analysis.testability_issues or [],
                "lines_of_code": analysis.lines_of_code,
                "cyclomatic_complexity": analysis.cyclomatic_complexity,
                "cognitive_complexity": analysis.cognitive_complexity,
                "security_issues": analysis.security_issues or [],
                "n_plus_one_queries": analysis.n_plus_one_queries or []
            }
        else:
            result["analysis"] = None
        
        return json.dumps(result, indent=2)
    
    async def _get_refactoring_suggestions(self, db, args: Dict[str, Any]) -> str:
        """Get refactoring suggestions"""
        entity_id = args.get("entity_id")
        similarity_threshold = args.get("similarity_threshold", 0.7)
        
        entity = db.query(Entity).filter(Entity.id == entity_id).first()
        if not entity:
            return json.dumps({"error": "Entity not found"}, indent=2)
        
        analysis = db.query(Analysis).filter(Analysis.entity_id == entity_id).first()
        
        suggestions = {
            "entity_id": entity_id,
            "entity_name": entity.name,
            "suggestions": []
        }
        
        # SOLID violations
        if analysis and analysis.solid_violations:
            for violation in analysis.solid_violations:
                suggestions["suggestions"].append({
                    "type": "solid_violation",
                    "principle": violation.get("principle"),
                    "description": violation.get("description"),
                    "severity": violation.get("severity"),
                    "suggestion": violation.get("suggestion")
                })
        
        # Similar code (simplified - would need to call similar code endpoint)
        # For now, just return SOLID violations
        
        return json.dumps(suggestions, indent=2)
    
    async def _get_similar_code(self, db, args: Dict[str, Any]) -> str:
        """Get similar code patterns"""
        entity_id = args.get("entity_id")
        project_id = args.get("project_id")
        limit = min(args.get("limit", 5), 20)
        
        entity = db.query(Entity).filter(Entity.id == entity_id).first()
        if not entity:
            return json.dumps({"error": "Entity not found"}, indent=2)
        
        # This would need to call the similar code search endpoint
        # For now, return a placeholder
        return json.dumps({
            "entity_id": entity_id,
            "message": "Similar code search requires implementation of similarity algorithm",
            "note": "Use get_refactoring_suggestions for refactoring opportunities"
        }, indent=2)
    
    async def _get_entity_details(self, db, args: Dict[str, Any]) -> str:
        """Get full entity details"""
        entity_id = args.get("entity_id")
        
        entity = db.query(Entity).filter(Entity.id == entity_id).first()
        
        if not entity:
            return json.dumps({"error": "Entity not found"}, indent=2)
        
        file = db.query(File).filter(File.id == entity.file_id).first()
        analysis = db.query(Analysis).filter(Analysis.entity_id == entity_id).first()
        
        # Get dependencies
        from app.models.database import Dependency
        dependencies = db.query(Dependency).filter(Dependency.entity_id == entity_id).all()
        
        result = {
            "entity": {
                "id": entity.id,
                "name": entity.name,
                "type": entity.type,
                "file_path": file.path if file else "",
                "start_line": entity.start_line,
                "end_line": entity.end_line,
                "full_qualified_name": entity.full_qualified_name,
                "code": entity.code
            },
            "dependencies": [
                {
                    "type": dep.type,
                    "depends_on_name": dep.depends_on_name,
                    "depends_on_entity_id": dep.depends_on_entity_id
                }
                for dep in dependencies
            ]
        }
        
        if analysis:
            result["analysis"] = {
                "description": analysis.description,
                "complexity": analysis.complexity,
                "complexity_explanation": analysis.complexity_explanation,
                "solid_violations": analysis.solid_violations or [],
                "design_patterns": analysis.design_patterns or [],
                "ddd_role": analysis.ddd_role,
                "mvc_role": analysis.mvc_role,
                "is_testable": analysis.is_testable,
                "testability_score": analysis.testability_score,
                "testability_issues": analysis.testability_issues or [],
                "metrics": {
                    "lines_of_code": analysis.lines_of_code,
                    "cyclomatic_complexity": analysis.cyclomatic_complexity,
                    "cognitive_complexity": analysis.cognitive_complexity,
                    "max_nesting_depth": analysis.max_nesting_depth,
                    "parameter_count": analysis.parameter_count,
                    "coupling_score": analysis.coupling_score,
                    "cohesion_score": analysis.cohesion_score,
                    "security_issues": analysis.security_issues or [],
                    "n_plus_one_queries": analysis.n_plus_one_queries or [],
                    "is_god_object": analysis.is_god_object,
                    "feature_envy_score": analysis.feature_envy_score,
                    "long_parameter_list": analysis.long_parameter_list
                }
            }
        else:
            result["analysis"] = None
        
        return json.dumps(result, indent=2)
    
    async def _list_projects(self, db) -> str:
        """List all projects"""
        projects = db.query(Project).all()
        
        result = []
        for project in projects:
            result.append({
                "id": project.id,
                "name": project.name,
                "path": project.path,
                "language": project.language,
                "total_files": project.total_files,
                "indexed_files": project.indexed_files,
                "total_entities": project.total_entities,
                "is_indexing": project.is_indexing
            })
        
        return json.dumps({"projects": result}, indent=2)
    
    async def _get_project_info(self, db, args: Dict[str, Any]) -> str:
        """Get detailed information about a project"""
        project_id = args.get("project_id")
        
        if not project_id:
            return json.dumps({"error": "project_id is required"}, indent=2)
        
        project = db.query(Project).filter(Project.id == project_id).first()
        
        if not project:
            return json.dumps({"error": f"Project with ID {project_id} not found"}, indent=2)
        
        # Get file count
        file_count = db.query(func.count(File.id)).filter(File.project_id == project_id).scalar() or 0
        
        # Get entity count
        entity_count = db.query(func.count(Entity.id)).join(File).filter(
            File.project_id == project_id
        ).scalar() or 0
        
        result = {
            "id": project.id,
            "name": project.name,
            "path": project.path,
            "language": project.language,
            "total_files": project.total_files or file_count,
            "indexed_files": project.indexed_files or file_count,
            "total_entities": project.total_entities or entity_count,
            "is_indexing": project.is_indexing,
            "tokens_used": project.tokens_used or 0,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None
        }
        
        return json.dumps(result, indent=2)
    
    async def _get_capabilities(self) -> str:
        """Get information about available capabilities and tools"""
        capabilities = {
            "system": "Goose - AI-ассистент для анализа кода в системе CodeRAG",
            "description": "Я помогаю отвечать на вопросы о кодовой базе, используя различные инструменты для поиска и анализа кода.",
            "available_tools": [
                {
                    "name": "search_code",
                    "description": "Поиск кода по естественному языку",
                    "capabilities": [
                        "Находит методы, классы, функции, константы, enum-ы",
                        "Поддерживает семантический поиск по описаниям и коду",
                        "Ищет по ключевым словам и синонимам"
                    ],
                    "example_questions": [
                        "какой таймаут отправки письма?",
                        "какие статусы есть для email?",
                        "найди методы для отправки сообщений",
                        "классы с высокой сложностью"
                    ]
                },
                {
                    "name": "get_entity_details",
                    "description": "Получение детальной информации о сущности",
                    "capabilities": [
                        "Анализ конкретного класса, метода, функции или константы",
                        "Получение метрик сложности, описания, зависимостей",
                        "Просмотр полного кода сущности"
                    ],
                    "example_questions": [
                        "расскажи про класс EmailService",
                        "что делает метод sendEmail?",
                        "детали константы EMAIL_SEND_TIMEOUT"
                    ]
                },
                {
                    "name": "analyze_method",
                    "description": "Детальный анализ метода/класса/функции",
                    "capabilities": [
                        "Анализ сложности (O-нотация, цикломатическая, когнитивная)",
                        "Выявление нарушений SOLID принципов",
                        "Определение паттернов проектирования",
                        "Оценка тестируемости и проблем безопасности"
                    ],
                    "example_questions": [
                        "проанализируй метод sendWelcomeEmail",
                        "какая сложность у этого класса?",
                        "есть ли нарушения SOLID?"
                    ]
                },
                {
                    "name": "get_refactoring_suggestions",
                    "description": "Предложения по рефакторингу",
                    "capabilities": [
                        "Поиск похожих паттернов кода",
                        "Выявление нарушений SOLID принципов",
                        "Рекомендации по улучшению кода"
                    ],
                    "example_questions": [
                        "как можно улучшить этот метод?",
                        "есть ли похожий код для рефакторинга?"
                    ]
                },
                {
                    "name": "get_similar_code",
                    "description": "Поиск похожего кода",
                    "capabilities": [
                        "Находит похожие методы и классы по отпечатку кода",
                        "Помогает найти дублирование",
                        "Выявляет возможности для рефакторинга"
                    ],
                    "example_questions": [
                        "найди похожий код",
                        "есть ли дублирование?"
                    ]
                },
                {
                    "name": "list_projects",
                    "description": "Список проиндексированных проектов",
                    "capabilities": [
                        "Показывает все проекты с их статусом",
                        "Статистика: количество файлов, сущностей",
                        "Информация о языке и пути проекта"
                    ],
                    "example_questions": [
                        "какие проекты есть?",
                        "покажи список проектов"
                    ]
                },
                {
                    "name": "get_project_info",
                    "description": "Информация о конкретном проекте",
                    "capabilities": [
                        "Детали проекта: путь, язык, статус индексации",
                        "Статистика: количество файлов и сущностей",
                        "Информация о последней индексации"
                    ],
                    "example_questions": [
                        "информация о проекте с ID 3",
                        "статус индексации проекта"
                    ]
                }
            ],
            "what_i_can_do": [
                "Отвечать на вопросы о функциональности кода",
                "Находить конкретные константы, методы, классы",
                "Объяснять, как работает код",
                "Предлагать улучшения и рефакторинг",
                "Анализировать сложность и качество кода",
                "Искать похожие паттерны в кодовой базе",
                "Определять нарушения SOLID принципов",
                "Оценивать тестируемость кода",
                "Выявлять проблемы безопасности"
            ]
        }
        return json.dumps(capabilities, indent=2, ensure_ascii=False)
    
    async def _get_entity_schema(self) -> str:
        """Get detailed schema of Entity and Analysis data structures"""
        schema = {
            "description": "Структура данных о сущностях кода (Entity) и их анализе (Analysis). Эта информация помогает понять, какие данные доступны и как по ним можно искать.",
            "entity": {
                "description": "Базовая информация о сущности кода (класс, метод, функция, константа, enum)",
                "fields": {
                    "id": {"type": "integer", "description": "Уникальный идентификатор сущности"},
                    "type": {"type": "string", "description": "Тип сущности: 'class', 'method', 'function', 'constant', 'enum'", "searchable": True, "example_queries": ["найди все классы", "покажи методы", "найди константы"]},
                    "name": {"type": "string", "description": "Имя сущности", "searchable": True, "example_queries": ["найди EmailService", "метод sendEmail"]},
                    "full_qualified_name": {"type": "string", "description": "Полное квалифицированное имя (например, 'ClassName.method_name')", "searchable": True},
                    "file_path": {"type": "string", "description": "Путь к файлу относительно корня проекта", "searchable": True},
                    "start_line": {"type": "integer", "description": "Номер строки начала"},
                    "end_line": {"type": "integer", "description": "Номер строки конца"},
                    "visibility": {"type": "string", "description": "Видимость: 'public', 'private', 'protected'", "searchable": True},
                    "code": {"type": "string", "description": "Полный код сущности", "searchable": True}
                }
            },
            "analysis": {
                "description": "Детальный анализ сущности с метриками, сложностью, архитектурными ролями и т.д.",
                "fields": {
                    "description": {"type": "string", "description": "Описание функциональности сущности (2-3 предложения)", "searchable": True, "example_queries": ["найди код для отправки email", "что делает метод отправки"]},
                    "complexity": {"type": "string", "description": "Временная сложность в O-нотации: 'O(1)', 'O(log n)', 'O(n)', 'O(n log n)', 'O(n^2)', 'O(n^3)', 'O(2^n)', 'O(n!)'", "searchable": True, "example_queries": ["найди методы со сложностью O(n^2)", "классы с O(n!) сложностью", "методы со сложностью NP"]},
                    "complexity_numeric": {"type": "float", "description": "Числовое значение сложности для сортировки: 1=O(1), 2=O(log n), 3=O(n), 4=O(n log n), 5=O(n^2), 6=O(n^3), 7=O(2^n), 8=O(n!)", "searchable": True, "range_queries": True},
                    "complexity_explanation": {"type": "string", "description": "Объяснение почему такая сложность"},
                    "ddd_role": {"type": "string", "description": "Роль в Domain-Driven Design: 'Entity', 'ValueObject', 'Aggregate', 'Service', 'Repository', 'Factory' и т.д.", "searchable": True, "example_queries": ["найди все Repository", "покажи Entity в DDD", "какие Service есть?"]},
                    "mvc_role": {"type": "string", "description": "Роль в MVC архитектуре: 'Controller', 'Model', 'View', 'Service', 'Repository' и т.д.", "searchable": True, "example_queries": ["найди все Controller", "покажи Model классы", "какие Service есть?"]},
                    "design_patterns": {"type": "array", "description": "Список паттернов проектирования (например, ['Factory', 'Strategy', 'Observer'])", "searchable": True, "example_queries": ["найди код с паттерном Factory", "где используется Strategy?"]},
                    "solid_violations": {"type": "array", "description": "Список нарушений SOLID принципов", "searchable": True, "example_queries": ["найди нарушения Single Responsibility", "где нарушается Liskov Substitution?"]},
                    "is_testable": {"type": "boolean", "description": "Можно ли тестировать", "searchable": True},
                    "testability_score": {"type": "float", "description": "Оценка тестируемости (0.0-1.0)", "searchable": True, "range_queries": True},
                    "testability_issues": {"type": "array", "description": "Проблемы с тестируемостью"},
                    "lines_of_code": {"type": "integer", "description": "Количество строк кода", "searchable": True, "range_queries": True},
                    "cyclomatic_complexity": {"type": "integer", "description": "Цикломатическая сложность", "searchable": True, "range_queries": True, "example_queries": ["найди методы с высокой цикломатической сложностью"]},
                    "cognitive_complexity": {"type": "integer", "description": "Когнитивная сложность", "searchable": True, "range_queries": True},
                    "max_nesting_depth": {"type": "integer", "description": "Максимальная глубина вложенности", "searchable": True, "range_queries": True},
                    "parameter_count": {"type": "integer", "description": "Количество параметров", "searchable": True, "range_queries": True},
                    "coupling_score": {"type": "float", "description": "Оценка связанности (0.0-1.0)", "searchable": True, "range_queries": True},
                    "cohesion_score": {"type": "float", "description": "Оценка связности (0.0-1.0)", "searchable": True, "range_queries": True},
                    "afferent_coupling": {"type": "integer", "description": "Входящие зависимости (сколько классов зависят от этого)", "searchable": True, "range_queries": True},
                    "efferent_coupling": {"type": "integer", "description": "Исходящие зависимости (от скольких классов зависит)", "searchable": True, "range_queries": True},
                    "space_complexity": {"type": "string", "description": "Пространственная сложность (например, 'O(1)', 'O(n)')", "searchable": True},
                    "n_plus_one_queries": {"type": "array", "description": "Список N+1 запросов к БД", "searchable": True, "example_queries": ["найди код с N+1 проблемой"]},
                    "hot_path_detected": {"type": "boolean", "description": "Обнаружен ли hot path (часто выполняемый код)", "searchable": True},
                    "security_issues": {"type": "array", "description": "Проблемы безопасности", "searchable": True, "example_queries": ["найди проблемы безопасности", "где есть уязвимости?"]},
                    "hardcoded_secrets": {"type": "array", "description": "Хардкоженные секреты", "searchable": True},
                    "insecure_dependencies": {"type": "array", "description": "Небезопасные зависимости", "searchable": True},
                    "is_god_object": {"type": "boolean", "description": "Является ли God Object (слишком много ответственности)", "searchable": True, "example_queries": ["найди God Objects"]},
                    "feature_envy_score": {"type": "float", "description": "Оценка Feature Envy (0.0-1.0)", "searchable": True, "range_queries": True},
                    "data_clumps": {"type": "array", "description": "Группы данных, которые часто используются вместе", "searchable": True},
                    "long_parameter_list": {"type": "boolean", "description": "Длинный список параметров", "searchable": True},
                    "keywords": {"type": "string", "description": "Ключевые слова для семантического поиска (синонимы, связанные термины)", "searchable": True}
                }
            },
            "search_guidelines": {
                "description": "Как правильно формулировать поисковые запросы",
                "tips": [
                    "Для поиска по сложности используйте: 'найди методы со сложностью O(n^2)', 'классы с O(n!) сложностью', 'методы со сложностью NP'",
                    "Для поиска по DDD ролям: 'найди все Repository', 'покажи Entity в DDD', 'какие Service есть?'",
                    "Для поиска по MVC ролям: 'найди все Controller', 'покажи Model классы', 'какие Service есть?'",
                    "Для поиска по паттернам: 'найди код с паттерном Factory', 'где используется Strategy?'",
                    "Для поиска по метрикам: 'найди методы с высокой цикломатической сложностью', 'классы с низкой тестируемостью'",
                    "Для поиска по проблемам: 'найди нарушения SOLID', 'найди God Objects', 'найди код с N+1 проблемой'",
                    "Система автоматически распознает эти паттерны в запросах и применяет соответствующие фильтры"
                ]
            }
        }
        return json.dumps(schema, indent=2, ensure_ascii=False)