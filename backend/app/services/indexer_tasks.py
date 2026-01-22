"""Celery tasks for indexing"""
from typing import Optional, List
from app.core.celery_app import celery_app
from app.services.indexer import IndexingService

# Don't cache indexer globally - create new instance each time
# This ensures analyzer uses latest provider from DB
def get_indexer():
    """Get IndexingService instance (always create new to get latest provider)"""
    return IndexingService()


@celery_app.task(name='index_project')
def index_project_task(project_id: int, resume: bool = False):
    """Task to index entire project
    
    Args:
        project_id: Project ID
        resume: If True, resume from last_indexed_file_path
    """
    indexer = get_indexer()
    indexer.index_project(project_id, resume=resume)


@celery_app.task(name='index_file')
def index_file_task(file_id: int):
    """Task to index single file"""
    indexer = get_indexer()
    indexer.index_file(file_id)


@celery_app.task(name='reindex_changed_files')
def reindex_changed_files_task(project_id: int, only_failed: bool = False):
    """Task to reindex project
    
    Args:
        project_id: Project ID
        only_failed: If True, only reindex entities with failed analysis
    """
    indexer = get_indexer()
    indexer.reindex_project(project_id, only_failed=only_failed)


@celery_app.task(name='delete_entities')
def delete_entities_task(
    project_id: Optional[int] = None,
    file_id: Optional[int] = None,
    entity_ids: Optional[List[int]] = None,
    delete_all: bool = False
):
    """Task to delete entities from index"""
    indexer = get_indexer()
    return indexer.delete_entities(
        project_id=project_id,
        file_id=file_id,
        entity_ids=entity_ids,
        delete_all=delete_all
    )

