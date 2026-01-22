"""
Migration script to add tokens_used field to projects table
Run: docker-compose exec -T backend python -m migrations.add_tokens_used
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from sqlalchemy import text

def migrate():
    """Add tokens_used column to projects table"""
    db = SessionLocal()
    try:
        # Check if column exists
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='projects' AND column_name='tokens_used'
        """))
        
        if result.fetchone():
            print("Column tokens_used already exists")
            return
        
        # Add column
        db.execute(text("""
            ALTER TABLE projects 
            ADD COLUMN tokens_used INTEGER NOT NULL DEFAULT 0
        """))
        db.commit()
        print("Successfully added tokens_used column")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()

