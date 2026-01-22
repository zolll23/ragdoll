"""
MCP Resources for CodeRAG
Provides access to code analysis data as resources
"""
import logging
import os
import sys
from typing import List, Dict, Any
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# MCP types (simplified, no external dependency)
from app.core.database import SessionLocal
from app.models.database import Entity, Analysis, File, Project

logger = logging.getLogger(__name__)


class CodeRAGResources:
    """Resources for code analysis data"""
    
    async def get_resources(self) -> List[Dict[str, Any]]:
        """Get list of available resources"""
        return [
            {
                "uri": "coderag://projects",
                "name": "Projects",
                "description": "List of all indexed projects",
                "mimeType": "application/json"
            },
            {
                "uri": "coderag://entity/{entity_id}",
                "name": "Entity",
                "description": "Get entity details by ID (use entity_id in URI)",
                "mimeType": "application/json"
            },
            {
                "uri": "coderag://analysis/{entity_id}",
                "name": "Analysis",
                "description": "Get analysis for entity by ID (use entity_id in URI)",
                "mimeType": "application/json"
            }
        ]
    
    async def read_resource(self, uri: str) -> str:
        """Read a resource by URI"""
        if uri == "coderag://projects":
            return await self._get_projects()
        elif uri.startswith("coderag://entity/"):
            entity_id = int(uri.split("/")[-1])
            return await self._get_entity(entity_id)
        elif uri.startswith("coderag://analysis/"):
            entity_id = int(uri.split("/")[-1])
            return await self._get_analysis(entity_id)
        else:
            raise ValueError(f"Unknown resource URI: {uri}")
    
    async def _get_projects(self) -> str:
        """Get all projects"""
        db = SessionLocal()
        try:
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
        finally:
            db.close()
    
    async def _get_entity(self, entity_id: int) -> str:
        """Get entity by ID"""
        db = SessionLocal()
        try:
            entity = db.query(Entity).filter(Entity.id == entity_id).first()
            if not entity:
                return json.dumps({"error": "Entity not found"}, indent=2)
            
            file = db.query(File).filter(File.id == entity.file_id).first()
            
            result = {
                "id": entity.id,
                "name": entity.name,
                "type": entity.type,
                "file_path": file.path if file else "",
                "start_line": entity.start_line,
                "end_line": entity.end_line,
                "full_qualified_name": entity.full_qualified_name,
                "code": entity.code
            }
            
            return json.dumps(result, indent=2)
        finally:
            db.close()
    
    async def _get_analysis(self, entity_id: int) -> str:
        """Get analysis for entity"""
        db = SessionLocal()
        try:
            entity = db.query(Entity).filter(Entity.id == entity_id).first()
            if not entity:
                return json.dumps({"error": "Entity not found"}, indent=2)
            
            analysis = db.query(Analysis).filter(Analysis.entity_id == entity_id).first()
            
            if not analysis:
                return json.dumps({"error": "Analysis not available"}, indent=2)
            
            result = {
                "entity_id": entity_id,
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
            
            return json.dumps(result, indent=2)
        finally:
            db.close()

