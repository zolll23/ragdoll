"""
IDE API Endpoints
Provides endpoints for IDE plugins (PhpStorm, PyCharm) to access code analysis
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.database import Entity, Analysis, File, Project, Dependency
from app.api.models.schemas import EntityResponse, AnalysisResponse
from app.services.search_service import SearchService

router = APIRouter(prefix="/api/ide", tags=["ide"])


# Request/Response models for IDE API
class FileLocationRequest(BaseModel):
    """Request to find entity by file location"""
    project_id: int
    file_path: str  # Relative to project root
    line_number: Optional[int] = None  # If provided, find entity at this line


class EntityAnalysisRequest(BaseModel):
    """Request for entity analysis"""
    entity_id: Optional[int] = None
    project_id: Optional[int] = None
    file_path: Optional[str] = None
    entity_name: Optional[str] = None
    line_number: Optional[int] = None


class SearchRequest(BaseModel):
    """Search request for IDE"""
    query: str
    project_id: Optional[int] = None
    limit: int = Field(default=20, ge=1, le=100)


class RefactoringRequest(BaseModel):
    """Request for refactoring suggestions"""
    entity_id: int
    include_similar_code: bool = True
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class IDEEntityResponse(BaseModel):
    """Enhanced entity response for IDE"""
    entity: EntityResponse
    analysis: Optional[AnalysisResponse] = None
    dependencies: List[Dict[str, Any]] = Field(default_factory=list)
    metrics: Optional[Dict[str, Any]] = None


@router.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "ide-api"}


@router.post("/find-entity", response_model=IDEEntityResponse)
def find_entity_by_location(
    request: FileLocationRequest,
    db: Session = Depends(get_db)
):
    """Find entity by file path and optional line number"""
    # Find project
    project = db.query(Project).filter(Project.id == request.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Find file
    file = db.query(File).filter(
        File.project_id == request.project_id,
        File.path == request.file_path
    ).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Find entity
    if request.line_number:
        # Find entity that contains this line
        entity = db.query(Entity).filter(
            Entity.file_id == file.id,
            Entity.start_line <= request.line_number,
            Entity.end_line >= request.line_number
        ).order_by(Entity.start_line.desc()).first()
    else:
        # Return first entity in file (or raise error)
        entity = db.query(Entity).filter(Entity.file_id == file.id).first()
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found at specified location")
    
    return _build_ide_entity_response(db, entity)


@router.post("/analyze", response_model=IDEEntityResponse)
def analyze_entity(
    request: EntityAnalysisRequest,
    db: Session = Depends(get_db)
):
    """Analyze entity by ID, file path, or location"""
    entity = None
    
    if request.entity_id:
        entity = db.query(Entity).filter(Entity.id == request.entity_id).first()
    elif request.file_path and request.entity_name and request.project_id:
        # Find by file path and name
        file = db.query(File).filter(
            File.project_id == request.project_id,
            File.path == request.file_path
        ).first()
        if file:
            entity = db.query(Entity).filter(
                Entity.file_id == file.id,
                Entity.name == request.entity_name
            ).first()
    elif request.file_path and request.line_number and request.project_id:
        # Find by file path and line number
        file = db.query(File).filter(
            File.project_id == request.project_id,
            File.path == request.file_path
        ).first()
        if file:
            entity = db.query(Entity).filter(
                Entity.file_id == file.id,
                Entity.start_line <= request.line_number,
                Entity.end_line >= request.line_number
            ).order_by(Entity.start_line.desc()).first()
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    return _build_ide_entity_response(db, entity)


@router.post("/search", response_model=List[Dict[str, Any]])
def search_code(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    """Search code using natural language query"""
    service = SearchService()
    
    results = service.search(
        db=db,
        query=request.query,
        project_id=request.project_id,
        limit=request.limit
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
            "full_qualified_name": entity.full_qualified_name,
            "description": analysis.description if analysis else None,
            "complexity": analysis.complexity if analysis else None,
            "score": result.score,
            "match_type": result.match_type
        })
    
    return formatted_results


@router.post("/refactoring", response_model=Dict[str, Any])
def get_refactoring_suggestions(
    request: RefactoringRequest,
    db: Session = Depends(get_db)
):
    """Get refactoring suggestions for an entity"""
    entity = db.query(Entity).filter(Entity.id == request.entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    file = db.query(File).filter(File.id == entity.file_id).first()
    analysis = db.query(Analysis).filter(Analysis.entity_id == request.entity_id).first()
    
    suggestions = {
        "entity_id": request.entity_id,
        "entity_name": entity.name,
        "file_path": file.path if file else None,
        "suggestions": [],
        "similar_code": []
    }
    
    # SOLID violations
    if analysis and analysis.solid_violations:
        for violation in analysis.solid_violations:
            suggestions["suggestions"].append({
                "type": "solid_violation",
                "principle": violation.get("principle"),
                "description": violation.get("description"),
                "severity": violation.get("severity", "medium"),
                "suggestion": violation.get("suggestion"),
                "location": {
                    "file_path": file.path if file else None,
                    "start_line": entity.start_line,
                    "end_line": entity.end_line
                }
            })
    
    # Code quality issues
    if analysis:
        issues = []
        
        # High complexity
        if analysis.cyclomatic_complexity and analysis.cyclomatic_complexity > 10:
            issues.append({
                "type": "high_complexity",
                "description": f"Cyclomatic complexity is {analysis.cyclomatic_complexity} (recommended: < 10)",
                "severity": "medium",
                "suggestion": "Consider breaking down into smaller methods"
            })
        
        # Security issues
        if analysis.security_issues:
            for sec_issue in analysis.security_issues:
                issues.append({
                    "type": "security",
                    "description": sec_issue.get("description", "Security issue detected"),
                    "severity": sec_issue.get("severity", "high"),
                    "suggestion": sec_issue.get("suggestion"),
                    "location": sec_issue.get("location")
                })
        
        # N+1 queries
        if analysis.n_plus_one_queries:
            for n1_issue in analysis.n_plus_one_queries:
                issues.append({
                    "type": "n_plus_one",
                    "description": n1_issue,
                    "severity": "high",
                    "suggestion": "Use eager loading or batch queries"
                })
        
        # God object
        if analysis.is_god_object:
            issues.append({
                "type": "god_object",
                "description": "This class has too many responsibilities",
                "severity": "medium",
                "suggestion": "Split into smaller, focused classes"
            })
        
        # Long parameter list
        if analysis.long_parameter_list:
            issues.append({
                "type": "long_parameter_list",
                "description": f"Method has {analysis.parameter_count} parameters (recommended: < 5)",
                "severity": "low",
                "suggestion": "Consider using a parameter object or builder pattern"
            })
        
        suggestions["suggestions"].extend(issues)
    
    # Similar code (if requested)
    if request.include_similar_code:
        # This would call the similar code search endpoint
        # For now, return empty list
        suggestions["similar_code"] = []
    
    return suggestions


@router.get("/entity/{entity_id}/metrics", response_model=Dict[str, Any])
def get_entity_metrics(
    entity_id: int,
    db: Session = Depends(get_db)
):
    """Get all metrics for an entity"""
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    analysis = db.query(Analysis).filter(Analysis.entity_id == entity_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not available")
    
    return {
        "entity_id": entity_id,
        "entity_name": entity.name,
        "metrics": {
            "size": {
                "lines_of_code": analysis.lines_of_code,
                "parameter_count": analysis.parameter_count
            },
            "complexity": {
                "cyclomatic": analysis.cyclomatic_complexity,
                "cognitive": analysis.cognitive_complexity,
                "max_nesting_depth": analysis.max_nesting_depth,
                "asymptotic": analysis.complexity,
                "space": analysis.space_complexity
            },
            "coupling": {
                "coupling_score": analysis.coupling_score,
                "cohesion_score": analysis.cohesion_score,
                "afferent_coupling": analysis.afferent_coupling,
                "efferent_coupling": analysis.efferent_coupling
            },
            "quality": {
                "is_testable": analysis.is_testable,
                "testability_score": analysis.testability_score,
                "is_god_object": analysis.is_god_object,
                "feature_envy_score": analysis.feature_envy_score,
                "long_parameter_list": analysis.long_parameter_list
            },
            "issues": {
                "security_issues_count": len(analysis.security_issues or []),
                "n_plus_one_queries_count": len(analysis.n_plus_one_queries or []),
                "solid_violations_count": len(analysis.solid_violations or [])
            }
        }
    }


@router.get("/projects", response_model=List[Dict[str, Any]])
def list_projects(
    db: Session = Depends(get_db)
):
    """List all projects for IDE selection, ordered by ID descending (newest first)"""
    projects = db.query(Project).order_by(Project.id.desc()).all()
    
    return [
        {
            "id": p.id,
            "name": p.name,
            "path": p.path,
            "language": p.language,
            "total_files": p.total_files,
            "indexed_files": p.indexed_files,
            "total_entities": p.total_entities,
            "is_indexing": p.is_indexing,
            "progress_percent": (
                (p.indexed_files / p.total_files * 100) if p.total_files > 0 else 0
            )
        }
        for p in projects
    ]


def _build_ide_entity_response(db: Session, entity: Entity) -> IDEEntityResponse:
    """Build IDE entity response with all related data"""
    file = db.query(File).filter(File.id == entity.file_id).first()
    analysis = db.query(Analysis).filter(Analysis.entity_id == entity.id).first()
    
    # Get dependencies
    dependencies = db.query(Dependency).filter(Dependency.entity_id == entity.id).all()
    
    # Build entity response
    entity_response = EntityResponse(
        id=entity.id,
        type=entity.type,
        name=entity.name,
        start_line=entity.start_line,
        end_line=entity.end_line,
        visibility=entity.visibility,
        full_qualified_name=entity.full_qualified_name,
        file_path=file.path if file else "",
        code=entity.code
    )
    
    # Build analysis response
    analysis_response = None
    if analysis:
        analysis_response = AnalysisResponse(
            id=analysis.id,
            description=analysis.description,
            complexity=_convert_complexity(analysis.complexity),
            complexity_explanation=analysis.complexity_explanation,
            complexity_numeric=analysis.complexity_numeric,
            solid_violations=analysis.solid_violations or [],
            design_patterns=analysis.design_patterns or [],
            ddd_role=analysis.ddd_role,
            mvc_role=analysis.mvc_role,
            is_testable=analysis.is_testable,
            testability_score=analysis.testability_score,
            testability_issues=analysis.testability_issues or [],
            entity=entity_response,
            # Extended metrics
            lines_of_code=analysis.lines_of_code,
            cyclomatic_complexity=analysis.cyclomatic_complexity,
            cognitive_complexity=analysis.cognitive_complexity,
            max_nesting_depth=analysis.max_nesting_depth,
            parameter_count=analysis.parameter_count,
            coupling_score=analysis.coupling_score,
            cohesion_score=analysis.cohesion_score,
            afferent_coupling=analysis.afferent_coupling,
            efferent_coupling=analysis.efferent_coupling,
            n_plus_one_queries=analysis.n_plus_one_queries or [],
            space_complexity=analysis.space_complexity,
            hot_path_detected=analysis.hot_path_detected,
            security_issues=analysis.security_issues or [],
            hardcoded_secrets=analysis.hardcoded_secrets or [],
            insecure_dependencies=analysis.insecure_dependencies or [],
            is_god_object=analysis.is_god_object,
            feature_envy_score=analysis.feature_envy_score,
            data_clumps=analysis.data_clumps or [],
            long_parameter_list=analysis.long_parameter_list,
            keywords=analysis.keywords
        )
    
    # Build dependencies list
    deps_list = []
    for dep in dependencies:
        dep_entity = None
        if dep.depends_on_entity_id:
            dep_entity = db.query(Entity).filter(Entity.id == dep.depends_on_entity_id).first()
        
        deps_list.append({
            "id": dep.id,
            "type": dep.type,
            "depends_on_name": dep.depends_on_name,
            "depends_on_entity_id": dep.depends_on_entity_id,
            "depends_on_entity": {
                "id": dep_entity.id,
                "name": dep_entity.name,
                "type": dep_entity.type,
                "file_path": dep_entity.file_path if hasattr(dep_entity, 'file_path') else None
            } if dep_entity else None
        })
    
    # Build metrics summary
    metrics = None
    if analysis:
        metrics = {
            "size": {
                "lines_of_code": analysis.lines_of_code,
                "parameter_count": analysis.parameter_count
            },
            "complexity": {
                "cyclomatic": analysis.cyclomatic_complexity,
                "cognitive": analysis.cognitive_complexity,
                "max_nesting_depth": analysis.max_nesting_depth,
                "asymptotic": analysis.complexity,
                "space": analysis.space_complexity
            },
            "coupling": {
                "coupling_score": analysis.coupling_score,
                "cohesion_score": analysis.cohesion_score,
                "afferent_coupling": analysis.afferent_coupling,
                "efferent_coupling": analysis.efferent_coupling
            },
            "quality": {
                "is_testable": analysis.is_testable,
                "testability_score": analysis.testability_score,
                "is_god_object": analysis.is_god_object,
                "feature_envy_score": analysis.feature_envy_score,
                "long_parameter_list": analysis.long_parameter_list
            },
            "issues": {
                "security_issues": analysis.security_issues or [],
                "n_plus_one_queries": analysis.n_plus_one_queries or [],
                "solid_violations": analysis.solid_violations or []
            }
        }
    
    return IDEEntityResponse(
        entity=entity_response,
        analysis=analysis_response,
        dependencies=deps_list,
        metrics=metrics
    )

