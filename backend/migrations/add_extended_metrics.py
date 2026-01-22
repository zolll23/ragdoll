"""
Migration script to add extended metrics fields to analysis table
Run: docker-compose exec -T backend python -m migrations.add_extended_metrics
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from sqlalchemy import text

def migrate():
    """Add extended metrics columns to analysis table"""
    db = SessionLocal()
    try:
        # Check if columns already exist
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='analysis' AND column_name='lines_of_code'
        """))
        
        if result.fetchone():
            print("Extended metrics columns already exist")
            return
        
        # Add all extended metrics columns
        columns = [
            ("lines_of_code", "INTEGER"),
            ("cyclomatic_complexity", "INTEGER"),
            ("cognitive_complexity", "INTEGER"),
            ("max_nesting_depth", "INTEGER"),
            ("parameter_count", "INTEGER"),
            ("coupling_score", "FLOAT"),
            ("cohesion_score", "FLOAT"),
            ("afferent_coupling", "INTEGER"),
            ("efferent_coupling", "INTEGER"),
            ("n_plus_one_queries", "JSON"),
            ("space_complexity", "VARCHAR(50)"),
            ("hot_path_detected", "BOOLEAN"),
            ("security_issues", "JSON"),
            ("hardcoded_secrets", "JSON"),
            ("insecure_dependencies", "JSON"),
            ("is_god_object", "BOOLEAN"),
            ("feature_envy_score", "FLOAT"),
            ("data_clumps", "JSON"),
            ("long_parameter_list", "BOOLEAN"),
        ]
        
        for col_name, col_type in columns:
            try:
                db.execute(text(f"""
                    ALTER TABLE analysis 
                    ADD COLUMN {col_name} {col_type}
                """))
                print(f"Added column: {col_name}")
            except Exception as e:
                print(f"Warning: Could not add {col_name}: {e}")
                # Continue with other columns
        
        # Also add complexity_explanation if it doesn't exist
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='analysis' AND column_name='complexity_explanation'
        """))
        
        if not result.fetchone():
            db.execute(text("""
                ALTER TABLE analysis 
                ADD COLUMN complexity_explanation TEXT
            """))
            print("Added column: complexity_explanation")
        
        # Set default values for numeric columns
        db.execute(text("""
            UPDATE analysis 
            SET 
                lines_of_code = 0,
                cyclomatic_complexity = 1,
                cognitive_complexity = 0,
                max_nesting_depth = 0,
                parameter_count = 0,
                coupling_score = 0.0,
                cohesion_score = 1.0,
                afferent_coupling = 0,
                efferent_coupling = 0,
                space_complexity = 'O(1)',
                hot_path_detected = false,
                is_god_object = false,
                feature_envy_score = 0.0,
                long_parameter_list = false
            WHERE lines_of_code IS NULL
        """))
        
        # Set default empty arrays for JSON columns
        db.execute(text("""
            UPDATE analysis 
            SET 
                n_plus_one_queries = '[]'::json,
                security_issues = '[]'::json,
                hardcoded_secrets = '[]'::json,
                insecure_dependencies = '[]'::json,
                data_clumps = '[]'::json
            WHERE n_plus_one_queries IS NULL
        """))
        
        db.commit()
        print("Successfully added extended metrics columns")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()

