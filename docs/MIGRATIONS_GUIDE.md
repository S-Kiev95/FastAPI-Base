# Database Migrations Guide (Alembic)

## Overview

Este proyecto usa **Alembic** para gestionar migraciones de base de datos. Alembic permite:

- Crear migraciones automáticamente detectando cambios en modelos
- Aplicar/revertir migraciones de forma controlada
- Mantener historial de cambios de esquema
- Trabajar con PostgreSQL, MySQL, SQLite y otros

## Configuración

### Variables de Entorno

Para PostgreSQL (recomendado en producción):

```env
DATABASE_URL=postgresql://user:password@localhost:5432/mydb
```

Para desarrollo local (SQLite):

```env
DATABASE_URL=sqlite:///./app.db
```

### Dependencias Instaladas

- `alembic`: Sistema de migraciones
- `psycopg2-binary`: Driver de PostgreSQL

## Comandos Básicos

### 1. Crear una Nueva Migración

Después de crear o modificar modelos SQLModel:

```bash
# Generar migración automáticamente
uv run alembic revision --autogenerate -m "Descripción del cambio"

# Ejemplo:
uv run alembic revision --autogenerate -m "Add posts table"
uv run alembic revision --autogenerate -m "Add email_verified field to users"
```

Alembic detectará automáticamente:
- Nuevas tablas
- Columnas agregadas/eliminadas
- Cambios de tipo de datos
- Índices y constraints

### 2. Ver Migraciones Pendientes

```bash
uv run alembic current
uv run alembic history
```

### 3. Aplicar Migraciones

```bash
# Aplicar todas las migraciones pendientes
uv run alembic upgrade head

# Aplicar una migración específica
uv run alembic upgrade <revision_id>

# Aplicar siguiente migración
uv run alembic upgrade +1
```

### 4. Revertir Migraciones

```bash
# Revertir última migración
uv run alembic downgrade -1

# Revertir a una revisión específica
uv run alembic downgrade <revision_id>

# Revertir todas las migraciones
uv run alembic downgrade base
```

### 5. Ver Estado Actual

```bash
# Ver revisión actual
uv run alembic current

# Ver historial completo
uv run alembic history --verbose

# Ver SQL que se ejecutará (sin aplicar)
uv run alembic upgrade head --sql
```

## Workflow Completo

### Agregar un Nuevo Modelo

**1. Crear el modelo:**

```python
# app/models/post.py
from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime

class Post(SQLModel, table=True):
    __tablename__ = "posts"
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    content: str
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**2. Importar en alembic/env.py:**

```python
# alembic/env.py
from app.models.user import User  # noqa: F401
from app.models.media import Media  # noqa: F401
from app.models.post import Post  # noqa: F401  # AGREGAR ESTO
```

**3. Importar en app/database/connection.py:**

```python
# app/database/connection.py
def init_db():
    from app.models import User  # noqa: F401
    from app.models.media import Media  # noqa: F401
    from app.models.post import Post  # noqa: F401  # AGREGAR ESTO

    SQLModel.metadata.create_all(engine)
```

**4. Generar migración:**

```bash
uv run alembic revision --autogenerate -m "Add posts table"
```

**5. Revisar el archivo generado:**

Alembic creará un archivo en `alembic/versions/`. **Siempre revísalo** para asegurar que:
- Los cambios detectados son correctos
- No hay operaciones peligrosas (DROP TABLE, DROP COLUMN)
- Los valores por defecto son apropiados

**6. Aplicar la migración:**

```bash
uv run alembic upgrade head
```

### Modificar un Modelo Existente

**1. Modificar el modelo:**

```python
# app/models/user.py
class User(SQLModel, table=True):
    # ... campos existentes ...
    email_verified: bool = Field(default=False)  # NUEVO CAMPO
```

**2. Generar migración:**

```bash
uv run alembic revision --autogenerate -m "Add email_verified to users"
```

**3. Revisar y aplicar:**

```bash
# Revisar archivo generado
cat alembic/versions/<revision_id>_add_email_verified_to_users.py

# Aplicar
uv run alembic upgrade head
```

## Ejemplos de Migraciones

### Agregar Columna

```python
# Generado automáticamente
def upgrade():
    op.add_column('users', sa.Column('phone', sa.String(), nullable=True))
    op.create_index(op.f('ix_users_phone'), 'users', ['phone'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_users_phone'), table_name='users')
    op.drop_column('users', 'phone')
```

### Crear Nueva Tabla

```python
def upgrade():
    op.create_table('posts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('content', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_posts_title'), 'posts', ['title'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_posts_title'), table_name='posts')
    op.drop_table('posts')
```

### Agregar Relación (Foreign Key)

```python
def upgrade():
    op.add_column('posts', sa.Column('category_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_posts_category', 'posts', 'categories', ['category_id'], ['id'])

def downgrade():
    op.drop_constraint('fk_posts_category', 'posts', type_='foreignkey')
    op.drop_column('posts', 'category_id')
```

## Migraciones Manuales

A veces necesitas crear migraciones manualmente (datos, operaciones complejas):

```bash
# Crear migración vacía
uv run alembic revision -m "Seed initial data"
```

Editar el archivo generado:

```python
def upgrade():
    # Insertar datos iniciales
    op.execute("""
        INSERT INTO categories (name, description) VALUES
        ('Technology', 'Tech related posts'),
        ('Science', 'Science articles')
    """)

def downgrade():
    # Revertir datos
    op.execute("DELETE FROM categories WHERE name IN ('Technology', 'Science')")
```

## Buenas Prácticas

### 1. Siempre Revisa las Migraciones Generadas

```bash
# Después de generar
cat alembic/versions/<latest_revision>.py
```

Verifica:
- ✅ Cambios detectados correctamente
- ✅ No hay DROP TABLE accidentales
- ✅ Foreign keys están bien definidas
- ✅ Índices necesarios están presentes

### 2. Prueba en Desarrollo Primero

```bash
# Aplicar migración
uv run alembic upgrade head

# Si algo sale mal, revertir
uv run alembic downgrade -1

# Borrar y regenerar si es necesario
rm alembic/versions/<revision_id>_*.py
uv run alembic revision --autogenerate -m "Mensaje corregido"
```

### 3. Usa Mensajes Descriptivos

```bash
# ❌ Malo
uv run alembic revision --autogenerate -m "changes"

# ✅ Bueno
uv run alembic revision --autogenerate -m "Add email verification fields to users"
```

### 4. Una Migración, Un Cambio Lógico

No mezcles cambios no relacionados:

```bash
# ✅ Bueno - migraciones separadas
uv run alembic revision --autogenerate -m "Add posts table"
uv run alembic revision --autogenerate -m "Add comments table"

# ❌ Malo - cambios mezclados
uv run alembic revision --autogenerate -m "Add posts and comments and fix users"
```

### 5. Backup Antes de Migraciones en Producción

```bash
# PostgreSQL
pg_dump -U user -d dbname > backup_$(date +%Y%m%d_%H%M%S).sql

# Luego aplicar migración
uv run alembic upgrade head
```

### 6. No Edites Migraciones Aplicadas

Si una migración ya fue aplicada (`alembic upgrade`):
- ❌ No la edites
- ✅ Crea una nueva migración con el cambio

## Trabajo en Equipo

### Conflictos de Migraciones

Cuando dos personas crean migraciones en paralelo:

```bash
# Ver ramas de migración
uv run alembic branches

# Fusionar ramas
uv run alembic merge -m "Merge migrations" <rev1> <rev2>
```

### Sincronizar con el Equipo

```bash
# 1. Pull cambios de git
git pull

# 2. Ver nuevas migraciones
uv run alembic history

# 3. Aplicar migraciones del equipo
uv run alembic upgrade head
```

## Integración con CI/CD

### GitHub Actions Example

```yaml
name: Run Migrations

on:
  push:
    branches: [ main ]

jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install uv
          uv sync

      - name: Run migrations
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: uv run alembic upgrade head
```

## Troubleshooting

### Error: "Can't locate revision identified by..."

La base de datos y el código están desincronizados:

```bash
# Ver estado actual
uv run alembic current

# Ver todas las revisiones
uv run alembic history

# Si la BD está vacía, aplicar desde cero
uv run alembic upgrade head
```

### Error: "Target database is not up to date"

```bash
# Ver qué migraciones faltan
uv run alembic current
uv run alembic history

# Aplicar migraciones pendientes
uv run alembic upgrade head
```

### Resetear Base de Datos (Desarrollo)

```bash
# 1. Eliminar archivo SQLite
rm app.db

# 2. Recrear con migraciones
uv run alembic upgrade head

# O alternativamente (PostgreSQL):
# dropdb mydb
# createdb mydb
# uv run alembic upgrade head
```

### Ver SQL Sin Ejecutar

```bash
# Ver SQL que se ejecutará
uv run alembic upgrade head --sql > migration.sql

# Revisar antes de aplicar
cat migration.sql
```

## PostgreSQL vs SQLite

### SQLite (Desarrollo)

```env
DATABASE_URL=sqlite:///./app.db
```

**Limitaciones:**
- No soporta ALTER TABLE completo
- No soporta DROP COLUMN (versiones antiguas)
- No soporta múltiples ALTER en una transacción

**Solución:** Alembic usa "batch mode" automáticamente para SQLite.

### PostgreSQL (Producción)

```env
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

**Ventajas:**
- Transacciones completas
- Mejor performance con grandes datasets
- Soporte completo de ALTER TABLE
- Tipos de datos avanzados

## Comandos de Referencia Rápida

```bash
# Crear migración
uv run alembic revision --autogenerate -m "mensaje"

# Aplicar migraciones
uv run alembic upgrade head

# Revertir última
uv run alembic downgrade -1

# Ver estado
uv run alembic current
uv run alembic history

# Ver SQL sin ejecutar
uv run alembic upgrade head --sql

# Crear migración manual
uv run alembic revision -m "manual change"

# Fusionar ramas
uv run alembic merge -m "merge" <rev1> <rev2>
```

## Recursos Adicionales

- [Documentación Oficial de Alembic](https://alembic.sqlalchemy.org/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## Resumen

1. **Crear modelo** → Importar en `alembic/env.py` y `connection.py`
2. **Generar migración** → `alembic revision --autogenerate -m "mensaje"`
3. **Revisar archivo** → Verificar cambios detectados
4. **Aplicar** → `alembic upgrade head`
5. **Commit** → Subir código + archivo de migración a git

¡Siempre prueba en desarrollo antes de aplicar en producción!
