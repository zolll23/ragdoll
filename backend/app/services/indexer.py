import os
import hashlib
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models.database import Project, File, Entity, Analysis, Dependency
from app.parsers.code_parser import CodeParser
from app.agents.analyzer import CodeAnalyzer
from app.services.embedding_service import EmbeddingService
from app.services.qdrant_service import QdrantService
from app.core.database import SessionLocal
from app.core.config import settings
from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


class IndexingService:
    """Service for indexing code projects"""
    
    def __init__(self):
        self.parser = CodeParser()
        # Create analyzer fresh each time to get latest provider from DB
        self.analyzer = CodeAnalyzer()
        self.embedding_service = EmbeddingService()
        self.qdrant = QdrantService()
    
    def index_project(self, project_id: int, resume: bool = False):
        """Index entire project
        
        Args:
            project_id: Project ID
            resume: If True, resume from last_indexed_file_path
        """
        db = SessionLocal()
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # Mark as indexing
            project.is_indexing = True
            db.commit()
            db.refresh(project)
            
            logger.info(f"Starting indexing for project: {project.name} (resume={resume})")
            
            # Get all files
            project_path = Path(project.path)
            if not project_path.exists():
                raise ValueError(f"Project path does not exist: {project.path}")
            
            files = self._get_code_files(project_path, project.language)
            
            # Update project total files count (only if not resuming)
            if not resume:
                project.total_files = len(files)
                project.indexed_files = 0
                project.total_entities = 0
                project.last_indexed_file_path = None
                db.commit()
                db.refresh(project)
            
            # Get already indexed files to skip them (use full path for comparison)
            indexed_file_paths = {
                f.path for f in db.query(File).filter(File.project_id == project_id).all()
            }
            
            # Resume from last indexed file if resuming
            start_index = 0
            if resume and project.last_indexed_file_path:
                try:
                    start_index = next(
                        (i for i, f in enumerate(files) if str(f) == project.last_indexed_file_path),
                        0
                    )
                    # Start from next file
                    start_index += 1
                    logger.info(f"Resuming from file index {start_index}: {project.last_indexed_file_path}")
                except (StopIteration, ValueError):
                    logger.warning(f"Could not find resume file: {project.last_indexed_file_path}, starting from beginning")
                    start_index = 0
            
            indexed_count = project.indexed_files or 0
            total_files_count = len(files)
            
            for i, file_path in enumerate(files[start_index:], start=start_index):
                try:
                    # Update current file and status
                    file_path_str = str(file_path)
                    project.current_file_path = file_path_str
                    project.indexing_status = f"Processing file {i+1}/{total_files_count}: {file_path.name}"
                    db.commit()
                    db.refresh(project)
                    
                    logger.info(f"[{project.name}] Processing file {i+1}/{total_files_count}: {file_path_str}")
                    
                    # Check if file is already indexed (compare full path)
                    if file_path_str in indexed_file_paths:
                        # File already indexed, but count it
                        indexed_count += 1
                        project.indexed_files = indexed_count
                        project.last_indexed_file_path = file_path_str
                        project.indexing_status = f"File {i+1}/{total_files_count} already indexed: {file_path.name}"
                        db.commit()
                        db.refresh(project)
                        logger.info(f"[{project.name}] File already indexed, skipping: {file_path.name}")
                        continue
                    
                    # Index the file
                    logger.info(f"[{project.name}] Starting to index file: {file_path.name}")
                    self._index_file(db, project, file_path, None)
                    indexed_count += 1
                    project.indexed_files = indexed_count
                    project.last_indexed_file_path = file_path_str
                    project.indexing_status = f"Completed file {i+1}/{total_files_count}: {file_path.name}"
                    db.commit()
                    db.refresh(project)
                    logger.info(f"[{project.name}] Successfully indexed file {i+1}/{total_files_count}: {file_path.name}")
                    
                except Exception as e:
                    error_msg = f"Error indexing file {file_path}: {str(e)}"
                    logger.error(f"[{project.name}] {error_msg}", exc_info=True)
                    project.indexing_status = f"Error in file {i+1}/{total_files_count}: {file_path.name} - {str(e)[:100]}"
                    db.rollback()
                    # Continue to next file instead of stopping
                    continue
            
            # Recalculate total entities after indexing
            project.total_entities = db.query(Entity).join(File).filter(File.project_id == project_id).count()
            project.is_indexing = False
            project.indexing_task_id = None
            project.current_file_path = None
            project.indexing_status = f"Indexing completed. Indexed {project.indexed_files}/{project.total_files} files, {project.total_entities} entities."
            db.commit()
            db.refresh(project)
            
            logger.info(f"Finished indexing project: {project.name}")
            
        except Exception as e:
            # Mark as not indexing on error
            error_msg = f"Indexing failed: {str(e)}"
            logger.error(f"[{project.name}] {error_msg}", exc_info=True)
            project.is_indexing = False
            project.indexing_task_id = None
            project.current_file_path = None
            project.indexing_status = f"Indexing failed: {error_msg[:150]}"
            db.commit()
            raise
        finally:
            db.close()
    
    def index_file(self, file_id: int):
        """Index single file"""
        db = SessionLocal()
        try:
            file = db.query(File).filter(File.id == file_id).first()
            if not file:
                raise ValueError(f"File {file_id} not found")
            
            project = db.query(Project).filter(Project.id == file.project_id).first()
            file_path = Path(file.path)
            
            self._index_file(db, project, file_path)
            
        finally:
            db.close()
    
    def reindex_project(self, project_id: int, only_failed: bool = False):
        """Reindex project
        
        Args:
            project_id: Project ID
            only_failed: If True, only reindex entities with failed analysis
        """
        db = SessionLocal()
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            if only_failed:
                logger.info(f"Starting reindexing failed analyses for project: {project.name}")
                # Mark as reindexing failed
                project.is_reindexing_failed = True
                project.reindexed_failed_count = 0
                db.commit()
                
                # Find all entities with failed analysis OR without analysis
                # This includes entities that lost their analysis due to errors
                failed_entities_with_analysis = db.query(Entity).join(File).join(Analysis).filter(
                    File.project_id == project_id,
                    Analysis.description == 'Analysis failed'
                ).all()
                
                # Also find entities without any analysis
                failed_entities_without_analysis = db.query(Entity).join(File).outerjoin(Analysis).filter(
                    File.project_id == project_id,
                    Analysis.id == None
                ).all()
                
                # Combine both lists
                all_failed_entities = list(failed_entities_with_analysis) + list(failed_entities_without_analysis)
                
                # Remove duplicates: keep only one entity per (name, file_id, start_line, end_line)
                # This prevents reindexing the same entity multiple times
                seen_entities = {}
                failed_entities = []
                
                for entity in all_failed_entities:
                    # Create unique key: (name, file_id, start_line, end_line)
                    unique_key = (entity.name, entity.file_id, entity.start_line, entity.end_line)
                    
                    if unique_key not in seen_entities:
                        # Keep the first occurrence (prefer entity with lower ID)
                        seen_entities[unique_key] = entity
                        failed_entities.append(entity)
                    else:
                        # If we already have this entity, keep the one with lower ID
                        existing_entity = seen_entities[unique_key]
                        if entity.id < existing_entity.id:
                            # Replace with entity that has lower ID
                            failed_entities.remove(existing_entity)
                            seen_entities[unique_key] = entity
                            failed_entities.append(entity)
                
                duplicates_count = len(all_failed_entities) - len(failed_entities)
                if duplicates_count > 0:
                    logger.info(f"Removed {duplicates_count} duplicate entities from reindexing queue")
                
                project.failed_entities_count = len(failed_entities)
                project.reindexing_failed_status = f"Found {len(failed_entities)} failed entities. Starting reindexing..."
                db.commit()
                db.refresh(project)
                
                logger.info(f"Found {len(failed_entities)} entities to reindex: {len(failed_entities_with_analysis)} with 'Analysis failed', {len(failed_entities_without_analysis)} without analysis")
                
                # Reindex each entity
                total_failed = len(failed_entities)
                for idx, entity in enumerate(failed_entities, 1):
                    try:
                        # Update status
                        project.reindexing_failed_status = f"Reindexing failed entity {idx}/{total_failed}: {entity.name}"
                        db.commit()
                        db.refresh(project)
                        
                        file = db.query(File).filter(File.id == entity.file_id).first()
                        if file and Path(file.path).exists():
                            # Refresh entity to get latest state
                            db.refresh(entity)
                            
                            # Delete old analysis BEFORE re-analyzing
                            old_analysis = entity.analysis
                            if old_analysis:
                                if old_analysis.embedding_id:
                                    try:
                                        point_id = int(old_analysis.embedding_id)
                                        self.qdrant.delete(point_id)
                                    except (ValueError, TypeError):
                                        pass
                                db.delete(old_analysis)
                                db.commit()  # Commit deletion before re-analyzing
                            
                            # Re-analyze existing entity (don't create new one)
                            try:
                                # Analyze existing entity without creating a new one
                                # Get context (dependencies)
                                context = self._get_entity_context(db, project, {
                                    'type': entity.type,
                                    'name': entity.name,
                                    'code': entity.code,
                                    'full_qualified_name': entity.full_qualified_name
                                })
                                
                                # Analyze with AI (with retry and reconnection logic)
                                max_retries = 3
                                retry_delay = 2
                                analysis_result = None
                                tokens_used = 0
                                
                                for attempt in range(max_retries):
                                    try:
                                        logger.info(f"Re-analyzing entity {entity.name} (attempt {attempt + 1}/{max_retries})")
                                        dependency_names = [dep.depends_on_name for dep in entity.dependencies] if hasattr(entity, 'dependencies') and entity.dependencies else []
                                        
                                        analysis_result, tokens_used = self.analyzer.analyze_code(
                                            code=entity.code,
                                            language=project.language,
                                            entity_type=entity.type,
                                            entity_name=entity.name,
                                            context=context,
                                            ui_language=project.ui_language or "EN",
                                            dependencies=dependency_names
                                        )
                                        project.tokens_used = (project.tokens_used or 0) + tokens_used
                                        db.commit()
                                        logger.info(f"Successfully re-analyzed entity {entity.name} (used {tokens_used} tokens)")
                                        break
                                    except Exception as e:
                                        error_msg = str(e)
                                        logger.warning(f"Error re-analyzing entity {entity.name} (attempt {attempt + 1}/{max_retries}): {error_msg}")
                                        
                                        from app.agents.analyzer import RateLimitException
                                        is_rate_limit = isinstance(e, RateLimitException) or any(keyword in error_msg.lower() for keyword in [
                                            'rate limit', '429', 'too many requests'
                                        ])
                                        
                                        is_llm_error = is_rate_limit or any(keyword in error_msg.lower() for keyword in [
                                            'connection', 'timeout', 'network', 'unreachable', 'refused',
                                            'api key', 'authentication', '503', '502', '500'
                                        ])
                                        
                                        if is_llm_error and attempt < max_retries - 1:
                                            if is_rate_limit:
                                                wait_time = max(30, retry_delay * (2 ** attempt))
                                                logger.warning(f"Rate limit detected. Waiting {wait_time}s before retry...")
                                            else:
                                                wait_time = retry_delay * (attempt + 1)
                                                try:
                                                    self.analyzer = CodeAnalyzer()
                                                    logger.info(f"Reconnected to LLM provider: {self.analyzer.provider}")
                                                except Exception as reconnect_error:
                                                    logger.error(f"Failed to reconnect to LLM: {reconnect_error}")
                                            
                                            import time
                                            time.sleep(wait_time)
                                            continue
                                        else:
                                            if attempt == max_retries - 1:
                                                logger.error(f"Failed to re-analyze entity {entity.name} after {max_retries} attempts")
                                            break
                                
                                # Create fallback analysis if needed
                                if analysis_result is None:
                                    logger.warning(f"Using fallback analysis for reindexed entity {entity.name}")
                                    from app.api.models.schemas import CodeAnalysisResult, ComplexityClass
                                    from app.analyzers.static_metrics import StaticMetricsAnalyzer
                                    
                                    static_analyzer = StaticMetricsAnalyzer()
                                    dependency_names = [dep.depends_on_name for dep in entity.dependencies] if hasattr(entity, 'dependencies') and entity.dependencies else []
                                    static_metrics = static_analyzer.analyze(
                                        code=entity.code,
                                        language=project.language,
                                        entity_type=entity.type,
                                        dependencies=dependency_names
                                    )
                                    
                                    analysis_result = CodeAnalysisResult(
                                        description='Analysis failed',
                                        complexity=ComplexityClass.LINEAR,
                                        complexity_explanation='Could not analyze',
                                        solid_violations=[],
                                        design_patterns=[],
                                        ddd_role=None,
                                        mvc_role=None,
                                        is_testable=False,
                                        testability_score=0.0,
                                        testability_issues=['Analysis failed'],
                                        code_fingerprint=entity.code,
                                        dependencies=[],
                                        lines_of_code=static_metrics['lines_of_code'],
                                        cyclomatic_complexity=static_metrics['cyclomatic_complexity'],
                                        cognitive_complexity=static_metrics['cognitive_complexity'],
                                        max_nesting_depth=static_metrics['max_nesting_depth'],
                                        parameter_count=static_metrics['parameter_count'],
                                        coupling_score=static_metrics['coupling_score'],
                                        cohesion_score=static_metrics['cohesion_score'],
                                        afferent_coupling=static_metrics['afferent_coupling'],
                                        efferent_coupling=static_metrics['efferent_coupling'],
                                        n_plus_one_queries=static_metrics['n_plus_one_queries'],
                                        space_complexity=static_metrics['space_complexity'],
                                        hot_path_detected=static_metrics['hot_path_detected'],
                                        security_issues=static_metrics['security_issues'],
                                        hardcoded_secrets=static_metrics['hardcoded_secrets'],
                                        insecure_dependencies=static_metrics['insecure_dependencies'],
                                        is_god_object=static_metrics['is_god_object'],
                                        feature_envy_score=static_metrics['feature_envy_score'],
                                        data_clumps=static_metrics['data_clumps'],
                                        long_parameter_list=static_metrics['long_parameter_list'],
                                    )
                                
                                # Save analysis to existing entity (reuse code from _process_entity)
                                # This is the same logic as in _process_entity, but for existing entity
                                # Define complexity map
                                complexity_map = {
                                    "O(1)": 1,
                                    "O(log n)": 2,
                                    "O(n)": 3,
                                    "O(n log n)": 4,
                                    "O(n^2)": 5,
                                    "O(n^3)": 6,
                                    "O(2^n)": 7,
                                    "O(n!)": 8,
                                }
                                
                                # For constants, always use O(1) complexity
                                if entity.type == 'constant':
                                    complexity_value = "O(1)"
                                    complexity_numeric = 1.0
                                else:
                                    if hasattr(analysis_result.complexity, 'value'):
                                        complexity_value = analysis_result.complexity.value
                                    elif isinstance(analysis_result.complexity, str):
                                        complexity_value = analysis_result.complexity
                                    else:
                                        complexity_value = str(analysis_result.complexity)
                                    complexity_numeric = complexity_map.get(complexity_value, 3)
                                
                                # Convert SecurityIssue objects to dicts
                                security_issues_dict = []
                                if hasattr(analysis_result, 'security_issues') and analysis_result.security_issues:
                                    for issue in analysis_result.security_issues:
                                        if hasattr(issue, 'dict'):
                                            security_issues_dict.append(issue.dict())
                                        elif isinstance(issue, dict):
                                            security_issues_dict.append(issue)
                                        else:
                                            security_issues_dict.append({
                                                'type': getattr(issue, 'type', 'unknown'),
                                                'severity': str(getattr(issue, 'severity', 'medium')),
                                                'description': getattr(issue, 'description', ''),
                                                'location': getattr(issue, 'location', ''),
                                                'suggestion': getattr(issue, 'suggestion', None)
                                            })
                                
                                # Create analysis record
                                analysis = Analysis(
                                    entity_id=entity.id,
                                    description=analysis_result.description,
                                    complexity=complexity_value,
                                    complexity_numeric=complexity_numeric,
                                    complexity_explanation=getattr(analysis_result, 'complexity_explanation', None),
                                    solid_violations=[v.dict() for v in analysis_result.solid_violations],
                                    design_patterns=analysis_result.design_patterns,
                                    ddd_role=analysis_result.ddd_role,
                                    mvc_role=analysis_result.mvc_role,
                                    is_testable=analysis_result.is_testable,
                                    testability_score=analysis_result.testability_score,
                                    testability_issues=analysis_result.testability_issues,
                                    code_fingerprint=analysis_result.code_fingerprint,
                                    lines_of_code=getattr(analysis_result, 'lines_of_code', None),
                                    cyclomatic_complexity=getattr(analysis_result, 'cyclomatic_complexity', None),
                                    cognitive_complexity=getattr(analysis_result, 'cognitive_complexity', None),
                                    max_nesting_depth=getattr(analysis_result, 'max_nesting_depth', None),
                                    parameter_count=getattr(analysis_result, 'parameter_count', None),
                                    coupling_score=getattr(analysis_result, 'coupling_score', None),
                                    cohesion_score=getattr(analysis_result, 'cohesion_score', None),
                                    afferent_coupling=getattr(analysis_result, 'afferent_coupling', None),
                                    efferent_coupling=getattr(analysis_result, 'efferent_coupling', None),
                                    n_plus_one_queries=getattr(analysis_result, 'n_plus_one_queries', None) or [],
                                    space_complexity=getattr(analysis_result, 'space_complexity', None),
                                    hot_path_detected=getattr(analysis_result, 'hot_path_detected', None),
                                    security_issues=security_issues_dict,
                                    hardcoded_secrets=getattr(analysis_result, 'hardcoded_secrets', None) or [],
                                    insecure_dependencies=getattr(analysis_result, 'insecure_dependencies', None) or [],
                                    is_god_object=getattr(analysis_result, 'is_god_object', None),
                                    feature_envy_score=getattr(analysis_result, 'feature_envy_score', None),
                                    data_clumps=getattr(analysis_result, 'data_clumps', None) or [],
                                    long_parameter_list=getattr(analysis_result, 'long_parameter_list', None),
                                )
                                db.add(analysis)
                                db.flush()
                                
                                # Extract and save dependencies
                                try:
                                    dependencies_list = self.parser.extract_dependencies(
                                        entity.code,
                                        project.language,
                                        entity.code
                                    )
                                    
                                    # Delete old dependencies
                                    db.query(Dependency).filter(Dependency.entity_id == entity.id).delete()
                                    
                                    # Save new dependencies
                                    for dep_data in dependencies_list:
                                        dep_name = dep_data['name']
                                        depends_on_entity = None
                                        
                                        if '::' in dep_name or '.' in dep_name:
                                            depends_on_entity = db.query(Entity).filter(
                                                Entity.full_qualified_name == dep_name
                                            ).first()
                                        else:
                                            depends_on_entity = db.query(Entity).join(File).filter(
                                                Entity.name == dep_name,
                                                Entity.type == 'class',
                                                File.project_id == project.id
                                            ).first()
                                        
                                        dependency = Dependency(
                                            entity_id=entity.id,
                                            depends_on_entity_id=depends_on_entity.id if depends_on_entity else None,
                                            depends_on_name=dep_name,
                                            type=dep_data.get('type', 'calls')
                                        )
                                        db.add(dependency)
                                except Exception as e:
                                    logger.error(f"Error extracting dependencies for {entity.name}: {e}", exc_info=True)
                                
                                # Generate keywords for better semantic search
                                keywords = self._generate_keywords(
                                    {
                                        'name': entity.name,
                                        'type': entity.type,
                                        'full_qualified_name': entity.full_qualified_name,
                                        'code': entity.code
                                    },
                                    analysis_result.description,
                                    entity.code
                                )
                                analysis.keywords = keywords
                                
                                # Generate embedding with keywords
                                embedding_text = self._build_embedding_text(
                                    {
                                        'name': entity.name,
                                        'full_qualified_name': entity.full_qualified_name
                                    },
                                    analysis_result.description,
                                    keywords
                                )
                                embedding = self.embedding_service.generate_embedding(embedding_text)
                                point_id = entity.id
                                self.qdrant.upsert_embedding(
                                    point_id=point_id,
                                    vector=embedding,
                                    payload={
                                        "entity_id": entity.id,
                                        "entity_type": entity.type,
                                        "name": entity.name,
                                        "description": analysis_result.description,
                                        "file_path": file.path,
                                        "start_line": entity.start_line,
                                        "end_line": entity.end_line
                                    }
                                )
                                analysis.embedding_id = str(point_id)
                                db.commit()
                                
                                # Verify that analysis was created
                                db.refresh(entity)
                                if entity.analysis:
                                    project.reindexed_failed_count += 1
                                    db.commit()
                                    db.refresh(project)
                                else:
                                    logger.warning(f"Analysis was not created for entity {entity.name} after reindexing")
                            except Exception as process_error:
                                logger.error(f"Error re-analyzing entity {entity.name}: {process_error}", exc_info=True)
                                db.rollback()
                                # Entity will remain without analysis, which is expected if analysis fails
                                continue
                        else:
                            logger.warning(f"File not found for entity {entity.name}: {file.path if file else 'No file'}")
                    except Exception as e:
                        logger.error(f"Error reindexing entity {entity.name}: {e}", exc_info=True)
                        db.rollback()
                        continue
                
                # Mark as completed
                project.is_reindexing_failed = False
                project.reindexing_failed_task_id = None
                project.reindexing_failed_status = f"Reindexing completed. Reindexed {project.reindexed_failed_count}/{project.failed_entities_count} failed entities."
                db.commit()
                db.refresh(project)
                
                logger.info(f"Finished reindexing failed analyses for project: {project.name}. Reindexed {project.reindexed_failed_count}/{project.failed_entities_count} entities.")
            else:
                logger.info(f"Starting reindexing for project: {project.name}")
                
                project_path = Path(project.path)
                current_files = self._get_code_files(project_path, project.language)
                
                # Get indexed files from DB
                indexed_files = {
                    f.path: f for f in db.query(File).filter(File.project_id == project_id).all()
                }
                
                # Find changes
                current_file_hashes = {}
                for file_path in current_files:
                    file_hash = self._calculate_file_hash(file_path)
                    current_file_hashes[str(file_path)] = file_hash
                
                # Files to add or update
                to_process = []
                for file_path_str, file_hash in current_file_hashes.items():
                    file_path = Path(file_path_str)
                    if file_path_str not in indexed_files:
                        # New file
                        to_process.append((file_path, None))
                    elif indexed_files[file_path_str].hash != file_hash:
                        # Changed file - delete old data first
                        old_file = indexed_files[file_path_str]
                        self._delete_file_data(db, old_file.id)
                        to_process.append((file_path, old_file.id))
                
                # Files to delete
                for file_path_str, file in indexed_files.items():
                    if file_path_str not in current_file_hashes:
                        self._delete_file_data(db, file.id)
                
                # Process files
                for file_path, file_id in to_process:
                    try:
                        self._index_file(db, project, file_path, file_id)
                    except Exception as e:
                        logger.error(f"Error indexing file {file_path}: {e}")
                
                logger.info(f"Finished reindexing project: {project.name}")
            
        finally:
            db.close()
    
    def _get_code_files(self, project_path: Path, language: str) -> List[Path]:
        """Get all code files in project"""
        extensions = {
            'python': ['.py'],
            'php': ['.php']
        }
        
        ext_list = extensions.get(language, [])
        files = []
        
        for ext in ext_list:
            # Use rglob with pattern to find all files recursively
            files.extend(project_path.rglob(f'*{ext}'))
        
        # Filter out common directories and files
        exclude_dirs = {'__pycache__', '.git', 'node_modules', 'vendor', 'tests', 'test', 'data', 'migrations', '.venv', 'venv', 'env'}
        exclude_files = {'__init__.py'}  # Can add more if needed
        
        filtered_files = []
        for f in files:
            # Skip if in excluded directory
            if any(exclude in f.parts for exclude in exclude_dirs):
                continue
            # Skip excluded files
            if f.name in exclude_files:
                continue
            filtered_files.append(f)
        
        return filtered_files
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def _index_file(
        self,
        db: Session,
        project: Project,
        file_path: Path,
        file_id: Optional[int] = None
    ):
        """Index a single file"""
        logger.info(f"Indexing file: {file_path}")
        
        file_hash = self._calculate_file_hash(file_path)
        last_modified = datetime.fromtimestamp(file_path.stat().st_mtime)
        
        # Get or create file record
        if file_id:
            file = db.query(File).filter(File.id == file_id).first()
            if file:
                file.hash = file_hash
                file.last_modified = last_modified
            else:
                # File ID was provided but file not found - create new
                file = File(
                    project_id=project.id,
                    path=str(file_path),
                    hash=file_hash,
                    last_modified=last_modified
                )
                db.add(file)
        else:
            file = db.query(File).filter(
                and_(File.project_id == project.id, File.path == str(file_path))
            ).first()
            
            if file:
                file.hash = file_hash
                file.last_modified = last_modified
            else:
                file = File(
                    project_id=project.id,
                    path=str(file_path),
                    hash=file_hash,
                    last_modified=last_modified
                )
                db.add(file)
        
        db.flush()
        
        # Ensure file has an ID
        if not file or not file.id:
            raise ValueError(f"Failed to create or retrieve file record for {file_path}")
        
        # Parse file
        try:
            entities = self.parser.parse_file(str(file_path), project.language)
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            return
        
        # Delete old entities (cascade will delete dependencies)
        db.query(Entity).filter(Entity.file_id == file.id).delete()
        db.flush()
        
        # Process entities in dependency order for better context
        # Strategy: 
        # 1. First index classes (they may be parents for other classes)
        # 2. Then index methods/functions (they can use class context)
        # 3. Within classes, sort by dependencies (base classes first)
        entities_sorted = self._sort_entities_by_dependencies(entities, project.language)
        
        for entity_data in entities_sorted:
            try:
                self._process_entity(db, project, file, entity_data)
            except Exception as e:
                import traceback
                logger.error(f"Error processing entity {entity_data.get('name')} (type: {entity_data.get('type')}): {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Even if analysis fails, try to create entity record at least
                try:
                    entity = Entity(
                        file_id=file.id,
                        type=entity_data['type'],
                        name=entity_data['name'],
                        start_line=entity_data['start_line'],
                        end_line=entity_data['end_line'],
                        visibility=entity_data.get('visibility'),
                        code=entity_data['code'],
                        full_qualified_name=entity_data.get('full_qualified_name')
                    )
                    db.add(entity)
                    db.flush()
                    logger.warning(f"Created entity record for {entity_data.get('name')} despite processing error")
                except Exception as entity_error:
                    logger.error(f"Failed to create entity record: {entity_error}")
                continue
        
        file.indexed_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Successfully indexed file: {file_path}")
    
    def _process_entity(
        self,
        db: Session,
        project: Project,
        file: File,
        entity_data: Dict
    ):
        """Process and analyze a single entity"""
        # Check if entity already exists (to prevent duplicates)
        # For constants, use more flexible matching (name + file + type) since start_line may vary
        # For other entities, use strict matching (name + file + start_line + end_line + type)
        if entity_data['type'] == 'constant':
            # For constants, match by name, file, and type only (start_line may change with comments)
            existing_entity = db.query(Entity).filter(
                Entity.file_id == file.id,
                Entity.name == entity_data['name'],
                Entity.type == entity_data['type']
            ).first()
        else:
            # For methods, classes, etc., use strict matching
            existing_entity = db.query(Entity).filter(
                Entity.file_id == file.id,
                Entity.name == entity_data['name'],
                Entity.start_line == entity_data['start_line'],
                Entity.end_line == entity_data['end_line'],
                Entity.type == entity_data['type']
            ).first()
        
        if existing_entity:
            # Entity already exists - update it instead of creating duplicate
            entity = existing_entity
            # Update entity properties in case they changed
            entity.visibility = entity_data.get('visibility')
            entity.code = entity_data['code']
            entity.full_qualified_name = entity_data.get('full_qualified_name')
            # Delete old analysis if exists (will be recreated below)
            if entity.analysis:
                if entity.analysis.embedding_id:
                    try:
                        point_id = int(entity.analysis.embedding_id)
                        self.qdrant.delete(point_id)
                    except (ValueError, TypeError):
                        pass
                db.delete(entity.analysis)
            # Delete old dependencies
            db.query(Dependency).filter(Dependency.entity_id == entity.id).delete()
        else:
            # Create new entity record
            entity = Entity(
                file_id=file.id,
                type=entity_data['type'],
                name=entity_data['name'],
                start_line=entity_data['start_line'],
                end_line=entity_data['end_line'],
                visibility=entity_data.get('visibility'),
                code=entity_data['code'],
                full_qualified_name=entity_data.get('full_qualified_name')
            )
            db.add(entity)
        
        db.flush()
        
        # Get context (dependencies)
        context = self._get_entity_context(db, project, entity_data)
        
        # Analyze with AI (with retry and reconnection logic)
        max_retries = 3
        retry_delay = 2  # seconds
        analysis_result = None
        tokens_used = 0
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Analyzing entity {entity_data['name']} (attempt {attempt + 1}/{max_retries})")
                # Extract dependency names for static metrics calculation
                dependency_names = [dep.depends_on_name for dep in entity.dependencies] if hasattr(entity, 'dependencies') and entity.dependencies else []
                
                analysis_result, tokens_used = self.analyzer.analyze_code(
                    code=entity_data['code'],
                    language=project.language,
                    entity_type=entity_data['type'],
                    entity_name=entity_data['name'],
                    context=context,
                    ui_language=project.ui_language or "EN",
                    dependencies=dependency_names
                )
                # Update project token usage
                project.tokens_used = (project.tokens_used or 0) + tokens_used
                db.commit()
                logger.info(f"Successfully analyzed entity {entity_data['name']} (used {tokens_used} tokens, total: {project.tokens_used})")
                break  # Success, exit retry loop
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Error analyzing entity {entity_data['name']} (attempt {attempt + 1}/{max_retries}): {error_msg}")
                
                # Log failed analysis attempt immediately (analyzer may have already logged, but we log here too for indexer context)
                logger.debug(f"LOG_FAILED_ANALYSES_TO_FILE setting: {settings.LOG_FAILED_ANALYSES_TO_FILE}")
                if settings.LOG_FAILED_ANALYSES_TO_FILE:
                    try:
                        # Use analyzer's logging method if available, otherwise log directly
                        if hasattr(self.analyzer, '_log_failed_analysis'):
                            # Get prompt if possible (we don't have it here, but analyzer should have logged it)
                            logger.debug(f"Calling analyzer._log_failed_analysis for {entity_data['name']}")
                            self.analyzer._log_failed_analysis(
                                e, 
                                entity_data['name'], 
                                entity_data['type'], 
                                project.language, 
                                self.analyzer.provider, 
                                self.analyzer.model, 
                                prompt=None, 
                                attempt=attempt + 1
                            )
                            logger.debug(f"Successfully called analyzer._log_failed_analysis")
                        else:
                            # Fallback: log directly
                            from datetime import datetime
                            import os
                            log_file = settings.LOG_FAILED_ANALYSES_FILE_PATH
                            log_dir = os.path.dirname(log_file)
                            if log_dir and not os.path.exists(log_dir):
                                os.makedirs(log_dir, exist_ok=True)
                            
                            with open(log_file, 'a', encoding='utf-8') as f:
                                f.write(f"\n{'='*80}\n")
                                f.write(f"FAILED ANALYSIS ATTEMPT {attempt + 1}/{max_retries}\n")
                                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                                f.write(f"Entity: {entity_data['name']} ({entity_data['type']})\n")
                                f.write(f"Language: {project.language}\n")
                                f.write(f"Provider: {self.analyzer.provider}\n")
                                f.write(f"Model: {self.analyzer.model}\n")
                                f.write(f"Error Type: {type(e).__name__}\n")
                                f.write(f"Error Message: {error_msg}\n")
                                f.write(f"{'='*80}\n\n")
                    except Exception as log_error:
                        logger.error(f"Failed to log failed analysis attempt to file: {log_error}", exc_info=True)
                
                # Check if it's a rate limit error (needs longer delay)
                from app.agents.analyzer import RateLimitException
                is_rate_limit = isinstance(e, RateLimitException) or any(keyword in error_msg.lower() for keyword in [
                    'rate limit', '429', 'too many requests'
                ])
                
                # Check if it's a connection/LLM error that might be recoverable
                is_llm_error = is_rate_limit or any(keyword in error_msg.lower() for keyword in [
                    'connection', 'timeout', 'network', 'unreachable', 'refused',
                    'api key', 'authentication', '503', '502', '500'
                ])
                
                if is_llm_error and attempt < max_retries - 1:
                    # For rate limiting, use longer delays (exponential backoff with minimum)
                    if is_rate_limit:
                        # Rate limit: wait longer (30s, 60s, 120s)
                        wait_time = max(30, retry_delay * (2 ** attempt))
                        logger.warning(f"Rate limit detected. Waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                    else:
                        # Other errors: shorter delay
                        wait_time = retry_delay * (attempt + 1)
                        logger.info(f"LLM error detected, attempting to reconnect...")
                        try:
                            # Reinitialize analyzer to get fresh connection
                            self.analyzer = CodeAnalyzer()
                            logger.info(f"Reconnected to LLM provider: {self.analyzer.provider}")
                        except Exception as reconnect_error:
                            logger.error(f"Failed to reconnect to LLM: {reconnect_error}")
                    
                    # Wait before retry
                    import time
                    time.sleep(wait_time)
                    continue
                else:
                    # Not retryable or max retries reached
                    if attempt == max_retries - 1:
                        logger.error(f"Failed to analyze entity {entity_data['name']} after {max_retries} attempts")
                        # Log final failure to file if enabled (analyzer already logs each attempt, but this is the final state)
                        if settings.LOG_FAILED_ANALYSES_TO_FILE:
                            try:
                                from datetime import datetime
                                import os
                                log_file = settings.LOG_FAILED_ANALYSES_FILE_PATH
                                log_dir = os.path.dirname(log_file)
                                if log_dir and not os.path.exists(log_dir):
                                    os.makedirs(log_dir, exist_ok=True)
                                
                                with open(log_file, 'a', encoding='utf-8') as f:
                                    f.write(f"\n{'='*80}\n")
                                    f.write(f"FINAL FAILURE - All retries exhausted\n")
                                    f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                                    f.write(f"Entity: {entity_data['name']} ({entity_data['type']})\n")
                                    f.write(f"Language: {project.language}\n")
                                    f.write(f"Provider: {self.analyzer.provider}\n")
                                    f.write(f"Model: {self.analyzer.model}\n")
                                    f.write(f"Total Attempts: {max_retries}\n")
                                    f.write(f"Error Message: {error_msg}\n")
                                    f.write(f"Error Type: {type(e).__name__}\n")
                                    f.write(f"{'='*80}\n\n")
                            except Exception as log_error:
                                logger.warning(f"Failed to log final failure to file: {log_error}")
                    break
        
        # If analysis failed, create minimal analysis with static metrics
        if analysis_result is None:
            logger.warning(f"Using fallback analysis for entity {entity_data['name']}")
            from app.api.models.schemas import CodeAnalysisResult, ComplexityClass
            from app.analyzers.static_metrics import StaticMetricsAnalyzer
            
            # Still compute static metrics even if LLM analysis failed
            static_analyzer = StaticMetricsAnalyzer()
            static_metrics = static_analyzer.analyze(
                code=entity_data['code'],
                language=project.language,
                entity_type=entity_data['type'],
                dependencies=dependency_names
            )
            
            analysis_result = CodeAnalysisResult(
                description='Analysis failed',
                complexity=ComplexityClass.LINEAR,
                complexity_explanation='Could not analyze',
                solid_violations=[],
                design_patterns=[],
                ddd_role=None,
                mvc_role=None,
                is_testable=False,
                testability_score=0.0,
                testability_issues=['Analysis failed'],
                code_fingerprint=entity_data['code'],
                dependencies=[],
                # Include static metrics
                lines_of_code=static_metrics['lines_of_code'],
                cyclomatic_complexity=static_metrics['cyclomatic_complexity'],
                cognitive_complexity=static_metrics['cognitive_complexity'],
                max_nesting_depth=static_metrics['max_nesting_depth'],
                parameter_count=static_metrics['parameter_count'],
                coupling_score=static_metrics['coupling_score'],
                cohesion_score=static_metrics['cohesion_score'],
                afferent_coupling=static_metrics['afferent_coupling'],
                efferent_coupling=static_metrics['efferent_coupling'],
                n_plus_one_queries=static_metrics['n_plus_one_queries'],
                space_complexity=static_metrics['space_complexity'],
                hot_path_detected=static_metrics['hot_path_detected'],
                security_issues=static_metrics['security_issues'],
                hardcoded_secrets=static_metrics['hardcoded_secrets'],
                insecure_dependencies=static_metrics['insecure_dependencies'],
                is_god_object=static_metrics['is_god_object'],
                feature_envy_score=static_metrics['feature_envy_score'],
                data_clumps=static_metrics['data_clumps'],
                long_parameter_list=static_metrics['long_parameter_list'],
            )
        
        # Define complexity map first
        complexity_map = {
            "O(1)": 1,
            "O(log n)": 2,
            "O(n)": 3,
            "O(n log n)": 4,
            "O(n^2)": 5,
            "O(n^3)": 6,
            "O(2^n)": 7,
            "O(n!)": 8,
        }
        
        # For constants, always use O(1) complexity
        if entity_data['type'] == 'constant':
            complexity_value = "O(1)"
            complexity_numeric = 1.0
        else:
            # Convert complexity to numeric
            # Get the actual value from the enum (e.g., "O(1)" instead of "ComplexityClass.CONSTANT")
            if hasattr(analysis_result.complexity, 'value'):
                complexity_value = analysis_result.complexity.value
            elif isinstance(analysis_result.complexity, str):
                complexity_value = analysis_result.complexity
            else:
                complexity_value = str(analysis_result.complexity)
            
            complexity_numeric = complexity_map.get(complexity_value, 3)
        
        # Create analysis record with all metrics
        # Convert SecurityIssue objects to dicts for JSON storage
        security_issues_dict = []
        if hasattr(analysis_result, 'security_issues') and analysis_result.security_issues:
            for issue in analysis_result.security_issues:
                if hasattr(issue, 'dict'):
                    security_issues_dict.append(issue.dict())
                elif isinstance(issue, dict):
                    security_issues_dict.append(issue)
                else:
                    security_issues_dict.append({
                        'type': getattr(issue, 'type', 'unknown'),
                        'severity': str(getattr(issue, 'severity', 'medium')),
                        'description': getattr(issue, 'description', ''),
                        'location': getattr(issue, 'location', ''),
                        'suggestion': getattr(issue, 'suggestion', None)
                    })
        
        analysis = Analysis(
            entity_id=entity.id,
            description=analysis_result.description,
            complexity=complexity_value,
            complexity_numeric=complexity_numeric,
            complexity_explanation=getattr(analysis_result, 'complexity_explanation', None),
            solid_violations=[v.dict() for v in analysis_result.solid_violations],
            design_patterns=analysis_result.design_patterns,
            ddd_role=analysis_result.ddd_role,
            mvc_role=analysis_result.mvc_role,
            is_testable=analysis_result.is_testable,
            testability_score=analysis_result.testability_score,
            testability_issues=analysis_result.testability_issues,
            code_fingerprint=analysis_result.code_fingerprint,
            # Extended metrics
            lines_of_code=getattr(analysis_result, 'lines_of_code', None),
            cyclomatic_complexity=getattr(analysis_result, 'cyclomatic_complexity', None),
            cognitive_complexity=getattr(analysis_result, 'cognitive_complexity', None),
            max_nesting_depth=getattr(analysis_result, 'max_nesting_depth', None),
            parameter_count=getattr(analysis_result, 'parameter_count', None),
            coupling_score=getattr(analysis_result, 'coupling_score', None),
            cohesion_score=getattr(analysis_result, 'cohesion_score', None),
            afferent_coupling=getattr(analysis_result, 'afferent_coupling', None),
            efferent_coupling=getattr(analysis_result, 'efferent_coupling', None),
            n_plus_one_queries=getattr(analysis_result, 'n_plus_one_queries', None) or [],
            space_complexity=getattr(analysis_result, 'space_complexity', None),
            hot_path_detected=getattr(analysis_result, 'hot_path_detected', None),
            security_issues=security_issues_dict,
            hardcoded_secrets=getattr(analysis_result, 'hardcoded_secrets', None) or [],
            insecure_dependencies=getattr(analysis_result, 'insecure_dependencies', None) or [],
            is_god_object=getattr(analysis_result, 'is_god_object', None),
            feature_envy_score=getattr(analysis_result, 'feature_envy_score', None),
            data_clumps=getattr(analysis_result, 'data_clumps', None) or [],
            long_parameter_list=getattr(analysis_result, 'long_parameter_list', None),
        )
        db.add(analysis)
        db.flush()
        
        # Extract and save dependencies (using AST-based extractor, no LLM needed)
        try:
            dependencies_list = self.parser.extract_dependencies(
                entity_data['code'],
                project.language,
                entity_data['code']
            )
            
            logger.info(f"Extracted {len(dependencies_list)} dependencies for {entity_data['name']}")
            
            # Save dependencies to database
            for dep_data in dependencies_list:
                # Try to find the entity this depends on
                depends_on_entity = None
                dep_name = dep_data['name']
                
                # Try to find by full qualified name or name
                if '::' in dep_name or '.' in dep_name:
                    # Method call: Class::method or Class.method
                    depends_on_entity = db.query(Entity).filter(
                        Entity.full_qualified_name == dep_name
                    ).first()
                else:
                    # Class or simple method name
                    # Try full qualified name first
                    depends_on_entity = db.query(Entity).filter(
                        Entity.full_qualified_name == dep_name
                    ).first()
                    
                    # If not found, try by name within the same project (more precise)
                    if not depends_on_entity:
                        depends_on_entity = db.query(Entity).join(File).filter(
                            Entity.name == dep_name,
                            Entity.type == 'class',
                            File.project_id == project.id
                        ).first()
                    
                    # If still not found, try by name in any project (less precise)
                    if not depends_on_entity:
                        depends_on_entity = db.query(Entity).filter(
                            Entity.name == dep_name,
                            Entity.type == 'class'
                        ).first()
                
                dependency = Dependency(
                    entity_id=entity.id,
                    depends_on_entity_id=depends_on_entity.id if depends_on_entity else None,
                    depends_on_name=dep_name,
                    type=dep_data.get('type', 'calls')
                )
                db.add(dependency)
                logger.debug(f"Added dependency: {entity_data['name']} -> {dep_name} ({dep_data.get('type', 'calls')})")
        except Exception as e:
            logger.error(f"Error extracting dependencies for {entity_data['name']}: {e}", exc_info=True)
        
        # Generate keywords for better semantic search
        keywords = self._generate_keywords(entity_data, analysis_result.description, entity_data.get('code', ''))
        analysis.keywords = keywords
        
        # Generate embedding with keywords for better semantic search
        embedding_text = self._build_embedding_text(entity_data, analysis_result.description, keywords)
        embedding = self.embedding_service.generate_embedding(embedding_text)
        
        # Store in Qdrant
        # Qdrant requires numeric ID or UUID, so we use entity.id directly
        point_id = entity.id
        self.qdrant.upsert_embedding(
            point_id=point_id,
            vector=embedding,
            payload={
                "entity_id": entity.id,
                "entity_type": entity_data['type'],
                "name": entity_data['name'],
                "description": analysis_result.description,
                "file_path": file.path,
                "start_line": entity_data['start_line'],
                "end_line": entity_data['end_line']
            }
        )
        
        analysis.embedding_id = str(point_id)  # Store as string in DB
        db.commit()
    
    def _generate_keywords(self, entity_data: Dict, description: str, code: str) -> str:
        """Generate keywords for better semantic search
        
        Extracts synonyms, related terms, and alternative names from:
        - Entity name (e.g., EMAIL_SEND_TIMEOUT -> email, send, timeout, таймаут)
        - Description (extract key terms)
        - Code comments (extract key terms)
        """
        keywords = []
        
        # Extract from entity name
        entity_name = entity_data.get('name', '')
        entity_type = entity_data.get('type', '')
        
        # Split camelCase, UPPER_CASE, and snake_case
        import re
        # Split on uppercase, underscore, or camelCase boundaries
        name_parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', entity_name)
        # Also split on underscores
        name_parts.extend(entity_name.lower().split('_'))
        # Remove empty and very short parts
        name_parts = [p.lower() for p in name_parts if len(p) > 2]
        keywords.extend(name_parts)
        
        # Add entity name itself (lowercase)
        keywords.append(entity_name.lower())
        
        # Extract from description - find key terms
        description_lower = description.lower()
        
        # Common synonyms and related terms
        synonym_map = {
            'timeout': ['таймаут', 'timeout', 'time out', 'wait time', 'waiting time', 'время ожидания'],
            'email': ['email', 'письмо', 'письма', 'почта', 'mail', 'сообщение'],
            'send': ['отправка', 'отправки', 'send', 'sending', 'отправить'],
            'constant': ['константа', 'constant', 'const', 'значение', 'value'],
            'retry': ['повтор', 'retry', 'retries', 'повторная попытка'],
            'size': ['размер', 'size', 'размер файла'],
            'connection': ['соединение', 'connection', 'подключение', 'connect'],
        }
        
        # Check for synonyms in description
        for key, synonyms in synonym_map.items():
            if any(syn in description_lower for syn in synonyms):
                keywords.extend(synonyms)
        
        # Extract from code comments if available
        if code:
            # Look for docblock comments
            comment_pattern = r'/\*\*.*?\*/|//.*?$|#.*?$'
            comments = re.findall(comment_pattern, code, re.DOTALL | re.MULTILINE)
            for comment in comments:
                # Extract words from comments
                comment_words = re.findall(r'\b[a-zа-яё]{3,}\b', comment.lower())
                keywords.extend(comment_words[:10])  # Limit to avoid too many keywords
        
        # Add full_qualified_name parts if available
        full_name = entity_data.get('full_qualified_name', '')
        if full_name:
            # Split on :: and \
            name_parts = re.split(r'[::\\]+', full_name)
            keywords.extend([p.lower() for p in name_parts if len(p) > 2])
        
        # Remove duplicates and join
        unique_keywords = list(dict.fromkeys(keywords))  # Preserves order
        return ', '.join(unique_keywords[:30])  # Limit to 30 keywords
    
    def _build_embedding_text(self, entity_data: Dict, description: str, keywords: str) -> str:
        """Build text for embedding generation
        
        Includes:
        - Entity name
        - Description
        - Keywords (synonyms, related terms)
        """
        parts = [
            entity_data.get('name', ''),
            description
        ]
        
        if keywords:
            parts.append(f"Keywords: {keywords}")
        
        # Add full_qualified_name if available
        full_name = entity_data.get('full_qualified_name', '')
        if full_name:
            parts.append(full_name)
        
        return ' '.join(parts)
    
    def _get_entity_context(self, db: Session, project: Project, entity_data: Dict) -> Optional[str]:
        """Get context (dependencies) for entity based on dependency tree
        
        Builds context from:
        1. Parent classes (extends)
        2. Implemented interfaces (implements)
        3. Imported classes that are indexed
        4. Methods/classes that this entity calls
        """
        context_parts = []
        
        # Extract dependencies from code
        try:
            dependencies_list = self.parser.extract_dependencies(
                entity_data['code'],
                project.language,
                entity_data['code']
            )
        except Exception as e:
            logger.warning(f"Error extracting dependencies for context: {e}")
            return None
        
        # Group dependencies by type
        extends_deps = [d for d in dependencies_list if d.get('type') == 'extends']
        implements_deps = [d for d in dependencies_list if d.get('type') == 'implements']
        import_deps = [d for d in dependencies_list if d.get('type') == 'import']
        calls_deps = [d for d in dependencies_list if d.get('type') == 'calls']
        
        # Find and include parent classes (extends)
        for dep in extends_deps:
            dep_name = dep['name']
            # Try to find the parent class
            parent_entity = self._find_dependency_entity(db, project, dep_name, 'class')
            if parent_entity:
                if parent_entity.analysis:
                    context_parts.append(f"Parent class '{dep_name}':\n{parent_entity.code}\nDescription: {parent_entity.analysis.description}")
                else:
                    # Entity exists but not analyzed yet - include code only
                    context_parts.append(f"Parent class '{dep_name}':\n{parent_entity.code}")
            else:
                # Try to find in source files directly (for dependencies not yet indexed)
                parent_code = self._find_dependency_in_files(project, dep_name, 'class')
                if parent_code:
                    context_parts.append(f"Parent class '{dep_name}' (from source):\n{parent_code}")
        
        # Find and include implemented interfaces
        for dep in implements_deps:
            dep_name = dep['name']
            interface_entity = self._find_dependency_entity(db, project, dep_name, 'class')
            if interface_entity:
                if interface_entity.analysis:
                    context_parts.append(f"Interface '{dep_name}':\n{interface_entity.code}\nDescription: {interface_entity.analysis.description}")
                else:
                    context_parts.append(f"Interface '{dep_name}':\n{interface_entity.code}")
            else:
                interface_code = self._find_dependency_in_files(project, dep_name, 'class')
                if interface_code:
                    context_parts.append(f"Interface '{dep_name}' (from source):\n{interface_code}")
        
        # Find and include imported classes (limit to most relevant)
        for dep in import_deps[:5]:  # Limit to 5 most important imports
            dep_name = dep['name']
            # Try to find by full name or simple name
            imported_entity = self._find_dependency_entity(db, project, dep_name, 'class')
            if imported_entity:
                if imported_entity.analysis:
                    context_parts.append(f"Imported class '{dep_name}':\n{imported_entity.code}\nDescription: {imported_entity.analysis.description}")
                else:
                    context_parts.append(f"Imported class '{dep_name}':\n{imported_entity.code}")
        
        # Find and include called methods (limit to most relevant)
        for dep in calls_deps[:3]:  # Limit to 3 most important method calls
            dep_name = dep['name']
            # Try to find method by name or full qualified name
            method_entity = self._find_dependency_entity(db, project, dep_name, 'method')
            if method_entity and method_entity.analysis:
                context_parts.append(f"Called method '{dep_name}':\n{method_entity.code}\nDescription: {method_entity.analysis.description}")
        
        if context_parts:
            return "\n\n---\n\n".join(context_parts)
        
        return None
    
    def _find_dependency_entity(self, db: Session, project: Project, dep_name: str, preferred_type: str = None) -> Optional[Entity]:
        """Find entity by dependency name
        
        Args:
            db: Database session
            project: Project
            dep_name: Name of dependency (can be simple name or qualified)
            preferred_type: Preferred entity type (class, method, function)
        """
        # Try full qualified name first
        entity = db.query(Entity).join(File).filter(
            Entity.full_qualified_name == dep_name,
            File.project_id == project.id
        ).first()
        
        if entity:
            return entity
        
        # Try by simple name within project
        query = db.query(Entity).join(File).filter(
            File.project_id == project.id
        )
        
        # Handle qualified names (Class::method, Class.method, Namespace\Class)
        if '::' in dep_name:
            # PHP: Class::method -> try to find method
            parts = dep_name.split('::')
            if len(parts) == 2:
                class_name, method_name = parts
                entity = query.filter(
                    Entity.name == method_name,
                    Entity.type == 'method'
                ).first()
                if entity:
                    return entity
                # Try class
                entity = query.filter(
                    Entity.name == class_name,
                    Entity.type == 'class'
                ).first()
                if entity:
                    return entity
        elif '.' in dep_name:
            # Python: Class.method or module.Class
            parts = dep_name.split('.')
            if len(parts) == 2:
                class_or_module, method_or_class = parts
                # Try method first
                entity = query.filter(
                    Entity.name == method_or_class,
                    Entity.type == 'method'
                ).first()
                if entity:
                    return entity
                # Try class
                entity = query.filter(
                    Entity.name == method_or_class,
                    Entity.type == 'class'
                ).first()
                if entity:
                    return entity
        
        # Try by simple name
        if preferred_type:
            entity = query.filter(
                Entity.name == dep_name,
                Entity.type == preferred_type
            ).first()
            if entity:
                return entity
        
        # Try any type
        entity = query.filter(Entity.name == dep_name).first()
        return entity
    
    def _find_dependency_in_files(self, project: Project, dep_name: str, entity_type: str) -> Optional[str]:
        """Find dependency code directly in source files (for dependencies not yet indexed)
        
        Args:
            project: Project
            dep_name: Name of dependency
            entity_type: Type of entity (class, method, function)
        """
        try:
            project_path = Path(project.path)
            if not project_path.exists():
                return None
            
            # Get all code files
            files = self._get_code_files(project_path, project.language)
            
            # Clean dependency name (remove namespace)
            clean_name = dep_name.split('\\')[-1].split('.')[-1].split('::')[-1]
            
            # Search in files
            for file_path in files:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        code = f.read()
                    
                    # Try to find class/interface definition
                    if entity_type == 'class':
                        if project.language == 'php':
                            # PHP: class Message or class Message extends ...
                            pattern = rf'class\s+{re.escape(clean_name)}\s*(?:extends|implements|\{{)'
                            if re.search(pattern, code):
                                # Extract class code
                                class_match = re.search(rf'class\s+{re.escape(clean_name)}[^{{]*\{{', code)
                                if class_match:
                                    start = class_match.start()
                                    # Find matching closing brace
                                    brace_count = 0
                                    for i in range(start, len(code)):
                                        if code[i] == '{':
                                            brace_count += 1
                                        elif code[i] == '}':
                                            brace_count -= 1
                                            if brace_count == 0:
                                                return code[start:i+1]
                        elif project.language == 'python':
                            # Python: class Message( or class Message:
                            pattern = rf'class\s+{re.escape(clean_name)}\s*[\(:]'
                            if re.search(pattern, code):
                                class_match = re.search(rf'class\s+{re.escape(clean_name)}[^:]*:', code)
                                if class_match:
                                    start = class_match.start()
                                    # Find class end (next class or end of file)
                                    lines = code[start:].split('\n')
                                    indent = len(lines[0]) - len(lines[0].lstrip())
                                    class_lines = [lines[0]]
                                    for line in lines[1:]:
                                        if line.strip() and len(line) - len(line.lstrip()) <= indent and not line.strip().startswith('#'):
                                            break
                                        class_lines.append(line)
                                    return '\n'.join(class_lines)
                
                except Exception as e:
                    logger.debug(f"Error reading file {file_path} for dependency search: {e}")
                    continue
        
        except Exception as e:
            logger.warning(f"Error searching for dependency in files: {e}")
        
        return None
    
    def _sort_entities_by_dependencies(self, entities: List[Dict], language: str) -> List[Dict]:
        """Sort entities by dependency order (base classes first, then dependent classes, then methods)
        
        This ensures that when analyzing a class, its parent classes are already indexed
        and can be included in context for better LLM analysis.
        
        Args:
            entities: List of entity dictionaries
            language: Programming language
            
        Returns:
            Sorted list of entities
        """
        # Separate by type
        classes = [e for e in entities if e['type'] == 'class']
        methods = [e for e in entities if e['type'] in ['method', 'function']]
        constants = [e for e in entities if e['type'] == 'constant']
        
        if not classes:
            # No classes, just return methods as-is
            return methods
        
        # Sort classes by dependencies (classes with no extends first)
        def get_base_classes(entities_list):
            """Get classes that don't extend anything (base classes)"""
            base_classes = []
            dependent_classes = []
            
            for entity in entities_list:
                try:
                    # Extract dependencies
                    deps = self.parser.extract_dependencies(entity['code'], language, entity['code'])
                    extends_deps = [d for d in deps if d.get('type') == 'extends']
                    
                    if not extends_deps:
                        # No parent class - this is a base class
                        base_classes.append(entity)
                    else:
                        dependent_classes.append(entity)
                except Exception:
                    # If dependency extraction fails, treat as base class
                    base_classes.append(entity)
            
            return base_classes, dependent_classes
        
        base_classes, dependent_classes = get_base_classes(classes)
        
        # Sort dependent classes by number of inheritance levels (simple heuristic)
        # Classes extending base classes come first
        sorted_classes = base_classes.copy()
        
        # Add dependent classes (they will have context from base classes)
        for cls in dependent_classes:
            # Find position: after its parent if parent is in the list
            inserted = False
            try:
                deps = self.parser.extract_dependencies(cls['code'], language, cls['code'])
                extends_deps = [d for d in deps if d.get('type') == 'extends']
                
                if extends_deps:
                    parent_name = extends_deps[0]['name']
                    # Clean parent name (remove namespace)
                    parent_name_clean = parent_name.split('\\')[-1].split('.')[-1]
                    # Find parent in sorted list
                    for i, existing_cls in enumerate(sorted_classes):
                        if existing_cls['name'] == parent_name_clean or existing_cls['name'] == parent_name:
                            sorted_classes.insert(i + 1, cls)
                            inserted = True
                            break
            except Exception:
                pass
            
            if not inserted:
                sorted_classes.append(cls)
        
        # Add constants at the end (they can use class context)
        # Add methods/functions at the very end (they can use class context)
        return sorted_classes + constants + methods
    
    def _delete_file_data(self, db: Session, file_id: int):
        """Delete all data for a file"""
        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            return
        
        # Delete embeddings from Qdrant
        entities = db.query(Entity).filter(Entity.file_id == file_id).all()
        for entity in entities:
            if entity.analysis and entity.analysis.embedding_id:
                # Convert string ID back to int for Qdrant
                try:
                    point_id = int(entity.analysis.embedding_id)
                    self.qdrant.delete(point_id)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid embedding_id format: {entity.analysis.embedding_id}")
        
        # Delete from DB (cascade will handle related records)
        db.delete(file)
        db.commit()
    
    def delete_entities(
        self,
        project_id: Optional[int] = None,
        file_id: Optional[int] = None,
        entity_ids: Optional[List[int]] = None,
        delete_all: bool = False
    ):
        """Delete entities from index
        
        Args:
            project_id: Project ID (required if delete_all=True)
            file_id: Optional file ID to delete entities from
            entity_ids: Optional list of entity IDs to delete
            delete_all: Delete all entities from project
        """
        db = SessionLocal()
        try:
            if delete_all and project_id:
                # Delete all entities from project
                project = db.query(Project).filter(Project.id == project_id).first()
                if not project:
                    raise ValueError(f"Project {project_id} not found")
                
                # Stop indexing if it's running
                if project.is_indexing and project.indexing_task_id:
                    logger.info(f"Stopping indexing task {project.indexing_task_id} before deleting entities")
                    try:
                        celery_app.control.revoke(project.indexing_task_id, terminate=True)
                        logger.info(f"Successfully revoked indexing task {project.indexing_task_id}")
                    except Exception as e:
                        logger.warning(f"Failed to revoke indexing task {project.indexing_task_id}: {e}")
                
                # Get all files for this project
                files = db.query(File).filter(File.project_id == project_id).all()
                
                # Delete embeddings from Qdrant and entities from DB
                deleted_count = 0
                for file in files:
                    entities = db.query(Entity).filter(Entity.file_id == file.id).all()
                    for entity in entities:
                        if entity.analysis and entity.analysis.embedding_id:
                            try:
                                point_id = int(entity.analysis.embedding_id)
                                self.qdrant.delete(point_id)
                            except (ValueError, TypeError):
                                logger.warning(f"Invalid embedding_id format: {entity.analysis.embedding_id}")
                        deleted_count += 1
                
                # Delete all files (cascade will delete entities and analyses)
                for file in files:
                    db.delete(file)
                
                # Update project counters - recalculate from actual DB state
                project.total_entities = 0
                project.indexed_files = 0
                project.total_files = 0  # Also reset total_files
                project.tokens_used = 0  # Reset token usage when deleting all entities
                project.is_indexing = False
                project.indexing_task_id = None
                project.indexing_status = None
                project.current_file_path = None
                project.last_indexed_file_path = None
                
                db.commit()
                logger.info(f"Deleted all entities from project {project_id}: {deleted_count} entities. Reset tokens_used to 0")
                
            elif file_id:
                # Delete entities from specific file
                file = db.query(File).filter(File.id == file_id).first()
                if not file:
                    raise ValueError(f"File {file_id} not found")
                
                project = db.query(Project).filter(Project.id == file.project_id).first()
                if not project:
                    raise ValueError(f"Project not found for file {file_id}")
                
                # Stop indexing if it's running (to prevent creating new entities while deleting)
                if project.is_indexing and project.indexing_task_id:
                    logger.info(f"Stopping indexing task {project.indexing_task_id} before deleting entities from file")
                    try:
                        celery_app.control.revoke(project.indexing_task_id, terminate=True)
                        logger.info(f"Successfully revoked indexing task {project.indexing_task_id}")
                    except Exception as e:
                        logger.warning(f"Failed to revoke indexing task {project.indexing_task_id}: {e}")
                
                # Delete embeddings from Qdrant
                entities = db.query(Entity).filter(Entity.file_id == file_id).all()
                deleted_count = len(entities)
                for entity in entities:
                    if entity.analysis and entity.analysis.embedding_id:
                        try:
                            point_id = int(entity.analysis.embedding_id)
                            self.qdrant.delete(point_id)
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid embedding_id format: {entity.analysis.embedding_id}")
                
                # Delete file (cascade will delete entities and analyses)
                db.delete(file)
                
                # Update project counters - recalculate from actual DB state
                actual_entities = db.query(func.count(Entity.id)).join(File).filter(
                    File.project_id == project.id
                ).scalar()
                actual_files = db.query(func.count(File.id)).filter(
                    File.project_id == project.id
                ).scalar()
                
                project.total_entities = actual_entities
                project.indexed_files = actual_files
                project.total_files = actual_files
                project.tokens_used = 0  # Reset token usage when deleting entities
                
                db.commit()
                logger.info(f"Deleted {deleted_count} entities from file {file_id}. Updated counters: {actual_entities} entities, {actual_files} files. Reset tokens_used to 0")
                
            elif entity_ids:
                # Delete specific entities
                entities = db.query(Entity).filter(Entity.id.in_(entity_ids)).all()
                if not entities:
                    logger.warning(f"No entities found with IDs: {entity_ids}")
                    return
                
                # Get project for counter update
                file_ids = set(e.file_id for e in entities)
                files = db.query(File).filter(File.id.in_(file_ids)).all()
                project_ids = set(f.project_id for f in files)
                
                if len(project_ids) > 1:
                    logger.warning(f"Entities belong to multiple projects: {project_ids}")
                
                # Stop indexing for all affected projects (to prevent creating new entities while deleting)
                for project_id in project_ids:
                    project = db.query(Project).filter(Project.id == project_id).first()
                    if project and project.is_indexing and project.indexing_task_id:
                        logger.info(f"Stopping indexing task {project.indexing_task_id} for project {project_id} before deleting entities")
                        try:
                            celery_app.control.revoke(project.indexing_task_id, terminate=True)
                            logger.info(f"Successfully revoked indexing task {project.indexing_task_id}")
                            # Update project state
                            project.is_indexing = False
                            project.indexing_task_id = None
                            db.commit()
                        except Exception as e:
                            logger.warning(f"Failed to revoke indexing task {project.indexing_task_id}: {e}")
                
                # Delete embeddings from Qdrant
                deleted_count = 0
                for entity in entities:
                    if entity.analysis and entity.analysis.embedding_id:
                        try:
                            point_id = int(entity.analysis.embedding_id)
                            self.qdrant.delete(point_id)
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid embedding_id format: {entity.analysis.embedding_id}")
                    deleted_count += 1
                
                # Delete entities (cascade will delete analyses)
                for entity in entities:
                    db.delete(entity)
                
                # Update project counters - recalculate from actual DB state
                for project_id in project_ids:
                    project = db.query(Project).filter(Project.id == project_id).first()
                    if project:
                        actual_entities = db.query(func.count(Entity.id)).join(File).filter(
                            File.project_id == project.id
                        ).scalar()
                        actual_files = db.query(func.count(File.id)).filter(
                            File.project_id == project.id
                        ).scalar()
                        project.total_entities = actual_entities
                        project.total_files = actual_files
                        project.indexed_files = actual_files
                        project.tokens_used = 0  # Reset token usage when deleting entities
                        db.commit()
                
                logger.info(f"Deleted {deleted_count} entities with IDs: {entity_ids}. Reset tokens_used to 0 for affected projects")
            else:
                raise ValueError("Must specify project_id (with delete_all=True), file_id, or entity_ids")
                
        except Exception as e:
            logger.error(f"Error deleting entities: {e}")
            db.rollback()
            raise
        finally:
            db.close()

