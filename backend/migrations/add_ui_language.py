"""
Migration script to add ui_language field to projects table
Run: docker-compose exec backend python -m migrations.add_ui_language
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from sqlalchemy import text

def migrate():
    """Add ui_language column to projects table"""
    db = SessionLocal()
    try:
        # Check if column exists
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='projects' AND column_name='ui_language'
        """))
        
        if result.fetchone():
            print("Column ui_language already exists")
            return
        
        # Add column
        db.execute(text("""
            ALTER TABLE projects 
            ADD COLUMN ui_language VARCHAR(10) NOT NULL DEFAULT 'EN'
        """))
        db.commit()
        print("Successfully added ui_language column")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
