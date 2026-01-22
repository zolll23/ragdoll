"""
Migration script to change full_qualified_name from VARCHAR(512) to TEXT
Run: docker-compose exec backend python -c "from migrations.fix_full_qualified_name import migrate; migrate()"
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from sqlalchemy import text

def migrate():
    """Change full_qualified_name column type to TEXT"""
    db = SessionLocal()
    try:
        # Check current type
        result = db.execute(text("""
            SELECT data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'entities' AND column_name = 'full_qualified_name'
        """))
        row = result.fetchone()
        if row:
            current_type = row[0]
            max_length = row[1]
            print(f"Current type: {current_type}({max_length})")
            
            if current_type == 'character varying' and max_length == 512:
                # Change to TEXT
                db.execute(text("""
                    ALTER TABLE entities 
                    ALTER COLUMN full_qualified_name TYPE TEXT
                """))
                db.commit()
                print("Successfully changed full_qualified_name to TEXT")
            else:
                print(f"Column already has type {current_type}, no change needed")
        else:
            print("Column not found")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()

