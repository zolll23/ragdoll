"""
Migration script to add progress fields to projects table
Run: docker-compose exec -T backend python -m migrations.add_progress_fields
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from sqlalchemy import text

def migrate():
    """Add progress columns to projects table"""
    db = SessionLocal()
    try:
        # Check if columns exist
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='projects' AND column_name='total_files'
        """))
        
        if result.fetchone():
            print("Columns already exist")
            return
        
        # Add columns
        db.execute(text("""
            ALTER TABLE projects 
            ADD COLUMN total_files INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN indexed_files INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN total_entities INTEGER NOT NULL DEFAULT 0
        """))
        db.commit()
        print("Successfully added progress columns")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()

