"""
Migration script to create llm_providers table
Run: docker-compose exec backend python -c "from migrations.create_llm_providers import migrate; migrate()"
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, engine
from sqlalchemy import text

def migrate():
    """Create llm_providers table"""
    db = SessionLocal()
    try:
        # Check if table exists
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'llm_providers'
            )
        """))
        
        if result.scalar():
            print("Table llm_providers already exists")
            return
        
        # Create table
        db.execute(text("""
            CREATE TABLE llm_providers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) NOT NULL UNIQUE,
                display_name VARCHAR(100) NOT NULL,
                base_url VARCHAR(255),
                api_key VARCHAR(512),
                is_active BOOLEAN DEFAULT TRUE,
                is_default BOOLEAN DEFAULT FALSE,
                config JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.commit()
        print("Successfully created llm_providers table")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()

