"""
Migration script to add indexing state fields to projects table
Run: docker-compose exec backend python -m migrations.add_indexing_state
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from sqlalchemy import text

def migrate():
    """Add indexing state columns to projects table"""
    db = SessionLocal()
    try:
        # Check if columns exist
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='projects' AND column_name='is_indexing'
        """))
        
        if result.fetchone():
            print("Columns already exist")
            return
        
        # Add columns
        db.execute(text("""
            ALTER TABLE projects 
            ADD COLUMN is_indexing BOOLEAN NOT NULL DEFAULT false,
            ADD COLUMN indexing_task_id VARCHAR(255),
            ADD COLUMN last_indexed_file_path VARCHAR(512)
        """))
        db.commit()
        print("Successfully added indexing state columns")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
