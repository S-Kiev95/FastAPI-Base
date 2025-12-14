"""
Script temporal para crear la tabla enum_definitions
"""
from app.database import engine
from app.models.enum_definition import EnumDefinition
from sqlmodel import SQLModel

# Create enum_definitions table
SQLModel.metadata.create_all(engine, tables=[EnumDefinition.__table__])
print("Tabla enum_definitions creada exitosamente!")
