# Plan de Implementación: Dominio de Seguros

## Contexto

Seguros-BK tiene toda la infraestructura SaaS resuelta (auth JWT, RBAC, multi-tenancy por Organization, billing, WebSocket, storage, audit, GDPR, rate limiting, etc.) pero sin dominio de negocio. Este plan implementa el dominio de seguros basado en el esquema de `db.md` + diagrama, y agrega un frontend Svelte demo servido por FastAPI.

## Decisiones de diseño

- **PKs**: `int` auto-increment (compatible con BaseService existente)
- **`organization_id`**: `uuid.UUID` FK a `organizations.id` (BaseService filtra automáticamente)
- **Nombres**: clases en inglés (`Client`, `Policy`), tablas en español (`cliente`, `poliza`), endpoints en español (`/clientes`, `/polizas`)
- **Frontend**: nueva app SvelteKit `portal-ui/` servida en `/app` (separada de `admin-ui/` en `/admin`)
- **Rutas**: bajo `/api/orgs/{org_slug}/seguros/...` usando `TenantContext` de `app/core/tenant.py`

---

## Fase 1 — Modelos de dominio + Migración

### Crear paquete `app/models/seguros/`

11 archivos de modelos (cada uno con tabla + schemas Create/Read/Update):

| Archivo | Clase | Tabla | Campos clave |
|---|---|---|---|
| `client.py` | `Client` | `cliente` | nombre, apellido, documento_identidad, telefono, email, direccion, fecha_nacimiento |
| `vehicle.py` | `Vehicle` | `vehiculo` | marca, modelo, anio, matricula, tipo (enum), color, numero_motor, numero_chasis |
| `insurer.py` | `Insurer` | `aseguradora` | nombre, telefono, email, direccion, contactos (JSON). Unique(org, nombre) |
| `policy.py` | `Policy` | `poliza` | numero_poliza, tipo_seguro (enum), vigente_desde/hasta, prima_total, moneda, total_cuotas, estado (enum) |
| `installment.py` | `Installment` | `cuota` | numero_cuota, monto, fecha_vencimiento, fecha_pago, pagada, metodo_pago |
| `claim.py` | `Claim` | `siniestro` | numero_siniestro, fecha_ocurrencia, fecha_denuncia, tipo_dano (enum), estado (enum), montos |
| `claim_document.py` | `ClaimDocument` | `siniestro_documento` | tipo_documento, recibido, fecha_recepcion, archivo_url |
| `workshop.py` | `Workshop` | `taller` | nombre, direccion, departamento, ciudad, telefono, especialidad (enum), marcas_atendidas |
| `insurer_workshop.py` | `InsurerWorkshop` | `aseguradora_taller` | zona, prioridad, vigente_desde/hasta (M2M) |
| `insurance_task.py` | `InsuranceTask` | `tarea` | titulo, descripcion, prioridad (enum), estado (enum), fecha_vencimiento |
| `message.py` | `Message` | `mensaje` | asunto, contenido, leido, fecha_leido |

Registrar modelos en: `app/models/__init__.py`, `app/database/connection.py`, `alembic/env.py`.
Correr migración: `alembic revision --autogenerate` + `alembic upgrade head`.

---

## Fase 2 — Services

### Crear paquete `app/services/seguros/`

11 services heredando `BaseService` + 1 dashboard service:

| Service | Métodos custom |
|---|---|
| `client_service` | búsqueda por nombre/apellido/documento |
| `vehicle_service` | `get_by_client()` |
| `policy_service` | `get_expiring_soon()`, `get_by_client()`, `renew_policy()` |
| `installment_service` | `get_by_policy()`, `get_overdue()`, `mark_paid()`, `generate_installments()` |
| `claim_service` | `get_by_policy()`, `get_by_status()` |
| `claim_document_service` | `get_by_claim()`, `mark_received()` |
| `workshop_service` | `get_by_departamento()`, `get_by_insurer()` |
| `insurance_task_service` | `get_assigned_to()`, `get_overdue()`, `complete_task()` |
| `message_service` | `get_inbox()`, `get_sent()`, `mark_read()`, `get_unread_count()` |
| `dashboard_service` | KPIs: clientes, pólizas activas, siniestros abiertos, cuotas vencidas, próximos vencimientos |

Agregar 11 WebSocket channels en `app/services/websocket/channels.py`.

---

## Fase 3 — Routes

### Crear paquete `app/routes/seguros/`

Router padre: `/api/orgs/{org_slug}/seguros`

| Archivo | Prefix | Endpoints clave |
|---|---|---|
| `clients.py` | `/clientes` | CRUD + `/{id}/vehiculos` + `/{id}/polizas` + búsqueda |
| `vehicles.py` | `/vehiculos` | CRUD |
| `insurers.py` | `/aseguradoras` | CRUD + `/{id}/talleres` + vincular/desvincular |
| `policies.py` | `/polizas` | CRUD + `/renovar` + `/por-vencer` + `/{id}/cuotas` + `/{id}/siniestros` |
| `installments.py` | `/cuotas` | Lista + `/vencidas` + `/{id}/pagar` |
| `claims.py` | `/siniestros` | CRUD + `/{id}/documentos` |
| `workshops.py` | `/talleres` | CRUD (filtro por departamento/especialidad) |
| `insurance_tasks.py` | `/tareas` | CRUD + `/completar` + `/mis-tareas` + `/vencidas` |
| `messages.py` | `/mensajes` | inbox + enviados + enviar + no-leidos |
| `dashboard.py` | `/dashboard` | KPIs + próximos vencimientos |

Registrar `seguros_router` en `main.py`.

---

## Fase 4 — Frontend Svelte (Portal de Seguros)

### Crear `portal-ui/` (SvelteKit app)

Build a `../app/portal`, base path `/app`, adapter-static.

**Páginas**:
- Dashboard (KPIs + alertas de vencimientos)
- Clientes (lista, detalle con tabs, crear)
- Pólizas (lista con filtros, detalle con cuotas/siniestros, wizard de creación)
- Cuotas (reporte de vencidas)
- Siniestros (lista, detalle con checklist documentos, crear)
- Aseguradoras (lista, detalle con contactos y talleres)
- Talleres (directorio filtrable)
- Tareas (lista con filtros)
- Mensajes (bandeja de entrada)

**Componentes reutilizables**: PortalLayout, Sidebar, DataTable, Modal, StatusBadge, KpiCard.

Montar portal SPA en `main.py` bajo `/app`.

---

## Fase 5 — Tests y Commit

- Test E2E: flujo completo cliente → vehículo → póliza → cuotas → siniestro → documentos
- Verificar aislamiento multi-tenant
- Verificar dashboard stats
- Build portal-ui + commit + push a rama `seguros`

---

## Resumen de archivos

| Categoría | Cantidad |
|---|---|
| Modelos (`app/models/seguros/`) | 12 archivos |
| Services (`app/services/seguros/`) | 13 archivos |
| Routes (`app/routes/seguros/`) | 11 archivos |
| Frontend (`portal-ui/`) | ~20 archivos |
| Tests | 1 archivo |
| **Total** | **~57 archivos nuevos + 5 modificados** |
