"""
Migration script to add keywords field to analysis table
Run: docker-compose exec -T backend python -m migrations.add_keywords_field
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from sqlalchemy import text

def migrate():
    """Add keywords column to analysis table"""
    db = SessionLocal()
    try:
        # Check if column already exists
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='analysis' AND column_name='keywords'
        """))
        
        if result.fetchone():
            print("Keywords column already exists")
            return
        
        # Add keywords column
        db.execute(text("""
            ALTER TABLE analysis 
            ADD COLUMN keywords TEXT
        """))
        print("Added column: keywords")
        
        db.commit()
        print("Successfully added keywords column")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
