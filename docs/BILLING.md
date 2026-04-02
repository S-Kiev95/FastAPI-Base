# Sistema de Billing

## Arquitectura

El sistema de billing usa una **abstracción de pasarela de pago** que permite intercambiar proveedores sin modificar la lógica de negocio.

```
Rutas (billing.py)
    ↓
BillingService (billing_service.py)
    ↓
PaymentGateway (interfaz abstracta)
    ↓
StripeGateway | MercadoPagoGateway | [FuturaGateway]
```

### Componentes principales

| Componente | Archivo | Responsabilidad |
|-----------|---------|-----------------|
| Modelo Subscription | `app/models/subscription.py` | Tabla BD, enums, schemas, definición de planes |
| Interfaz PaymentGateway | `app/services/billing/gateway.py` | Contrato abstracto (6 métodos) |
| Stubs Stripe/MP | `app/services/billing/stripe_gateway.py`, `mercadopago_gateway.py` | Implementaciones placeholder |
| Factory | `app/services/billing/__init__.py` | `get_gateway()` selecciona pasarela por config |
| Servicio | `app/services/billing/billing_service.py` | Orquesta pasarela + BD |
| Rutas | `app/routes/billing.py` | Endpoints HTTP |

---

## Relación con Organizations

Cada `Organization` tiene exactamente **una** `Subscription` (relación 1:1 via FK `organization_id` con `unique=True`).

- Al crear una org (registro), no se crea suscripción automáticamente.
- La primera vez que se consulta `/billing/subscription`, se crea una suscripción `free` por defecto.
- El campo `Organization.plan` existe por legado pero la fuente de verdad es `Subscription.plan`.

---

## Planes disponibles

| Plan | Precio/mes | Max miembros | Storage | Features principales |
|------|-----------|-------------|---------|---------------------|
| **free** | $0 | 3 | 100 MB | CRUD básico, soporte email |
| **starter** | $29 | 10 | 1 GB | + API access, branding |
| **pro** | $79 | 50 | 10 GB | + webhooks, soporte prioritario |
| **enterprise** | Personalizado | Ilimitado | Ilimitado | + SSO, audit log, soporte dedicado |

Los planes se definen en `PLAN_FEATURES` dentro de `app/models/subscription.py`. Para modificar precios o features, editar ese diccionario.

---

## Pasarelas de pago

### Interfaz abstracta (`PaymentGateway`)

Toda pasarela debe implementar estos 6 métodos:

```python
class PaymentGateway(ABC):
    async def create_customer(email, name, metadata) -> str          # customer_id
    async def create_subscription(customer_id, plan) -> dict          # {subscription_id, status}
    async def cancel_subscription(subscription_id) -> bool
    async def create_checkout_url(customer_id, plan, success_url, cancel_url) -> str
    async def handle_webhook(payload, signature) -> WebhookEvent
    async def get_subscription_status(subscription_id) -> dict
```

### Implementaciones actuales

- **StripeGateway** (`stripe_gateway.py`) — Stub, retorna datos simulados. Para producción: instalar `stripe` SDK y reemplazar stubs con llamadas reales.
- **MercadoPagoGateway** (`mercadopago_gateway.py`) — Stub. Para producción: usar API REST de MercadoPago con HMAC-SHA256 para webhooks.

### Agregar una nueva pasarela

1. Crear `app/services/billing/nueva_gateway.py` implementando `PaymentGateway`
2. Agregar valor al enum `PaymentGatewayType` en `app/models/subscription.py`
3. Agregar caso en `get_gateway()` en `app/services/billing/__init__.py`
4. Agregar settings en `app/config.py` (API keys, webhook secrets)

No se necesita modificar rutas, servicio ni modelos.

---

## Endpoints

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/billing/plans` | No | Lista todos los planes |
| GET | `/billing/plans/{id}` | No | Detalle de un plan |
| GET | `/billing/subscription` | Sí + Org | Suscripción de la org actual |
| POST | `/billing/checkout` | Sí + Org | Genera URL de checkout en la pasarela |
| POST | `/billing/change-plan` | Sí + Org | Cambia plan directamente (admin) |
| POST | `/billing/cancel` | Sí + Org | Cancela suscripción |
| GET | `/billing/payments` | Sí + Org | Historial de pagos (paginado) |
| GET | `/billing/payments/{id}` | Sí + Org | Detalle de un pago |
| GET | `/billing/usage` | Sí + Org | Uso actual vs límites del plan |
| POST | `/billing/webhooks/stripe` | No* | Recibe eventos de Stripe |
| POST | `/billing/webhooks/mercadopago` | No* | Recibe eventos de MercadoPago |

*Los webhooks no requieren JWT pero verifican firma de la pasarela.

### Ejemplo: Checkout

```bash
POST /billing/checkout
Authorization: Bearer <token>
Content-Type: application/json

{
    "plan": "pro",
    "gateway": "stripe"
}

# Respuesta:
{
    "checkout_url": "https://checkout.stripe.com/...",
    "subscription_id": "uuid"
}
```

---

## Configuración (variables de entorno)

```env
# Pasarela activa por defecto
ACTIVE_PAYMENT_GATEWAY=stripe    # "stripe" | "mercadopago"

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# MercadoPago
MERCADOPAGO_ACCESS_TOKEN=APP_USR-...
MERCADOPAGO_WEBHOOK_SECRET=...
```

---

## Flujo de webhook

```
Pasarela → POST /billing/webhooks/{gateway}
    → handle_webhook() verifica firma
    → Retorna WebhookEvent normalizado
    → BillingService actualiza Subscription según tipo de evento:
        - subscription.created/updated → status = active
        - subscription.cancelled → status = cancelled
        - payment.success → registra Payment succeeded + actualiza subscription
        - payment.failed → status = past_due + registra Payment failed
```

Los eventos se normalizan a un formato interno (`WebhookEvent`) independiente de la pasarela.

---

## Dashboard de billing (Fase 4.1)

### Modelo Payment

Tabla `payments` — historial de transacciones registrado automáticamente desde webhooks.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | UUID | PK |
| `organization_id` | UUID | FK → organizations |
| `subscription_id` | UUID | FK → subscriptions |
| `gateway` | str | "stripe" / "mercadopago" |
| `gateway_payment_id` | str | ID externo del pago |
| `amount` | int | Monto en centavos |
| `currency` | str | "usd", "ars", etc. |
| `status` | str | succeeded / failed / pending / refunded |
| `description` | str | Descripción del pago |
| `created_at` | datetime | Fecha de registro |

### Endpoint de uso (`GET /billing/usage`)

Retorna el uso actual de la organización vs los límites de su plan:

```json
{
    "plan": "starter",
    "status": "active",
    "members": {
        "current": 7,
        "max": 10,
        "percentage": 70.0,
        "unlimited": false
    },
    "storage": {
        "current_mb": 0,
        "max_mb": 1000,
        "percentage": 0,
        "unlimited": false
    },
    "features": ["basic_crud", "email_support", "api_access", "custom_branding"]
}
```

### Aislamiento de datos

Los pagos están filtrados por `organization_id`. Un pago de la Org A no es visible desde la Org B.

---

## Limitaciones actuales y extensiones futuras

### Lo que NO está implementado aún

1. **Cobro por usuario extra** — Los planes definen `max_members` pero no hay enforcement ni cobro por excedente. Para implementar cobros por usuario adicional (ej. $10/usuario extra):
   - Agregar `price_per_extra_member` a `PLAN_FEATURES`
   - Contar miembros activos en `Membership` vs `max_members` del plan
   - Al agregar miembro que exceda el límite: crear cobro adicional en la pasarela (Stripe: usage-based billing o line items)

2. **Enforcement de límites** — `max_members` y `max_storage_mb` son informativos, no se validan al crear memberships o subir archivos. Agregar guards en `MembershipService` y `StorageService`.

3. **Período de prueba (trial)** — El status `trialing` existe en el enum pero no hay lógica para activar/expirar trials.

4. **Storage tracking** — `GET /billing/usage` retorna `current_mb: 0` porque el modelo `Media` no tiene `organization_id` aún. Al agregar tenant isolation a media, calcular storage real.

5. **Llamadas reales a APIs** — Los gateways son stubs. Para producción necesitan SDKs reales (`stripe`, `httpx` para MercadoPago).

6. **Proration** — Al cambiar de plan mid-cycle, no hay cálculo de prorrateo. Stripe lo maneja automáticamente con su API.
