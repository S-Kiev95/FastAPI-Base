# ChatStudio — Decisiones de Arquitectura

Este documento fija las decisiones fundamentales del proyecto. Cualquier cambio a estas decisiones debe hacerse conscientemente y documentarse como una nueva entrada al final.

---

## ADR-001 — Modelo de despliegue: single-tenant por VPS

**Decisión**: cada cliente recibe su propia instancia aislada de ChatStudio, desplegada en un VPS dedicado (Contabo ~$5/mes, 8GB RAM).

**Contexto**: evaluamos tres modelos — multi-tenant compartido con un solo Chatwoot, multi-instancia Chatwoot sobre un único backend multi-tenant, y single-tenant self-hosted por cliente.

**Razones**:
- Chatwoot no está diseñado para ser SaaS multi-tenant con cientos de accounts de clientes que no se conocen. Compartir Redis, Sidekiq y uploads entre clientes es un riesgo de incidentes.
- Aislamiento físico de datos es un argumento comercial fuerte (compliance, enterprise).
- Encaja con la filosofía de despliegue nativa de Chatwoot (self-hosted).
- Costo marginal por cliente predecible: ~$5 infra + OpenAI/Anthropic pass-through.
- Márgenes sanos sin necesidad de escalar a cientos de clientes.
- Evita bugs cross-tenant por diseño.

**Consecuencias aceptadas**:
- Ops burden lineal — cada cliente es un VPS que mantener, monitorizar y backupear.
- Necesidad eventual de un Control Plane para gestionar la flota (ver ADR-006).
- Updates y parches requieren fleet management disciplinado.
- Modelo de negocio nicho, no SaaS masivo de auto-registro.

---

## ADR-002 — Backend-only, sin UI en scope

**Decisión**: el proyecto entrega una API REST + WebSocket. No incluye frontend.

**Razones**:
- Reemplazar la UI de Chatwoot es una tarea subestimada que no aporta valor diferencial.
- El frontend puede ser construido después, por terceros, o puede no existir si el cliente solo consume la API.
- Swagger/OpenAPI se vuelve el "producto visible" para integradores.
- Permite iterar rápido sin la carga de UX/diseño.

**Consecuencias**:
- Documentación de API es crítica, no opcional.
- Versionado de API desde el día 1 (`/api/v1`).
- Ejemplos de uso y Postman collections necesarios para adopción.

---

## ADR-003 — Chatwoot como dependencia externa, no forkeado

**Decisión**: Chatwoot se usa como imagen Docker oficial. NO se porta, NO se forkea, NO se modifica.

**Razones**:
- Portar Chatwoot (~100k líneas de Ruby/Rails con 7+ años de edge cases) a FastAPI es económicamente inviable: 6-12 meses full-time para lograr algo apenas funcional y permanentemente desactualizado.
- Ahorrar RAM (~750MB) no justifica meses de trabajo en un VPS donde la RAM sobra.
- Forkear genera deuda técnica permanente: cada upgrade de Chatwoot se vuelve un conflicto de merge.
- El valor diferencial de ChatStudio está en la capa AI + automatización, no en reemplazar funcionalidad ya resuelta.

**Estrategia de reemplazo incremental**: si en el futuro una parte específica de Chatwoot estorba (ej. procesamiento de webhooks), se reemplaza esa parte puntual en FastAPI apuntando Meta directamente al endpoint propio, sin tocar el resto.

---

## ADR-004 — Reutilización del core de Seguros-BK (sin multi-tenancy)

**Decisión**: ChatStudio parte copiando la estructura de Seguros-BK como template inicial, eliminando la capa de multi-tenancy por Organization. Los dos proyectos viven en repos independientes y evolucionan por separado.

**Qué se reutiliza**:
- Auth JWT + API keys
- RBAC (roles y permisos dentro de una instancia)
- BaseService + filtros + paginación + WebSocket broadcasting
- Rate limiting por API key
- Storage (S3/local)
- ARQ workers
- Audit log + soft delete + GDPR
- Observabilidad (structured logging, Prometheus metrics)
- Setup Wizard visual (esencial para onboarding per-instancia)
- Tests, docs, docker-compose, alembic

**Qué se elimina**:
- Modelo `Organization` y toda la capa de aislamiento multi-tenant
- Billing interno (ahora es B2B externo, via Polar u otro)
- Modelos de dominio específicos de seguros (si existen)

**Razones**:
- ~70% del plumbing ya está resuelto y testeado.
- Evitar acoplamiento: un paquete compartido entre proyectos generaría fricción mutua.
- Duplicación de código es barata; acoplamiento prematuro es caro.

---

## ADR-005 — Modelo Meta: Tech Provider con Embedded Signup como objetivo

**Decisión**: ChatStudio opera como Tech Provider de Meta. El desarrollador/operador crea la app en su cuenta Meta verificada. Cada cliente conecta su propia WhatsApp Business Account (WABA) a través de esa app.

**Objetivo**: habilitar el flujo de **Embedded Signup** para reducir el onboarding de WhatsApp de 2-4 semanas a 1-2 días. Esto requiere pasar un App Review especial de Meta.

**Clarificación de responsabilidades**:
- El cliente aporta su propia WABA, business verification y número de teléfono.
- ChatStudio aporta el software, la app Meta y la capa de automatización.
- ChatStudio NO es BSP (Business Solution Provider) — no vende mensajes ni factura a Meta directamente.

**Consecuencias**:
- El App Review de Embedded Signup es prerequisito para producción a escala.
- Hasta conseguirlo, el onboarding manual sigue siendo válido para los primeros clientes.

---

## ADR-006 — Control Plane como proyecto separado (futuro)

**Decisión**: la gestión de la flota de instancias de ChatStudio se hará a través de un Control Plane propio, como proyecto independiente.

**Alcance del Control Plane**:
- Registro y ciclo de vida de clientes
- Provisioning automatizado de VPS (Contabo API) y despliegue de stack
- Health checks y monitorización centralizada
- Fleet updates (aplicar parches a todas las instancias)
- Facturación B2B (integración con Polar)
- Dashboard interno de operaciones

**Cuándo construirlo**: NO al inicio. Los primeros 3-5 clientes se gestionan manualmente. El Control Plane se construye cuando el dolor operativo lo justifique (estimado entre cliente 5 y 10).

**Base tecnológica**: el Control Plane SÍ reutiliza la multi-tenancy de Seguros-BK — cada "Organization" del Control Plane es un cliente externo con sus credenciales, billing y estado.

---

## ADR-007 — Billing B2B con Polar + herramientas de pago para agentes AI

**Decisión**: el billing de ChatStudio hacia los clientes finales se hace por fuera del producto, via Polar (Merchant of Record). Dentro de ChatStudio, los agentes AI tienen acceso a herramientas de pago (Mercado Pago, Stripe, etc.) como capability opcional para casos de uso de ventas.

**Razones**:
- Polar como MoR simplifica declaración de impuestos internacionales.
- Separar billing externo (cliente paga a ChatStudio) de billing interno (agente AI cobra al consumidor final) evita confusión conceptual.
- La integración base de pagos de Seguros-BK se reutiliza como librería o tool expuesta a los agentes.
- Mercado Pago requiere instancia local por país (Argentina opera con app hecha en MP Argentina) — esto se resuelve con configuración por instancia de ChatStudio.

---

## ADR-008 — Decisión técnica: persistencia compartida con Chatwoot

**Decisión**: ChatStudio y Chatwoot comparten la misma instancia de PostgreSQL (databases separadas) y de Redis (DB numbers separados).

- PostgreSQL: database `chatwoot` para Chatwoot, database `chatstudio` para ChatStudio (con extensión pgvector habilitada).
- Redis: `db=0` para Chatwoot, `db=1` para ChatStudio.

**Razones**:
- Menos servicios que mantener en cada VPS.
- Imagen `pgvector/pgvector:pg16` es Postgres estándar + extensión — Chatwoot no se ve afectado.
- Aislamiento suficiente a nivel de database para el modelo single-tenant.

**Riesgo mitigado**: un bug de Chatwoot NO afecta los datos de ChatStudio porque están en databases separadas. Los backups se hacen por database.

---

## Entradas futuras

Las decisiones futuras se agregan como `ADR-009`, `ADR-010`, etc., sin modificar las anteriores.
