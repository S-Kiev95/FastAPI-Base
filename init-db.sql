-- Script de inicialización para PostgreSQL
-- Se ejecuta automáticamente cuando se crea el contenedor por primera vez

-- Habilitar extensión pgvector para soporte de vectores
CREATE EXTENSION IF NOT EXISTS vector;

-- Habilitar extensión uuid-ossp para generar UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Log de extensiones habilitadas
SELECT 'pgvector extension enabled' AS status;
SELECT 'uuid-ossp extension enabled' AS status;
