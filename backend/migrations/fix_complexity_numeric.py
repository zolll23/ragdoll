"""
Migration script to fix complexity_numeric values
Run: docker-compose exec backend python -c "from migrations.fix_complexity_numeric import migrate; migrate()"
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.database import Analysis
from sqlalchemy import text

def migrate():
    """Fix complexity_numeric values based on complexity string"""
    db = SessionLocal()
    try:
        # Map complexity strings to numeric values
        complexity_map = {
            "O(1)": 1,
            "O(log n)": 2,
            "O(n)": 3,
            "O(n log n)": 4,
            "O(n^2)": 5,
            "O(n^3)": 6,
            "O(2^n)": 7,
            "O(n!)": 8,
        }
        
        # Also handle enum string format
        enum_to_value = {
            "ComplexityClass.CONSTANT": 1,
            "ComplexityClass.LOGARITHMIC": 2,
            "ComplexityClass.LINEAR": 3,
            "ComplexityClass.LINEARITHMIC": 4,
            "ComplexityClass.QUADRATIC": 5,
            "ComplexityClass.CUBIC": 6,
            "ComplexityClass.EXPONENTIAL": 7,
            "ComplexityClass.FACTORIAL": 8,
        }
        
        # Get all analyses
        analyses = db.query(Analysis).all()
        updated = 0
        
        for analysis in analyses:
            complexity_str = analysis.complexity
            
            # Try direct mapping first
            if complexity_str in complexity_map:
                correct_numeric = complexity_map[complexity_str]
            elif complexity_str in enum_to_value:
                correct_numeric = enum_to_value[complexity_str]
            else:
                # Try to extract from enum format
                if "CONSTANT" in complexity_str:
                    correct_numeric = 1
                elif "LOGARITHMIC" in complexity_str:
                    correct_numeric = 2
                elif "LINEARITHMIC" in complexity_str:
                    correct_numeric = 4
                elif "LINEAR" in complexity_str:
                    correct_numeric = 3
                elif "QUADRATIC" in complexity_str:
                    correct_numeric = 5
                elif "CUBIC" in complexity_str:
                    correct_numeric = 6
                elif "EXPONENTIAL" in complexity_str:
                    correct_numeric = 7
                elif "FACTORIAL" in complexity_str:
                    correct_numeric = 8
                else:
                    continue  # Skip if can't determine
            
            # Update if different
            if analysis.complexity_numeric != correct_numeric:
                analysis.complexity_numeric = correct_numeric
                updated += 1
        
        db.commit()
        print(f"Updated {updated} analyses with correct complexity_numeric values")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()

