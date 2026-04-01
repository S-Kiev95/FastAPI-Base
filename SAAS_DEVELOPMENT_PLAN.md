# Plan de Desarrollo SaaS — FastAPI-Base

> Documento de planificación para Claude Code.
> Base del proyecto: https://github.com/S-Kiev95/FastAPI-Base
> Stack: FastAPI + SQLModel + PostgreSQL + Redis + ARQ + WebSocket + S3/MinIO

---

## Contexto del proyecto

Este SaaS será **multi-tenant B2B**, con frontend en Svelte (servido como archivos estáticos desde FastAPI) y admin panel integrado al mismo servidor. La arquitectura base ya tiene `BaseService` con herencia genérica, sistema de filtros avanzados, WebSocket por canales, rate limiting con Redis, webhooks HMAC, logging estructurado JSON y cola de tareas ARQ.

---

## Fase 0 — Limpieza y preparación de la base

**Objetivo:** Dejar el proyecto en estado production-ready antes de agregar features.

### 0.1 Estructura de carpetas

Reorganizar la estructura para soportar multi-tenancy y nuevos módulos:

```
app/
├── core/                    # Configuración, seguridad, dependencias
│   ├── config.py
│   ├── security.py          # JWT, hashing, tokens
│   └── dependencies.py      # get_current_user, get_tenant, etc.
├── models/
│   ├── user.py
│   ├── organization.py      # NUEVO — tenant principal
│   ├── membership.py        # NUEVO — user ↔ org con rol
│   └── ...
├── services/
│   ├── base_service.py
│   ├── email/               # NUEVO
│   │   ├── service.py
│   │   └── templates/
│   ├── billing/             # NUEVO
│   │   ├── gateway.py       # Interfaz abstracta
│   │   ├── stripe.py
│   │   └── mercadopago.py
│   └── ...
├── routes/
│   └── ...
└── admin/                   # NUEVO — build de Svelte servido aquí
    └── (archivos estáticos del build)
```

### 0.2 Variables de entorno

Agregar al `.env.example`:

```env
# Multi-tenancy
DEFAULT_PLAN=free

# Email (Resend recomendado)
EMAIL_PROVIDER=resend          # resend | sendgrid | smtp
EMAIL_API_KEY=
EMAIL_FROM=noreply@tudominio.com
EMAIL_FROM_NAME=Tu SaaS

# Billing
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
MERCADOPAGO_ACCESS_TOKEN=
MERCADOPAGO_WEBHOOK_SECRET=
ACTIVE_PAYMENT_GATEWAY=mercadopago    # stripe | mercadopago

# Sentry (opcional para MVP)
SENTRY_DSN=

# Admin panel
ADMIN_BUILD_PATH=./app/admin
```

### 0.3 Tests existentes

Verificar que `test_auth.py`, `test_filters.py`, `test_rate_limit.py` y `test_websocket.py` pasan antes de cualquier cambio. Configurar pytest con fixtures de base de datos en memoria (SQLite) para tests.

---

## Fase 1 — Multi-tenancy

**Objetivo:** Aislar datos por organización. Cada tenant es una `Organization`. Los usuarios pertenecen a una o más organizaciones con un rol.

### 1.1 Modelos

**`app/models/organization.py`**

```python
class Organization(SQLModel, table=True):
    __tablename__ = "organizations"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    slug: str = Field(unique=True, index=True)
    plan: str = Field(default="free")          # free | starter | pro | enterprise
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**`app/models/membership.py`**

```python
class MembershipRole(str, Enum):
    owner = "owner"
    admin = "admin"
    member = "member"
    viewer = "viewer"

class Membership(SQLModel, table=True):
    __tablename__ = "memberships"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    organization_id: uuid.UUID = Field(foreign_key="organizations.id")
    role: MembershipRole = Field(default=MembershipRole.member)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### 1.2 Dependencia de tenant

Crear `app/core/dependencies.py`:

```python
async def get_current_organization(
    org_slug: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> Organization:
    """
    Verifica que el usuario tenga membresía activa en la org.
    Inyectar en cualquier ruta que opere sobre datos de un tenant.
    """
    ...

async def require_role(minimum_role: MembershipRole):
    """Decorator/dependencia para exigir un rol mínimo."""
    ...
```

### 1.3 Filtrado automático por tenant en BaseService

Agregar `tenant_id` como parámetro opcional en `get_all`, `filter` y `filter_paginated`:

```python
class BaseService(Generic[ModelT, CreateT, UpdateT, ReadT]):
    def get_all(
        self,
        session: Session,
        *,
        tenant_id: uuid.UUID | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[ReadT]:
        query = select(self.model)
        if tenant_id and hasattr(self.model, "organization_id"):
            query = query.where(self.model.organization_id == tenant_id)
        ...
```

### 1.4 Migración Alembic

Crear migración para `organizations` y `memberships`. Agregar `organization_id` como FK en los modelos que requieran aislamiento de datos.

---

## Fase 2 — Autenticación mejorada

**Objetivo:** Pasar de OAuth básico a un sistema completo con JWT propio, refresh tokens y RBAC.

### 2.1 JWT con refresh tokens

**`app/core/security.py`**

```python
def create_access_token(user_id: int, org_id: uuid.UUID, role: str) -> str:
    """Token de vida corta (15 min). Incluye org_id y role en claims."""
    ...

def create_refresh_token(user_id: int) -> str:
    """Token de vida larga (30 días). Almacenado en Redis para revocación."""
    ...

async def revoke_refresh_token(token: str, redis: Redis) -> None:
    """Invalida el token en Redis (logout, cambio de contraseña)."""
    ...
```

**Endpoints nuevos:**

```
POST /auth/refresh          → intercambia refresh token por nuevo access token
POST /auth/logout           → revoca refresh token
POST /auth/logout-all       → revoca todos los tokens del usuario
```

### 2.2 RBAC

Agregar decoradores/dependencias de permisos:

```python
# Uso en rutas:
@router.delete("/{item_id}")
async def delete_item(
    item_id: uuid.UUID,
    _: None = Depends(require_role(MembershipRole.admin))
):
    ...
```

Los roles jerárquicos son: `owner > admin > member > viewer`.

### 2.3 Invitaciones

```
POST /organizations/{slug}/invitations     → envía email de invitación
GET  /invitations/{token}/accept           → acepta invitación (crea Membership)
```

El token de invitación vive en Redis con TTL de 48h.

---

## Fase 3 — Emails transaccionales

**Objetivo:** Sistema de emails async con plantillas HTML versionadas en el proyecto.

### 3.1 Estructura de plantillas

```
app/services/email/
├── service.py              # EmailService principal
├── tasks.py                # Jobs ARQ para envío async
└── templates/
    ├── base.html           # Layout base con header/footer de la marca
    ├── welcome.html        # Bienvenida al registrarse
    ├── invitation.html     # Invitación a una organización
    ├── reset_password.html # Reset de contraseña
    ├── verify_email.html   # Verificación de email
    ├── invoice.html        # Factura / recibo de pago
    └── plan_change.html    # Cambio de plan (upgrade/downgrade)
```

Las plantillas usan **Jinja2** (ya en el ecosistema FastAPI). Variables en `{{ variable }}`.

### 3.2 EmailService

```python
class EmailService:
    def __init__(self, provider: str, api_key: str):
        self.provider = provider    # "resend" | "sendgrid" | "smtp"

    async def send(
        self,
        to: str,
        subject: str,
        template: str,
        context: dict,
        *,
        queue: bool = True          # True = envía por ARQ, False = envío directo
    ) -> None:
        html = self._render_template(template, context)
        if queue:
            await arq_queue.enqueue("send_email_task", to, subject, html)
        else:
            await self._send_now(to, subject, html)

    def _render_template(self, template_name: str, context: dict) -> str:
        """Renderiza Jinja2 desde la carpeta templates/."""
        ...
```

**Nota sobre plantillas en BD:** Para MVP, las plantillas viven en el repositorio. Si en el futuro un cliente necesita personalizar sus emails, agregar un modelo `EmailTemplate` con `organization_id` y `template_key`. El `EmailService` primero busca en BD para el tenant; si no hay, usa el archivo del proyecto como fallback.

### 3.3 ARQ task

```python
# app/services/email/tasks.py
async def send_email_task(ctx, to: str, subject: str, html: str) -> None:
    """Worker ARQ. Se reintenta automáticamente si falla."""
    await email_service._send_now(to, subject, html)
```

### 3.4 Proveedor recomendado

**Resend** (`pip install resend`) — API simple, buen deliverability, plan gratis generoso. Alternativa: SendGrid. Para desarrollo local usar SMTP con Mailpit o Mailtrap.

---

## Fase 4 — Billing dual (Stripe + MercadoPago)

**Objetivo:** Abstracción de pasarela de pago intercambiable por tenant o por configuración global.

### 4.1 Interfaz abstracta

```python
# app/services/billing/gateway.py
from abc import ABC, abstractmethod

class PaymentGateway(ABC):

    @abstractmethod
    async def create_customer(self, user: User, org: Organization) -> str:
        """Retorna customer_id en la pasarela."""
        ...

    @abstractmethod
    async def create_subscription(
        self, customer_id: str, plan: str
    ) -> dict:
        """Retorna subscription_id y status."""
        ...

    @abstractmethod
    async def cancel_subscription(self, subscription_id: str) -> bool:
        ...

    @abstractmethod
    async def handle_webhook(self, payload: bytes, signature: str) -> dict:
        """Verifica firma y retorna evento normalizado."""
        ...

    @abstractmethod
    async def create_payment_link(self, amount: int, currency: str, metadata: dict) -> str:
        """Para pagos one-time. Retorna URL de checkout."""
        ...
```

### 4.2 Implementaciones

**`app/services/billing/stripe.py`**

```python
class StripeGateway(PaymentGateway):
    def __init__(self, secret_key: str, webhook_secret: str):
        import stripe
        stripe.api_key = secret_key
        self.webhook_secret = webhook_secret

    async def handle_webhook(self, payload: bytes, signature: str) -> dict:
        event = stripe.Webhook.construct_event(payload, signature, self.webhook_secret)
        return self._normalize_event(event)

    def _normalize_event(self, event) -> dict:
        """Convierte eventos de Stripe a formato interno estandarizado."""
        type_map = {
            "customer.subscription.created": "subscription.created",
            "customer.subscription.deleted": "subscription.cancelled",
            "invoice.payment_succeeded": "payment.success",
            "invoice.payment_failed": "payment.failed",
        }
        return {
            "type": type_map.get(event["type"], event["type"]),
            "customer_id": event["data"]["object"].get("customer"),
            "raw": event,
        }
```

**`app/services/billing/mercadopago.py`**

```python
class MercadoPagoGateway(PaymentGateway):
    def __init__(self, access_token: str, webhook_secret: str):
        self.access_token = access_token
        self.webhook_secret = webhook_secret
        self.base_url = "https://api.mercadopago.com"

    async def create_payment_link(self, amount: int, currency: str, metadata: dict) -> str:
        """Crea una preferencia de pago y retorna la URL de checkout."""
        ...

    async def handle_webhook(self, payload: bytes, signature: str) -> dict:
        """MercadoPago usa HMAC-SHA256 en header x-signature."""
        ...
        return self._normalize_event(data)
```

### 4.3 Factory y rutas

```python
# app/services/billing/__init__.py
def get_gateway() -> PaymentGateway:
    provider = settings.ACTIVE_PAYMENT_GATEWAY
    if provider == "stripe":
        return StripeGateway(settings.STRIPE_SECRET_KEY, settings.STRIPE_WEBHOOK_SECRET)
    elif provider == "mercadopago":
        return MercadoPagoGateway(settings.MERCADOPAGO_ACCESS_TOKEN, settings.MERCADOPAGO_WEBHOOK_SECRET)
    raise ValueError(f"Gateway desconocido: {provider}")
```

**Endpoints de billing:**

```
POST /billing/checkout              → crea link de pago (ambas pasarelas)
POST /billing/webhooks/stripe       → recibe eventos de Stripe
POST /billing/webhooks/mercadopago  → recibe eventos de MercadoPago
GET  /billing/subscription          → estado actual de la suscripción
POST /billing/cancel                → cancela suscripción
```

### 4.4 Modelo de suscripción

```python
class Subscription(SQLModel, table=True):
    __tablename__ = "subscriptions"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    organization_id: uuid.UUID = Field(foreign_key="organizations.id", unique=True)
    gateway: str                        # "stripe" | "mercadopago"
    gateway_customer_id: str | None
    gateway_subscription_id: str | None
    plan: str                           # "free" | "starter" | "pro"
    status: str                         # "active" | "cancelled" | "past_due" | "trialing"
    current_period_end: datetime | None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## Fase 5 — Feature flags y límites por plan

**Objetivo:** Controlar qué funcionalidades están disponibles según el plan de la organización.

### 5.1 Configuración de planes

```python
# app/core/plans.py
PLANS = {
    "free": {
        "max_users": 3,
        "max_projects": 1,
        "websocket": False,
        "api_rate_limit": 100,        # requests/hora
        "storage_gb": 1,
    },
    "starter": {
        "max_users": 10,
        "max_projects": 5,
        "websocket": True,
        "api_rate_limit": 1000,
        "storage_gb": 10,
    },
    "pro": {
        "max_users": -1,              # ilimitado
        "max_projects": -1,
        "websocket": True,
        "api_rate_limit": 10000,
        "storage_gb": 100,
    },
}

def get_plan_limit(org: Organization, feature: str) -> int | bool:
    return PLANS.get(org.plan, PLANS["free"]).get(feature)
```

### 5.2 Dependencia de feature check

```python
async def require_feature(feature: str):
    """Inyectar en rutas que requieran un feature específico."""
    async def check(org: Organization = Depends(get_current_organization)):
        if not get_plan_limit(org, feature):
            raise HTTPException(
                status_code=402,
                detail=f"Tu plan no incluye '{feature}'. Actualizá tu suscripción."
            )
    return check
```

---

## Fase 6 — Admin panel (Svelte + FastAPI)

**Objetivo:** Servir el build de Svelte desde FastAPI con rutas protegidas para admins internos (no confundir con el admin de cada tenant).

### 6.1 Configuración en main.py

```python
from fastapi.staticfiles import StaticFiles

# Montar el build de Svelte
admin_build_path = settings.ADMIN_BUILD_PATH
if os.path.exists(admin_build_path):
    app.mount("/admin", StaticFiles(directory=admin_build_path, html=True), name="admin")
```

### 6.2 API exclusiva del admin

```
/api/admin/organizations        → CRUD de tenants
/api/admin/users                → gestión global de usuarios
/api/admin/subscriptions        → vista de todas las suscripciones
/api/admin/metrics              → métricas globales
/api/admin/impersonate/{user}   → login como cualquier usuario (debug)
```

Proteger con un rol especial `is_superadmin: bool` en el modelo `User`. No usar el mismo sistema de membresías de tenant para esto.

### 6.3 Build del Svelte

En el proyecto Svelte, configurar `adapter-static` con `base: '/admin'`. El build genera `admin/index.html` que maneja todas las rutas client-side. FastAPI sirve `index.html` para cualquier sub-ruta de `/admin/*`.

---

## Fase 7 — Observabilidad y métricas

**Objetivo:** Visibilidad en producción sin overhead excesivo para MVP.

### 7.1 Sentry (errores)

```python
# main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.1,         # 10% de requests trazados
        environment=settings.ENVIRONMENT,
    )
```

### 7.2 Métricas con Prometheus (opcional post-MVP)

```python
# pip install prometheus-fastapi-instrumentator
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

Luego conectar Grafana a `/metrics`. Para el MVP, el logging estructurado JSON existente es suficiente si se centraliza en Loki o Datadog.

### 7.3 Health checks extendidos

Extender el `/health` existente:

```python
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": settings.API_VERSION,
        "database": await check_db(),
        "redis": await check_redis(),
        "timestamp": datetime.utcnow().isoformat(),
    }
```

---

## Fase 8 — CI/CD y preparación para producción

### 8.1 Tests

Agregar `pytest` con fixtures de BD:

```
tests/
├── conftest.py             # fixtures: test_session, test_client, test_user, test_org
├── test_auth.py            # (ya existe, migrar al nuevo sistema)
├── test_tenancy.py         # aislamiento de datos entre orgs
├── test_billing.py         # webhooks, cambios de plan
├── test_email.py           # mock de envío, verificar templates
└── test_filters.py         # (ya existe)
```

### 8.2 GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
      redis:
        image: redis:7
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync
      - run: uv run pytest tests/ -v --tb=short
```

### 8.3 Docker Compose producción

El `docker-compose.yml` existente está bien como base. Agregar:

- Servicio `worker` para ARQ (misma imagen, distinto comando)
- Configuración de health checks en cada servicio
- Variables de entorno desde `.env` (no hardcodeadas)

```yaml
worker:
  build: .
  command: python -m arq app.workers.main.WorkerSettings
  env_file: .env
  depends_on:
    - redis
    - postgres
```

---

## Orden de implementación recomendado

| Prioridad | Fase | Tiempo estimado | Desbloqueante para |
|-----------|------|-----------------|-------------------|
| 1 | Fase 0 — Limpieza | 1-2 días | Todo |
| 2 | Fase 1 — Multi-tenancy | 3-4 días | Billing, Feature flags |
| 3 | Fase 2 — Auth mejorada | 2-3 días | Invitaciones, Admin |
| 4 | Fase 3 — Emails | 2-3 días | Invitaciones, Billing |
| 5 | Fase 4 — Billing | 3-5 días | Feature flags |
| 6 | Fase 5 — Feature flags | 1-2 días | — |
| 7 | Fase 6 — Admin panel | Variable (depende de Svelte) | — |
| 8 | Fase 7 — Observabilidad | 1 día | Producción |
| 9 | Fase 8 — CI/CD | 1-2 días | Producción |

---

## Dependencias Python a agregar

```toml
# pyproject.toml — agregar a [dependencies]
resend = ">=2.0"              # Email (alternativa: sendgrid)
jinja2 = ">=3.1"              # Templates de email
python-multipart = ">=0.0.9"  # Form data (si no está)
pyjwt = ">=2.8"               # JWT propio (si no está)
sentry-sdk = {version=">=2.0", extras=["fastapi"]}
stripe = ">=9.0"              # Billing Stripe
mercadopago = ">=2.3"         # Billing MercadoPago
```

---

## Notas para Claude Code

- Al implementar cualquier `BaseService`, recordar agregar el filtro `organization_id` si el modelo tiene esa FK — es el mecanismo central de aislamiento de datos.
- Los webhooks de billing deben verificar la firma **antes** de procesar cualquier dato del payload. Nunca confiar en el payload sin verificar.
- Las plantillas de email deben tener versión mobile-friendly. Usar tablas HTML para compatibilidad con clientes de correo. Herramienta de referencia: [mjml.io](https://mjml.io).
- El campo `slug` de Organization debe normalizarse al crear (lowercase, sin espacios, solo alfanumérico y guiones). Indexar para búsquedas rápidas.
- Mantener todos los IDs de recursos de tenant como `uuid.UUID`, no como `int`, para evitar enumeración.
- Los endpoints de webhook de billing deben estar **excluidos** del rate limiting global (las pasarelas pueden enviar múltiples eventos en ráfaga).
