import logging
import json
import re
from typing import List, Dict, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, cast, String

from app.models.database import Project, Entity, Analysis, File, Dependency
from app.api.models.schemas import SearchResult, EntityResponse, AnalysisResponse
from app.services.embedding_service import EmbeddingService
from app.services.qdrant_service import QdrantService
from app.agents.analyzer import CodeAnalyzer

logger = logging.getLogger(__name__)


class QueryAnalyzer:
    """Analyze search query to determine search strategy"""
    
    def __init__(self):
        try:
            self.analyzer = CodeAnalyzer()
        except Exception as e:
            logger.warning(f"Failed to initialize CodeAnalyzer for query analysis: {e}")
            self.analyzer = None
    
    def analyze_query(self, query: str, use_llm: bool = True) -> Dict:
        """Analyze query and extract structured filters
        
        Args:
            query: Search query
            use_llm: If True, use LLM to enhance query understanding (for MVC/DDD roles)
        """
        filters = {
            'complexity_filter': None,
            'solid_filter': None,
            'testability_filter': None,
            'pattern_filter': None,
            'entity_type_filter': None,  # Filter by entity type (method, class, function)
            'mvc_role_filter': None,  # Filter by MVC role (Controller, Model, View, Service, Repository, etc.)
            'ddd_role_filter': None,  # Filter by DDD role (Entity, ValueObject, Aggregate, Service, Repository, etc.)
            'semantic_query': query
        }
        
        query_lower = query.lower()
        
        # Entity type filters (English and Russian)
        if 'метод' in query_lower or 'method' in query_lower:
            filters['entity_type_filter'] = 'method'
        elif 'класс' in query_lower or 'class' in query_lower:
            filters['entity_type_filter'] = 'class'
        elif 'функция' in query_lower or 'function' in query_lower:
            filters['entity_type_filter'] = 'function'
        elif 'enum' in query_lower or 'перечислен' in query_lower:
            filters['entity_type_filter'] = 'enum'
        elif 'констант' in query_lower or 'constant' in query_lower:
            filters['entity_type_filter'] = 'constant'
        
        # MVC role filters (heuristic-based)
        mvc_keywords = {
            'controller': ['контроллер', 'controller', 'контроллеры', 'controllers'],
            'model': ['модель', 'model', 'модели', 'models'],
            'view': ['представление', 'view', 'представления', 'views'],
            'service': ['сервис', 'service', 'сервисы', 'services'],
            'repository': ['репозиторий', 'repository', 'репозитории', 'repositories'],
        }
        for role, keywords in mvc_keywords.items():
            if any(kw in query_lower for kw in keywords):
                filters['mvc_role_filter'] = role.capitalize()
                break
        
        # DDD role filters (heuristic-based)
        ddd_keywords = {
            'Entity': ['сущность', 'entity', 'entities', 'сущности'],
            'ValueObject': ['объект-значение', 'value object', 'value objects', 'объекты-значения'],
            'Aggregate': ['агрегат', 'aggregate', 'агрегаты', 'aggregates'],
            'Service': ['сервис', 'service', 'сервисы', 'services'],
            'Repository': ['репозиторий', 'repository', 'репозитории', 'repositories'],
            'Factory': ['фабрика', 'factory', 'фабрики', 'factories'],
        }
        for role, keywords in ddd_keywords.items():
            if any(kw in query_lower for kw in keywords):
                filters['ddd_role_filter'] = role
                break
        
        # Use LLM to enhance query understanding for complex queries
        if use_llm and self.analyzer and self.analyzer.client:
            try:
                llm_filters = self._analyze_query_with_llm(query)
                # Merge LLM results, prioritizing LLM if it found something
                if llm_filters.get('mvc_role_filter'):
                    filters['mvc_role_filter'] = llm_filters['mvc_role_filter']
                if llm_filters.get('ddd_role_filter'):
                    filters['ddd_role_filter'] = llm_filters['ddd_role_filter']
                if llm_filters.get('entity_type_filter') and not filters.get('entity_type_filter'):
                    filters['entity_type_filter'] = llm_filters['entity_type_filter']
            except Exception as e:
                logger.warning(f"LLM query analysis failed: {e}, using heuristic only")
        
        # Complexity filters (English and Russian)
        # Check for specific complexity patterns first (most specific)
        if 'o(n!)' in query_lower or 'o(n!)' in query_lower or 'factorial' in query_lower or 'факториальн' in query_lower or ('np' in query_lower and 'сложност' in query_lower):
            # NP-complete problems are often factorial or exponential
            filters['complexity_filter'] = {'min': 8, 'max': 8}  # O(n!)
        elif 'o(2^n)' in query_lower or 'o(2^' in query_lower or 'exponential' in query_lower or 'экспоненциальн' in query_lower:
            filters['complexity_filter'] = {'min': 7, 'max': 7}  # O(2^n)
        elif 'o(n^3)' in query_lower or 'o(n3)' in query_lower or 'cubic' in query_lower or 'кубическ' in query_lower:
            filters['complexity_filter'] = {'min': 6, 'max': 6}
        elif 'o(n^2)' in query_lower or 'o(n2)' in query_lower or 'quadratic' in query_lower or 'квадратичн' in query_lower:
            filters['complexity_filter'] = {'min': 5, 'max': 5}
        elif 'o(n log n)' in query_lower or 'o(n*log' in query_lower or 'linearithmic' in query_lower or 'линеарифмическ' in query_lower:
            filters['complexity_filter'] = {'min': 4, 'max': 4}  # O(n log n)
        elif ('o(n)' in query_lower or 'сложностью o(n)' in query_lower) and 'log' not in query_lower:
            # O(n) or higher
            if 'или выше' in query_lower or 'or higher' in query_lower or 'or above' in query_lower or 'и выше' in query_lower:
                # "или выше" означает >= O(n)
                filters['complexity_filter'] = {'min': 3}  # O(n) and above
            elif 'больше чем' in query_lower or 'больше' in query_lower or 'more than' in query_lower or 'выше' in query_lower:
                # "больше чем" означает строго > O(n), т.е. >= O(n log n)
                filters['complexity_filter'] = {'min': 4}  # Strictly greater than O(n), i.e. O(n log n) and above
            else:
                filters['complexity_filter'] = {'min': 3, 'max': 3}  # Exactly O(n)
        elif 'o(log n)' in query_lower or 'логарифмическ' in query_lower:
            filters['complexity_filter'] = {'min': 2, 'max': 2}
        elif 'o(1)' in query_lower or 'константн' in query_lower or 'constant' in query_lower:
            filters['complexity_filter'] = {'min': 1, 'max': 1}
        # Check for "сложностью" or "сложность" followed by complexity notation
        elif 'сложност' in query_lower:
            # Try to extract complexity from patterns like "сложностью O(n^2)", "со сложностью NP", etc.
            # Match patterns like "сложностью O(...)", "со сложностью O(...)", "сложность O(...)"
            complexity_patterns = [
                (r'сложностью\s+o\(n!\)', 8),
                (r'со\s+сложностью\s+o\(n!\)', 8),
                (r'сложностью\s+o\(2\^n\)', 7),
                (r'со\s+сложностью\s+o\(2\^n\)', 7),
                (r'сложностью\s+o\(n\^3\)', 6),
                (r'со\s+сложностью\s+o\(n\^3\)', 6),
                (r'сложностью\s+o\(n\^2\)', 5),
                (r'со\s+сложностью\s+o\(n\^2\)', 5),
                (r'сложностью\s+o\(n\s+log\s+n\)', 4),
                (r'со\s+сложностью\s+o\(n\s+log\s+n\)', 4),
                (r'сложностью\s+o\(n\)', 3),
                (r'со\s+сложностью\s+o\(n\)', 3),
                (r'сложностью\s+o\(log\s+n\)', 2),
                (r'со\s+сложностью\s+o\(log\s+n\)', 2),
                (r'сложностью\s+o\(1\)', 1),
                (r'со\s+сложностью\s+o\(1\)', 1),
                (r'сложностью\s+np', 8),  # NP-complete is usually factorial/exponential
                (r'со\s+сложностью\s+np', 8),
            ]
            for pattern, complexity_num in complexity_patterns:
                if re.search(pattern, query_lower):
                    filters['complexity_filter'] = {'min': complexity_num, 'max': complexity_num}
                    break
        
        # SOLID filters (English and Russian)
        if 'liskov' in query_lower or 'lsp' in query_lower or 'лисков' in query_lower:
            filters['solid_filter'] = {'principle': 'Liskov Substitution Principle'}
        elif 'single responsibility' in query_lower or 'srp' in query_lower or 'единичной ответственности' in query_lower or 'единичн' in query_lower or 'принцип единичн' in query_lower or 'нарушен' in query_lower and ('ответственн' in query_lower or 'responsibility' in query_lower):
            filters['solid_filter'] = {'principle': 'Single Responsibility Principle'}
        elif 'open/closed' in query_lower or 'ocp' in query_lower or 'открыт/закрыт' in query_lower:
            filters['solid_filter'] = {'principle': 'Open/Closed Principle'}
        elif 'interface segregation' in query_lower or 'isp' in query_lower or 'сегрегации интерфейса' in query_lower:
            filters['solid_filter'] = {'principle': 'Interface Segregation Principle'}
        elif 'dependency inversion' in query_lower or 'dip' in query_lower or 'инверсии зависимостей' in query_lower:
            filters['solid_filter'] = {'principle': 'Dependency Inversion Principle'}
        elif 'solid' in query_lower and ('нарушен' in query_lower or 'violation' in query_lower):
            # Generic SOLID violation search - will match any SOLID violation
            filters['solid_filter'] = {'principle': None}  # None means any SOLID violation
        
        # Testability
        if 'testable' in query_lower or 'unit test' in query_lower:
            filters['testability_filter'] = {'min_score': 0.5}
        
        # Pattern filters
        if 'factory' in query_lower:
            filters['pattern_filter'] = 'Factory'
        elif 'strategy' in query_lower:
            filters['pattern_filter'] = 'Strategy'
        elif 'observer' in query_lower:
            filters['pattern_filter'] = 'Observer'
        
        return filters
    
    def _analyze_query_with_llm(self, query: str) -> Dict:
        """Use LLM to analyze query and extract MVC/DDD role filters"""
        try:
            prompt = f"""Analyze the following code search query and extract structured information.

Query: "{query}"

Extract the following information if present:
1. Entity type: "method", "class", "function", "constant", or "enum"
2. MVC role: "Controller", "Model", "View", "Service", or "Repository"
3. DDD role: "Entity", "ValueObject", "Aggregate", "Service", "Repository", or "Factory"

Respond with a JSON object in this format:
{{
    "entity_type_filter": "method" or null,
    "mvc_role_filter": "Controller" or null,
    "ddd_role_filter": "Entity" or null
}}

Examples:
- "найди все методы контроллеров" -> {{"entity_type_filter": "method", "mvc_role_filter": "Controller"}}
- "find all controller methods" -> {{"entity_type_filter": "method", "mvc_role_filter": "Controller"}}
- "классы-сущности DDD" -> {{"entity_type_filter": "class", "ddd_role_filter": "Entity"}}
- "методы сервисов" -> {{"entity_type_filter": "method", "mvc_role_filter": "Service", "ddd_role_filter": "Service"}}
- "enum values" -> {{"entity_type_filter": "enum"}}
- "перечисления" -> {{"entity_type_filter": "enum"}}

Respond with JSON only, no additional text."""

            response = self.analyzer.client.chat.completions.create(
                model=self.analyzer.model,
                messages=[
                    {"role": "system", "content": "You are a code search query analyzer. Respond with JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=200
            )
            
            result_text = response.choices[0].message.content.strip()
            # Remove markdown code blocks if present
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()
            
            llm_result = json.loads(result_text)
            return llm_result
        except Exception as e:
            logger.warning(f"LLM query analysis error: {e}")
            return {}


class SearchService:
    """Service for searching code"""
    
    def __init__(self):
        self.query_analyzer = QueryAnalyzer()
        self.embedding_service = EmbeddingService()
        self.qdrant = QdrantService()
    
    def search(
        self,
        db: Session,
        query: str,
        project_id: Optional[int] = None,
        limit: int = 20
    ) -> List[SearchResult]:
        """Perform hybrid search with keyword-first approach
        
        Args:
            db: Database session
            query: Search query
            project_id: Project ID (required - search is scoped to a project)
            limit: Maximum number of results
        """
        # Require project_id for search
        if not project_id:
            logger.warning("Search called without project_id - returning empty results")
            return []
        
        # Analyze query
        filters = self.query_analyzer.analyze_query(query)
        
        results = []
        seen_entity_ids = set()
        
        # 1. Keyword search (exact matches first) - highest priority
        keyword_results = self._keyword_search(db, query, filters, project_id, limit)
        for result in keyword_results:
            if result.entity.id not in seen_entity_ids:
                results.append(result)
                seen_entity_ids.add(result.entity.id)
        
        # 1.5. If query is about statuses/enums and we found enum class, also search for enum cases
        query_lower = query.lower()
        if any(kw in query_lower for kw in ['статус', 'status', 'enum', 'перечислен']):
            # Find enum classes in results
            enum_classes = [r for r in keyword_results if r.entity.type == 'class' and ('status' in r.entity.name.lower() or 'enum' in r.entity.name.lower())]
            if enum_classes:
                # Search for enum cases (constants with :: in FQN)
                for enum_class in enum_classes:
                    enum_name = enum_class.entity.name
                    # Find constants that belong to this enum (must have :: in FQN)
                    enum_cases = db.query(Entity, Analysis, File).join(
                        Analysis, Entity.id == Analysis.entity_id
                    ).join(File, Entity.file_id == File.id).filter(
                        File.project_id == project_id,
                        Entity.type == 'constant',
                        Entity.full_qualified_name.like(f'%{enum_name}::%')
                    ).limit(10).all()
                    
                    for entity, analysis, file in enum_cases:
                        if entity.id not in seen_entity_ids:
                            results.append(SearchResult(
                                entity=self._entity_to_response(entity, file),
                                analysis=self._analysis_to_response(analysis, entity, file),
                                score=0.9,  # Very high score for enum cases when enum class is found
                                match_type="keyword"
                            ))
                            seen_entity_ids.add(entity.id)
            
            # Also search for enum classes directly if not found yet
            if not enum_classes:
                # Search for enum classes by name pattern
                enum_class_search = db.query(Entity, Analysis, File).join(
                    Analysis, Entity.id == Analysis.entity_id
                ).join(File, Entity.file_id == File.id).filter(
                    File.project_id == project_id,
                    Entity.type == 'class',
                    or_(
                        Entity.name.ilike('%Status%'),
                        Entity.name.ilike('%Enum%')
                    )
                ).limit(5).all()
                
                for entity, analysis, file in enum_class_search:
                    if entity.id not in seen_entity_ids:
                        results.append(SearchResult(
                            entity=self._entity_to_response(entity, file),
                            analysis=self._analysis_to_response(analysis, entity, file),
                            score=0.7,
                            match_type="keyword"
                        ))
                        seen_entity_ids.add(entity.id)
                        
                        # Also get enum cases for this class
                        enum_name = entity.name
                        enum_cases = db.query(Entity, Analysis, File).join(
                            Analysis, Entity.id == Analysis.entity_id
                        ).join(File, Entity.file_id == File.id).filter(
                            File.project_id == project_id,
                            Entity.type == 'constant',
                            Entity.full_qualified_name.like(f'%{enum_name}::%')
                        ).limit(10).all()
                        
                        for case_entity, case_analysis, case_file in enum_cases:
                            if case_entity.id not in seen_entity_ids:
                                results.append(SearchResult(
                                    entity=self._entity_to_response(case_entity, case_file),
                                    analysis=self._analysis_to_response(case_analysis, case_entity, case_file),
                                    score=0.9,
                                    match_type="keyword"
                                ))
                                seen_entity_ids.add(case_entity.id)
        
        # 2. Structured search (SQL) - for specific filters
        structured_results = self._structured_search(db, filters, project_id, limit)
        for result in structured_results:
            if result.entity.id not in seen_entity_ids:
                results.append(result)
                seen_entity_ids.add(result.entity.id)
        
        # 2.5. If SOLID filter is set but no results, also search by keywords in description
        if filters.get('solid_filter') and not structured_results:
            # Search for entities with SOLID violations mentioned in description/keywords
            solid_keywords = ['solid', 'нарушен', 'violation', 'responsibility', 'ответственн']
            query_lower = query.lower()
            if any(kw in query_lower for kw in solid_keywords):
                solid_search = db.query(Entity, Analysis, File).join(
                    Analysis, Entity.id == Analysis.entity_id
                ).join(File, Entity.file_id == File.id).filter(
                    File.project_id == project_id,
                    Analysis.solid_violations.isnot(None),
                    or_(
                        Analysis.description.ilike('%solid%'),
                        Analysis.description.ilike('%нарушен%'),
                        Analysis.description.ilike('%responsibility%'),
                        Analysis.description.ilike('%ответственн%'),
                        Analysis.keywords.ilike('%solid%'),
                        Analysis.keywords.ilike('%нарушен%')
                    )
                ).limit(10).all()
                
                for entity, analysis, file in solid_search:
                    if entity.id not in seen_entity_ids:
                        # Check if it matches the principle
                        principle = filters['solid_filter'].get('principle')
                        if principle is None or any(
                            v.get('principle') == principle 
                            for v in (analysis.solid_violations or [])
                            if isinstance(v, dict)
                        ):
                            results.append(SearchResult(
                                entity=self._entity_to_response(entity, file),
                                analysis=self._analysis_to_response(analysis, entity, file),
                                score=0.8,
                                match_type="structured"
                            ))
                            seen_entity_ids.add(entity.id)
        
        # 3. Dependency-based search (if keyword search found relevant classes OR if query mentions dependencies)
        # Check if query mentions common dependency patterns (SQLAlchemy, db.query, etc.)
        query_lower = query.lower()
        dependency_keywords = ['sqlalchemy', 'db.query', 'db.add', 'db.commit', 'db.flush', 'db.delete', 
                              'зависимост', 'dependency', 'использует', 'uses', 'вызывает', 'calls']
        has_dependency_query = any(kw in query_lower for kw in dependency_keywords)
        
        if keyword_results or has_dependency_query:
            dependency_results = self._dependency_search(db, query, keyword_results, filters, project_id, limit // 2, has_dependency_query)
            for result in dependency_results:
                if result.entity.id not in seen_entity_ids:
                    results.append(result)
                    seen_entity_ids.add(result.entity.id)
        
        # 4. Semantic search (Vector) - as fallback/complement
        # Only if we don't have enough results or for additional relevance
        if len(results) < limit:
            semantic_results = self._semantic_search(db, filters, project_id, limit - len(results))
            for result in semantic_results:
                if result.entity.id not in seen_entity_ids:
                    results.append(result)
                    seen_entity_ids.add(result.entity.id)
        
        # 5. Deduplicate and rank
        unique_results = self._deduplicate_results(results)
        ranked_results = self._rank_results(unique_results, query)
        
        return ranked_results[:limit]
    
    def _normalize_query(self, query: str) -> List[str]:
        """Normalize query and extract keywords"""
        # Remove common words and normalize
        query_lower = query.lower()
        
        # Russian stop words
        russian_stop_words = {'найти', 'все', 'для', 'которые', 'который', 'которую', 'которое'}
        
        # English stop words
        english_stop_words = {'find', 'all', 'the', 'for', 'which', 'that'}
        
        stop_words = russian_stop_words | english_stop_words
        
        # Extract words (Russian and English)
        words = re.findall(r'\b[а-яё]+|\b[a-z]+', query_lower)
        
        # Normalize Russian words (remove endings to get root forms)
        normalized_words = []
        for word in words:
            # Skip entity type words (методы, классы) - they're used for filtering, not search
            if word in {'методы', 'метод', 'классы', 'класс', 'функции', 'функция',
                       'methods', 'method', 'classes', 'class', 'functions', 'function'}:
                continue
            
            # Normalize Russian word endings to root forms
            # Remove common endings: -ия, -ий, -ие, -ии, -ию, -ей, -ем, -ами, -ах
            if len(word) > 4:
                # Plural genitive/accusative: отправки -> отправк, сообщений -> сообщени
                if word.endswith('ии') or word.endswith('ию'):
                    word = word[:-2]
                elif word.endswith('ий') or word.endswith('ие'):
                    word = word[:-2]
                elif word.endswith('ей') or word.endswith('ем'):
                    word = word[:-2]
                elif word.endswith('ами') or word.endswith('ах'):
                    word = word[:-3]
                elif word.endswith('ия'):
                    word = word[:-2]
                # Singular genitive: отправки -> отправк (if ends with и)
                elif word.endswith('и') and len(word) > 5:
                    word = word[:-1]
            
            normalized_words.append(word)
        
        # Filter out stop words and short words
        keywords = [w for w in normalized_words if w not in stop_words and len(w) > 3]
        
        return keywords
    
    def _keyword_search(
        self,
        db: Session,
        query: str,
        filters: Dict,
        project_id: Optional[int],
        limit: int
    ) -> List[SearchResult]:
        """Search by keywords in names and descriptions - highest priority"""
        # Require project_id
        if not project_id:
            return []
        
        keywords = self._normalize_query(query)
        
        if not keywords:
            return []
        
        # Build search query
        search_query = db.query(Entity, Analysis, File).join(
            Analysis, Entity.id == Analysis.entity_id
        ).join(File, Entity.file_id == File.id)
        
        # Always filter by project_id (required)
        search_query = search_query.filter(File.project_id == project_id)
        
        # Apply entity type filter if specified
        if filters.get('entity_type_filter'):
            entity_type = filters['entity_type_filter']
            if entity_type == 'enum':
                # Filter for enum case values (constants with :: in full_qualified_name)
                search_query = search_query.filter(
                    Entity.type == 'constant',
                    Entity.full_qualified_name.like('%::%')
                )
            else:
                search_query = search_query.filter(Entity.type == entity_type)
        
        # Build OR conditions for keywords - search in name, full_qualified_name, analysis description, and keywords field
        keyword_conditions = []
        for keyword in keywords:
            keyword_pattern = f"%{keyword}%"
            keyword_conditions.append(
                or_(
                    Entity.name.ilike(keyword_pattern),
                    Analysis.description.ilike(keyword_pattern),
                    Entity.full_qualified_name.ilike(keyword_pattern),
                    Analysis.keywords.ilike(keyword_pattern)  # Also search in keywords field
                )
            )
        
        if keyword_conditions:
            search_query = search_query.filter(or_(*keyword_conditions))
        
        # Get results
        entities = search_query.limit(limit * 2).all()
        
        results = []
        for entity, analysis, file in entities:
            # Calculate keyword match score
            score = self._calculate_keyword_score(entity, analysis, keywords)
            
            # Only include if score is high enough
            if score >= 0.3:  # At least 30% keyword match
                results.append(SearchResult(
                    entity=self._entity_to_response(entity, file),
                    analysis=self._analysis_to_response(analysis, entity, file),
                    score=min(score, 1.0),  # Cap at 1.0
                    match_type="keyword"
                ))
        
        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]
    
    def _calculate_keyword_score(self, entity: Entity, analysis: Analysis, keywords: List[str]) -> float:
        """Calculate relevance score based on keyword matches"""
        score = 0.0
        
        # Build text to search including keywords field
        text_parts = [
            entity.name,
            analysis.description if analysis else '',
            entity.full_qualified_name or ''
        ]
        
        # Add keywords from analysis if available
        if analysis and analysis.keywords:
            text_parts.append(analysis.keywords)
        
        text_to_search = ' '.join(text_parts).lower()
        
        # Count keyword matches
        matches = sum(1 for keyword in keywords if keyword in text_to_search)
        
        if matches == 0:
            return 0.0
        
        # Base score: percentage of keywords found
        base_score = matches / len(keywords)
        
        # Boost if keyword in name (more important)
        name_lower = entity.name.lower()
        name_matches = sum(1 for keyword in keywords if keyword in name_lower)
        if name_matches > 0:
            base_score += 0.3 * (name_matches / len(keywords))
        
        # Boost if keyword found in keywords field (high relevance)
        if analysis and analysis.keywords:
            keywords_lower = analysis.keywords.lower()
            keywords_matches = sum(1 for keyword in keywords if keyword in keywords_lower)
            if keywords_matches > 0:
                base_score += 0.2 * (keywords_matches / len(keywords))
        
        # Boost if all keywords found
        if matches == len(keywords):
            base_score += 0.2
        
        return min(base_score, 1.0)
    
    def _dependency_search(
        self,
        db: Session,
        query: str,
        keyword_results: List[SearchResult],
        filters: Dict,
        project_id: Optional[int],
        limit: int,
        has_dependency_query: bool = False
    ) -> List[SearchResult]:
        """Search for methods that depend on classes found in keyword search or match dependency patterns"""
        
        # Require project_id for dependency search
        if not project_id:
            return []
        
        # Get project language to filter language-specific dependencies
        from app.models.database import Project
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return []
        
        project_language = project.language.lower() if project.language else None
        
        # Extract entity IDs from keyword results (focus on classes)
        relevant_entity_ids = set()
        relevant_class_names = set()
        dependency_patterns = set()
        
        if keyword_results:
            for result in keyword_results:
                if result.entity.type == 'class':
                    relevant_entity_ids.add(result.entity.id)
                    relevant_class_names.add(result.entity.name.lower())
                    # Also check full qualified name
                    if result.entity.full_qualified_name:
                        relevant_class_names.add(result.entity.full_qualified_name.lower())
        
        # If query mentions dependencies directly, extract patterns
        if has_dependency_query:
            query_lower = query.lower()
            # Common SQLAlchemy patterns (Python only)
            if ('sqlalchemy' in query_lower or 'db.' in query_lower) and project_language == 'python':
                dependency_patterns.update(['db.query', 'db.add', 'db.commit', 'db.flush', 'db.delete', 
                                           'db.rollback', 'db.refresh', 'db.close', 'Session', 'session'])
            # Extract other dependency keywords from query
            keywords = self._normalize_query(query)
            dependency_patterns.update(keywords)
        
        if not relevant_entity_ids and not relevant_class_names and not dependency_patterns:
            return []
        
        # Find entities that depend on these classes
        # Method 1: Direct dependencies via Dependency table
        dependency_query = db.query(Entity, Analysis, File).join(
            Analysis, Entity.id == Analysis.entity_id
        ).join(File, Entity.file_id == File.id).join(
            Dependency, Entity.id == Dependency.entity_id
        )
        
        # Always filter by project_id (required)
        dependency_query = dependency_query.filter(File.project_id == project_id)
        
        # Filter by entity type if specified
        if filters.get('entity_type_filter'):
            entity_type = filters['entity_type_filter']
            if entity_type == 'enum':
                # Filter for enum case values (constants with :: in full_qualified_name)
                dependency_query = dependency_query.filter(
                    Entity.type == 'constant',
                    Entity.full_qualified_name.like('%::%')
                )
            else:
                dependency_query = dependency_query.filter(Entity.type == entity_type)
        
        # Match by depends_on_entity_id or depends_on_name
        dependency_conditions = []
        if relevant_entity_ids:
            dependency_conditions.append(Dependency.depends_on_entity_id.in_(relevant_entity_ids))
        
        if relevant_class_names:
            for class_name in relevant_class_names:
                dependency_conditions.append(Dependency.depends_on_name.ilike(f"%{class_name}%"))
        
        # Match by dependency patterns (e.g., db.query, SQLAlchemy methods)
        if dependency_patterns:
            pattern_conditions = []
            for pattern in dependency_patterns:
                pattern_conditions.append(Dependency.depends_on_name.ilike(f"%{pattern}%"))
            if pattern_conditions:
                dependency_conditions.append(or_(*pattern_conditions))
        
        if dependency_conditions:
            dependency_query = dependency_query.filter(or_(*dependency_conditions))
        
        dependency_entities = dependency_query.limit(limit).all()
        
        results = []
        seen_ids = set()
        
        for entity, analysis, file in dependency_entities:
            if entity.id in seen_ids:
                continue
            seen_ids.add(entity.id)
            
            # Get dependency description for context
            dependencies = db.query(Dependency).filter(Dependency.entity_id == entity.id).all()
            dependency_score = 0.5  # Base score for dependency match
            
            # Boost if dependency description is relevant
            if analysis and analysis.description:
                keywords = self._normalize_query(query)
                desc_lower = analysis.description.lower()
                keyword_matches = sum(1 for kw in keywords if kw in desc_lower)
                if keyword_matches > 0:
                    dependency_score += 0.2 * (keyword_matches / len(keywords)) if keywords else 0
            
            results.append(SearchResult(
                entity=self._entity_to_response(entity, file),
                analysis=self._analysis_to_response(analysis, entity, file),
                score=dependency_score,
                match_type="dependency"
            ))
        
        return results
    
    def _structured_search(
        self,
        db: Session,
        filters: Dict,
        project_id: Optional[int],
        limit: int
    ) -> List[SearchResult]:
        """Search using structured filters"""
        # Require project_id
        if not project_id:
            return []
        
        # Only perform structured search if we have specific filters
        # Don't use entity_type_filter alone - it's too broad and should rely on semantic search
        has_filters = any([
            filters.get('complexity_filter'),
            filters.get('solid_filter'),
            filters.get('testability_filter'),
            filters.get('pattern_filter'),
            filters.get('mvc_role_filter'),
            filters.get('ddd_role_filter')
        ])
        
        # Only use entity_type_filter if we have other filters too
        use_entity_type_filter = filters.get('entity_type_filter') and has_filters
        
        # Allow MVC/DDD role filters even without other filters (they're specific enough)
        if not has_filters and not (filters.get('mvc_role_filter') or filters.get('ddd_role_filter')):
            return []  # Don't return all entities if no filters
        
        query = db.query(Entity, Analysis, File).join(
            Analysis, Entity.id == Analysis.entity_id
        ).join(File, Entity.file_id == File.id)
        
        # Always filter by project_id (required)
        query = query.filter(File.project_id == project_id)
        
        # Complexity filter
        if filters.get('complexity_filter'):
            cf = filters['complexity_filter']
            if 'min' in cf:
                query = query.filter(Analysis.complexity_numeric >= cf['min'])
            if 'max' in cf:
                query = query.filter(Analysis.complexity_numeric <= cf['max'])
        
        # SOLID filter - will be applied in Python after fetching
        # Just ensure solid_violations is not empty
        if filters.get('solid_filter'):
            query = query.filter(
                Analysis.solid_violations.isnot(None)
            )
        
        # Testability filter
        if filters.get('testability_filter'):
            min_score = filters['testability_filter'].get('min_score', 0.5)
            query = query.filter(Analysis.testability_score >= min_score)
        
        # Pattern filter - will be applied in Python after fetching
        # Just ensure design_patterns is not empty
        if filters.get('pattern_filter'):
            query = query.filter(
                Analysis.design_patterns.isnot(None)
            )
        
        # MVC role filter
        if filters.get('mvc_role_filter'):
            query = query.filter(
                Analysis.mvc_role == filters['mvc_role_filter']
            )
        
        # DDD role filter
        if filters.get('ddd_role_filter'):
            query = query.filter(
                Analysis.ddd_role == filters['ddd_role_filter']
            )
        
        entities = query.limit(limit * 2).all()  # Get more to filter
        
        results = []
        for entity, analysis, file in entities:
            # Apply entity type filter if specified (only if we have other filters)
            if use_entity_type_filter:
                entity_type = filters['entity_type_filter']
                if entity_type == 'enum':
                    # Check if it's an enum case value (constant with :: in full_qualified_name)
                    if entity.type != 'constant' or '::' not in (entity.full_qualified_name or ''):
                        continue
                elif entity.type != entity_type:
                    continue
            
            # Apply complexity filter in Python if needed
            if filters.get('complexity_filter'):
                cf = filters['complexity_filter']
                complexity_num = analysis.complexity_numeric
                
                # Check min
                if 'min' in cf and complexity_num < cf['min']:
                    continue
                
                # Check max
                if 'max' in cf and complexity_num > cf['max']:
                    continue
            
            # Apply SOLID filter in Python if needed
            if filters.get('solid_filter'):
                principle = filters['solid_filter'].get('principle')
                violations = analysis.solid_violations or []
                
                if principle is None:
                    # Match any SOLID violation
                    if not violations:
                        continue
                else:
                    # Check if any violation matches the principle
                    has_match = any(
                        v.get('principle') == principle 
                        for v in violations 
                        if isinstance(v, dict)
                    )
                    if not has_match:
                        continue
            
            # Apply pattern filter in Python if needed
            if filters.get('pattern_filter'):
                pattern = filters['pattern_filter']
                patterns = analysis.design_patterns or []
                if pattern not in patterns:
                    continue
            
            results.append(SearchResult(
                entity=self._entity_to_response(entity, file),
                analysis=self._analysis_to_response(analysis, entity, file),
                score=1.0,
                match_type="structured"
            ))
            
            if len(results) >= limit:
                break
        
        return results
    
    def _semantic_search(
        self,
        db: Session,
        filters: Dict,
        project_id: Optional[int],
        limit: int
    ) -> List[SearchResult]:
        """Search using semantic similarity"""
        # Require project_id
        if not project_id:
            return []
        
        semantic_query = filters.get('semantic_query')
        if not semantic_query:
            return []
        
        # Generate embedding
        embedding = self.embedding_service.generate_embedding(semantic_query)
        
        # Search in Qdrant
        qdrant_filter = {}
        # Get file IDs for project (required)
        file_ids = db.query(File.id).filter(File.project_id == project_id).all()
        file_ids = [f[0] for f in file_ids]
        # Note: Qdrant filter would need file_id in payload
        # For now, we'll filter after search
        
        qdrant_results = self.qdrant.search(embedding, limit=limit * 2, filter=qdrant_filter if qdrant_filter else None)
        
        # Filter by minimum relevance score (0.5 threshold for better quality)
        # Higher threshold to reduce false positives
        min_score = 0.5
        relevant_results = [r for r in qdrant_results if r.get('score', 0) >= min_score]
        
        if not relevant_results:
            return []
        
        # Get entities from DB
        entity_ids = [r['payload']['entity_id'] for r in relevant_results]
        
        entities = db.query(Entity, Analysis, File).join(
            Analysis, Entity.id == Analysis.entity_id
        ).join(File, Entity.file_id == File.id).filter(
            Entity.id.in_(entity_ids)
        ).all()
        
        # Filter by project if needed
        if project_id:
            entities = [(e, a, f) for e, a, f in entities if f.project_id == project_id]
        
        # Create results with scores
        results = []
        score_map = {r['payload']['entity_id']: r['score'] for r in relevant_results}
        
        for entity, analysis, file in entities:
            # Apply entity type filter if specified
            if filters.get('entity_type_filter'):
                entity_type = filters['entity_type_filter']
                if entity_type == 'enum':
                    # Check if it's an enum case value (constant with :: in full_qualified_name)
                    if entity.type != 'constant' or '::' not in (entity.full_qualified_name or ''):
                        continue
                elif entity.type != entity_type:
                    continue
            
            # Apply MVC role filter if specified
            if filters.get('mvc_role_filter'):
                if analysis.mvc_role != filters['mvc_role_filter']:
                    continue
            
            # Apply DDD role filter if specified
            if filters.get('ddd_role_filter'):
                if analysis.ddd_role != filters['ddd_role_filter']:
                    continue
            
            # Apply complexity filter if specified
            if filters.get('complexity_filter'):
                cf = filters['complexity_filter']
                complexity_num = analysis.complexity_numeric
                
                # Check min
                if 'min' in cf and complexity_num < cf['min']:
                    continue
                
                # Check max
                if 'max' in cf and complexity_num > cf['max']:
                    continue
            
            score = score_map.get(entity.id, 0.0)
            results.append(SearchResult(
                entity=self._entity_to_response(entity, file),
                analysis=self._analysis_to_response(analysis, entity, file),
                score=float(score),
                match_type="semantic"
            ))
        
        return results
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicate results based on unique key (name, file_path, start_line, end_line)
        
        This prevents showing the same entity multiple times even if it has different entity_ids
        (which happens when entities are indexed multiple times)
        """
        seen = {}  # key: (name, file_path, start_line, end_line) -> SearchResult
        unique = []
        
        for result in results:
            # Create unique key from entity properties (not entity_id)
            # For constants, use name + file_path only (start_line may vary)
            # For other entities, use name + file_path + start_line + end_line
            if result.entity.type == 'constant':
                unique_key = (
                    result.entity.name,
                    result.entity.file_path,
                    result.entity.type
                )
            else:
                unique_key = (
                    result.entity.name,
                    result.entity.file_path,
                    result.entity.start_line,
                    result.entity.end_line
                )
            
            if unique_key not in seen:
                seen[unique_key] = result
                unique.append(result)
            else:
                # Merge scores if duplicate - keep the one with higher score
                existing = seen[unique_key]
                if result.score > existing.score:
                    # Replace with better scoring result
                    unique.remove(existing)
                    seen[unique_key] = result
                    unique.append(result)
                elif result.entity.id < existing.entity.id:
                    # If scores are equal, keep the one with lower ID (older, more likely to be the original)
                    unique.remove(existing)
                    seen[unique_key] = result
                    unique.append(result)
                else:
                    # Keep existing, but update score if needed
                    existing.score = max(existing.score, result.score)
                    if result.match_type == "semantic" and existing.match_type != "hybrid":
                        existing.match_type = "hybrid"
        
        return unique
    
    def _rank_results(self, results: List[SearchResult], query: str) -> List[SearchResult]:
        """Rank results by relevance"""
        query_lower = query.lower()
        
        # Extract key terms from query (Russian and English)
        key_terms = []
        if 'отправк' in query_lower or 'send' in query_lower or 'сообщени' in query_lower or 'message' in query_lower:
            key_terms.extend(['отправк', 'send', 'сообщени', 'message'])
        if 'метод' in query_lower or 'method' in query_lower:
            key_terms.extend(['метод', 'method'])
        if 'статус' in query_lower or 'status' in query_lower:
            key_terms.extend(['статус', 'status'])
        
        def score_result(result: SearchResult) -> float:
            score = result.score
            
            # Boost if name matches
            entity_name_lower = result.entity.name.lower()
            if query_lower in entity_name_lower:
                score += 0.3
            
            # Special boost for enum/status-related entities when query is about statuses
            if 'статус' in query_lower or 'status' in query_lower:
                if 'status' in entity_name_lower or 'статус' in entity_name_lower:
                    score += 0.4  # Strong boost for status-related entities
                if result.entity.type == 'class' and 'status' in entity_name_lower:
                    score += 0.3  # Extra boost for status classes/enums
            
            # Boost if description contains key terms
            if result.analysis:
                desc_lower = result.analysis.description.lower()
                # Check if description contains key terms from query
                key_term_matches = sum(1 for term in key_terms if term in desc_lower)
                if key_term_matches > 0:
                    score += 0.3 * (key_term_matches / len(key_terms)) if key_terms else 0
                elif query_lower in desc_lower:
                    score += 0.2
                else:
                    # Only penalize if description doesn't match AND it's not a status-related entity
                    if not ('status' in entity_name_lower or 'статус' in entity_name_lower):
                        score -= 0.1
            
            # Penalize structured results with low semantic relevance
            if result.match_type == "structured" and result.score == 1.0:
                # If it's only from structured search and not semantic, it might be less relevant
                score -= 0.1
            
            return score
        
        return sorted(results, key=score_result, reverse=True)
    
    def _entity_to_response(self, entity: Entity, file: File) -> EntityResponse:
        """Convert Entity to response model"""
        return EntityResponse(
            id=entity.id,
            type=entity.type,
            name=entity.name,
            start_line=entity.start_line,
            end_line=entity.end_line,
            visibility=entity.visibility,
            full_qualified_name=entity.full_qualified_name,
            file_path=file.path
        )
    
    def _analysis_to_response(
        self,
        analysis: Analysis,
        entity: Entity,
        file: File
    ) -> AnalysisResponse:
        """Convert Analysis to response model"""
        return AnalysisResponse(
            id=analysis.id,
            description=analysis.description,
            complexity=analysis.complexity,
            complexity_numeric=analysis.complexity_numeric,
            solid_violations=analysis.solid_violations or [],
            design_patterns=analysis.design_patterns or [],
            ddd_role=analysis.ddd_role,
            mvc_role=analysis.mvc_role,
            is_testable=analysis.is_testable,
            testability_score=analysis.testability_score,
            testability_issues=analysis.testability_issues or [],
            entity=self._entity_to_response(entity, file),
            keywords=analysis.keywords
        )

