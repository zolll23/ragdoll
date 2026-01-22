from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from app.core.database import get_db
from app.models.database import Project, File, Entity, Analysis
from app.api.models.schemas import ProjectCreate, ProjectResponse, ProjectProgressResponse
from app.services.indexer import IndexingService
from app.core.celery_app import celery_app

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("/", response_model=ProjectResponse, status_code=201)
def create_project(
    project: ProjectCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create a new project and start indexing"""
    # Check if project already exists
    existing = db.query(Project).filter(Project.path == project.path).first()
    if existing:
        raise HTTPException(status_code=400, detail="Project with this path already exists")
    
    db_project = Project(
        name=project.name,
        path=project.path,
        language=project.language,
        ui_language=project.ui_language
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    # Start indexing in background
    task = celery_app.send_task('index_project', args=[db_project.id])
    db_project.indexing_task_id = task.id
    db_project.is_indexing = True
    db.commit()
    db.refresh(db_project)
    
    return db_project


@router.get("/", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    """List all projects, ordered by ID descending (newest first)"""
    return db.query(Project).order_by(Project.id.desc()).all()


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Get project by ID"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/{project_id}/reindex")
def reindex_project(
    project_id: int,
    only_failed: bool = Query(False, description="Only reindex entities with failed analysis"),
    db: Session = Depends(get_db)
):
    """Reindex project
    
    Args:
        project_id: Project ID
        only_failed: If True, only reindex entities with failed analysis
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Start reindexing in background
    task = celery_app.send_task('reindex_changed_files', args=[project_id], kwargs={'only_failed': only_failed})
    
    # Update project state if reindexing failed
    if only_failed:
        project.is_reindexing_failed = True
        project.reindexing_failed_task_id = task.id
        project.reindexing_failed_status = "Starting reindexing of failed entities..."
        db.commit()
    
    message = "Reindexing failed analyses started" if only_failed else "Reindexing started"
    return {"message": message, "project_id": project_id, "only_failed": only_failed, "task_id": task.id}


@router.get("/{project_id}/progress", response_model=ProjectProgressResponse)
def get_project_progress(project_id: int, db: Session = Depends(get_db)):
    """Get indexing progress for a project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Count total files in project directory
    from pathlib import Path
    project_path = Path(project.path)
    if project_path.exists():
        extensions = ['.py'] if project.language == 'python' else ['.php']
        # Use same logic as indexer to count files
        exclude_dirs = {'__pycache__', '.git', 'node_modules', 'vendor', 'tests', 'test', 'data', 'migrations'}
        total_files = 0
        for ext in extensions:
            for file_path in project_path.rglob(f'*{ext}'):
                # Filter out excluded directories (same as indexer)
                if not any(exclude in file_path.parts for exclude in exclude_dirs):
                    total_files += 1
    else:
        total_files = 0
    
    # Use project.indexed_files and project.total_files from DB for consistency
    # This ensures the progress matches what the indexer reports
    db_indexed_files = project.indexed_files if project.indexed_files is not None else 0
    db_total_files = project.total_files if project.total_files is not None else total_files
    
    # Use DB values if available, otherwise count from files
    indexed_files = db_indexed_files if db_indexed_files > 0 or project.indexed_files is not None else (
        db.query(func.count(File.id)).filter(
            File.project_id == project_id,
            File.indexed_at.isnot(None)
        ).scalar() or 0
    )
    
    total_files = db_total_files if db_total_files > 0 or project.total_files is not None else total_files
    
    # Count total entities - always count from DB to ensure accuracy
    # Count only unique entities (deduplicate by name, file_id, start_line, end_line)
    total_entities_counted = db.query(
        Entity.name,
        Entity.file_id,
        Entity.start_line,
        Entity.end_line
    ).join(File).filter(
        File.project_id == project_id
    ).distinct().count() or 0
    
    # Use DB value if it's set and matches reality, otherwise use counted value
    # This handles cases where project.total_entities is outdated
    if project.total_entities and project.total_entities > 0:
        # If DB value exists, use it, but ensure it's not too far off from reality
        if abs(project.total_entities - total_entities_counted) <= 10:  # Allow small discrepancy
            total_entities = project.total_entities
        else:
            # DB value is too different from reality, use counted value
            total_entities = total_entities_counted
    else:
        # DB value is 0 or None, use counted value
        total_entities = total_entities_counted
    
    # Count entities with successful analysis (not failed and exists)
    # Count only unique entities (deduplicate by name, file_id, start_line, end_line)
    entities_with_analysis = db.query(
        Entity.name,
        Entity.file_id,
        Entity.start_line,
        Entity.end_line
    ).join(File).join(Analysis).filter(
        File.project_id == project_id,
        Analysis.description != 'Analysis failed'
    ).distinct().count() or 0
    
    # Count entities with failed analysis
    # Count only unique entities (deduplicate by name, file_id, start_line, end_line)
    entities_with_failed_analysis = db.query(
        Entity.name,
        Entity.file_id,
        Entity.start_line,
        Entity.end_line
    ).join(File).join(Analysis).filter(
        File.project_id == project_id,
        Analysis.description == 'Analysis failed'
    ).distinct().count() or 0
    
    # Count entities without analysis - use LEFT JOIN for accuracy
    # Count only unique entities (deduplicate by name, file_id, start_line, end_line)
    # This prevents counting duplicate entities multiple times
    entities_without_analysis_query = db.query(
        Entity.name,
        Entity.file_id,
        Entity.start_line,
        Entity.end_line
    ).join(File).outerjoin(Analysis).filter(
        File.project_id == project_id,
        Analysis.id.is_(None)
    ).distinct()
    
    entities_without_analysis = entities_without_analysis_query.count() or 0
    
    # Ensure we don't have negative values (sanity check)
    if entities_without_analysis < 0:
        # Fallback to calculation if LEFT JOIN gives unexpected result
        entities_without_analysis = max(0, total_entities - entities_with_analysis - entities_with_failed_analysis)
    
    # Calculate progress based on files AND entities with successful analysis
    # Progress = (indexed_files / total_files) * 0.5 + (entities_with_analysis / total_entities) * 0.5
    # This gives equal weight to file indexing and entity analysis completion
    # If there are failed or missing analyses, progress will be less than 100%
    file_progress = (indexed_files / total_files * 100) if total_files > 0 else 0.0
    entity_progress = (entities_with_analysis / total_entities * 100) if total_entities > 0 else 0.0
    progress_percent = (file_progress * 0.5 + entity_progress * 0.5) if total_files > 0 and total_entities > 0 else file_progress
    
    # Ensure progress never exceeds 100% and reflects actual completion
    progress_percent = min(progress_percent, 100.0)
    
    # Check if indexing is in progress
    # Only use project.is_indexing from DB, don't infer from file counts
    # This ensures UI shows correct status after indexing completes
    is_indexing = project.is_indexing if project.is_indexing is not None else False
    
    # Get current file and status from project
    current_file = None
    if project.current_file_path:
        from pathlib import Path
        current_file = Path(project.current_file_path).name
    
    return ProjectProgressResponse(
        project_id=project_id,
        total_files=total_files,
        indexed_files=indexed_files,
        total_entities=total_entities,
        progress_percent=round(progress_percent, 2),
        is_indexing=is_indexing,
        current_file=current_file,
        status_message=project.indexing_status,
        entities_with_analysis=entities_with_analysis,
        entities_with_failed_analysis=entities_with_failed_analysis,
        entities_without_analysis=entities_without_analysis,
        is_reindexing_failed=project.is_reindexing_failed if hasattr(project, 'is_reindexing_failed') else False,
        failed_entities_count=project.failed_entities_count if hasattr(project, 'failed_entities_count') else 0,
        reindexed_failed_count=project.reindexed_failed_count if hasattr(project, 'reindexed_failed_count') else 0,
        reindexing_failed_status=project.reindexing_failed_status if hasattr(project, 'reindexing_failed_status') else None
    )


@router.patch("/{project_id}")
def update_project(
    project_id: int, 
    ui_language: str = Query(..., description="UI language (EN or RU)"),
    db: Session = Depends(get_db)
):
    """Update project UI language"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if ui_language not in ["EN", "RU"]:
        raise HTTPException(status_code=400, detail="ui_language must be EN or RU")
    
    project.ui_language = ui_language
    db.commit()
    db.refresh(project)
    
    return project


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """Delete project and all its data"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(project)
    db.commit()
    
    return None


@router.post("/{project_id}/delete-entities")
def delete_entities(
    project_id: int,
    file_id: Optional[int] = Query(None, description="Delete entities from specific file"),
    entity_ids: Optional[str] = Query(None, description="Comma-separated entity IDs to delete"),
    delete_all: bool = Query(False, description="Delete all entities from project"),
    db: Session = Depends(get_db)
):
    """Delete entities from index
    
    Args:
        project_id: Project ID (required)
        file_id: Optional file ID to delete entities from
        entity_ids: Optional comma-separated list of entity IDs
        delete_all: Delete all entities from project
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Parse entity_ids if provided
    entity_ids_list = None
    if entity_ids:
        try:
            entity_ids_list = [int(id.strip()) for id in entity_ids.split(',')]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid entity_ids format")
    
    # Validate that at least one deletion criteria is provided
    if not delete_all and not file_id and not entity_ids_list:
        raise HTTPException(
            status_code=400,
            detail="Must specify file_id, entity_ids, or delete_all=True"
        )
    
    # Start deletion in background
    result = celery_app.send_task(
        'delete_entities',
        kwargs={
            'project_id': project_id if delete_all else None,
            'file_id': file_id,
            'entity_ids': entity_ids_list,
            'delete_all': delete_all
        }
    )
    
    return {
        "message": "Deletion started",
        "project_id": project_id,
        "task_id": result.id
    }


@router.post("/{project_id}/indexing/stop")
def stop_indexing(project_id: int, db: Session = Depends(get_db)):
    """Stop indexing for a project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not project.is_indexing or not project.indexing_task_id:
        return {"message": "No active indexing task"}
    
    # Revoke the Celery task
    try:
        celery_app.control.revoke(project.indexing_task_id, terminate=True)
    except Exception as e:
        # Task might already be finished or not exist
        pass
    
    # Update project state
    project.is_indexing = False
    project.indexing_task_id = None
    db.commit()
    
    return {"message": "Indexing stopped"}


@router.post("/{project_id}/indexing/resume")
def resume_indexing(project_id: int, db: Session = Depends(get_db)):
    """Resume indexing for a project from where it stopped"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.is_indexing:
        raise HTTPException(status_code=400, detail="Indexing is already in progress")
    
    # Start indexing with resume=True
    task = celery_app.send_task('index_project', args=[project_id], kwargs={'resume': True})
    project.indexing_task_id = task.id
    project.is_indexing = True
    project.indexing_status = "Resuming indexing..."
    db.commit()
    
    return {"message": "Indexing resumed", "task_id": task.id}


@router.post("/{project_id}/indexing/start")
def start_indexing(project_id: int, db: Session = Depends(get_db)):
    """Start indexing for a project (for new projects or to restart from beginning)"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.is_indexing:
        raise HTTPException(status_code=400, detail="Indexing is already in progress")
    
    # Start indexing from beginning (resume=False)
    task = celery_app.send_task('index_project', args=[project_id], kwargs={'resume': False})
    project.indexing_task_id = task.id
    project.is_indexing = True
    project.last_indexed_file_path = None  # Reset resume point
    project.current_file_path = None
    project.indexing_status = "Starting indexing..."
    db.commit()
    
    return {"message": "Indexing started", "task_id": task.id}


@router.get("/{project_id}/indexing/status")
def get_indexing_status(project_id: int, db: Session = Depends(get_db)):
    """Get detailed indexing status including Celery task status"""
    try:
        from celery.result import AsyncResult
    except ImportError:
        AsyncResult = None
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    task_status = None
    task_info = None
    
    if project.indexing_task_id and AsyncResult:
        try:
            result = AsyncResult(project.indexing_task_id, app=celery_app)
            task_status = result.state  # PENDING, STARTED, SUCCESS, FAILURE, etc.
            if result.info:
                if isinstance(result.info, dict):
                    task_info = str(result.info.get('error', result.info))[:500]
                else:
                    task_info = str(result.info)[:500]
        except Exception as e:
            task_status = f"Error: {str(e)[:100]}"
    
    return {
        "project_id": project_id,
        "is_indexing": project.is_indexing,
        "current_file": project.current_file_path,
        "status_message": project.indexing_status,
        "task_id": project.indexing_task_id,
        "task_status": task_status,
        "task_info": task_info,
        "indexed_files": getattr(project, 'indexed_files', 0) or 0,
        "total_files": getattr(project, 'total_files', 0) or 0,
        "total_entities": getattr(project, 'total_entities', 0) or 0
    }


@router.get("/{project_id}/files")
def get_project_files(
    project_id: int,
    indexed_only: Optional[bool] = Query(None, description="Filter by indexed status"),
    limit: int = Query(1000, le=10000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get list of files in project with indexing status
    
    Args:
        project_id: Project ID
        indexed_only: If True, return only indexed files. If False, return only non-indexed files. If None, return all.
    """
    from pathlib import Path
    from datetime import datetime
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_path = Path(project.path)
    if not project_path.exists():
        return {
            "project_id": project_id,
            "total_files": 0,
            "indexed_files": 0,
            "not_indexed_files": 0,
            "files": []
        }
    
    # Get all files from filesystem
    extensions = ['.py'] if project.language == 'python' else ['.php']
    exclude_dirs = {'__pycache__', '.git', 'node_modules', 'vendor', 'tests', 'test', 'data', 'migrations'}
    
    all_files = []
    for ext in extensions:
        for file_path in project_path.rglob(f'*{ext}'):
            # Filter out excluded directories
            if not any(exclude in file_path.parts for exclude in exclude_dirs):
                all_files.append(str(file_path))
    
    # Get indexed files from database
    indexed_files_db = db.query(File).filter(File.project_id == project_id).all()
    indexed_paths = {f.path: f for f in indexed_files_db}
    
    # Build file list with status
    files_list = []
    for file_path in sorted(all_files):
        file_info = indexed_paths.get(file_path)
        is_indexed = file_info is not None
        
        # Apply filter
        if indexed_only is not None:
            if indexed_only and not is_indexed:
                continue
            if not indexed_only and is_indexed:
                continue
        
        # Count entities in file
        entity_count = 0
        if file_info:
            entity_count = db.query(func.count(Entity.id)).filter(Entity.file_id == file_info.id).scalar() or 0
        
        files_list.append({
            "path": file_path,
            "relative_path": str(Path(file_path).relative_to(project_path)),
            "is_indexed": is_indexed,
            "indexed_at": file_info.indexed_at.isoformat() if file_info and file_info.indexed_at else None,
            "entity_count": entity_count,
            "file_id": file_info.id if file_info else None,
            "last_modified": file_info.last_modified.isoformat() if file_info else None
        })
    
    # Apply pagination
    total = len(files_list)
    files_list = files_list[offset:offset + limit]
    
    indexed_count = sum(1 for f in files_list if f['is_indexed'])
    not_indexed_count = total - indexed_count
    
    return {
        "project_id": project_id,
        "total_files": total,
        "indexed_files": indexed_count,
        "not_indexed_files": not_indexed_count,
        "files": files_list,
        "limit": limit,
        "offset": offset
    }

