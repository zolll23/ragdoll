"""
Migration script to add model column to llm_providers table
Run: docker-compose exec backend python -c "from migrations.add_model_to_providers import migrate; migrate()"
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from sqlalchemy import text

def migrate():
    """Add model column to llm_providers table"""
    db = SessionLocal()
    try:
        # Check if column exists
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='llm_providers' AND column_name='model'
        """))
        
        if result.fetchone():
            print("Column model already exists")
            return
        
        # Add column
        db.execute(text("""
            ALTER TABLE llm_providers 
            ADD COLUMN model VARCHAR(100)
        """))
        db.commit()
        print("Successfully added model column")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()

