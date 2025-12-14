"""
Script temporal para agregar la columna enum_id a field_definitions
"""
from app.database import engine
from sqlalchemy import text

# Add enum_id column to field_definitions
with engine.connect() as conn:
    try:
        conn.execute(text("""
            ALTER TABLE field_definitions
            ADD COLUMN enum_id INTEGER
            REFERENCES enum_definitions(id)
        """))
        conn.commit()
        print("Columna enum_id agregada exitosamente!")
    except Exception as e:
        print(f"Error o la columna ya existe: {e}")
