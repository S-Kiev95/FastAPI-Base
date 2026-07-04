# ChatStudio — Plan de Desarrollo

> **Nota**: este documento reemplaza la versión anterior del plan. Las decisiones arquitectónicas clave están en [`ARCHITECTURE_DECISION.md`](./ARCHITECTURE_DECISION.md). El contrato de API público en [`API_SURFACE.md`](./API_SURFACE.md). El futuro panel de gestión en [`CONTROL_PLANE.md`](./CONTROL_PLANE.md).

---

## Concepto

ChatStudio es un **backend de atención al cliente multicanal con agentes AI**, desplegado como instancia dedicada por cliente (single-tenant), que se apoya en Chatwoot como motor de canales y agrega encima una capa propia de automatización, agentes inteligentes y extensiones.

**Modelo de negocio**: licencia de software + despliegue gestionado + soporte + desarrollo de agentes AI custom. Cobro B2B mensual via Polar (Merchant of Record).

---

## Arquitectura (vista rápida)

```
                    1 VPS por cliente (Contabo 8GB)
            ┌───────────────────────────────────────┐
            │                                       │
            │   Puerto 8000 (único expuesto vía     │
            │            Caddy/Traefik)             │
            │                                       │
            │  ┌─────────────────────────────────┐  │
            │  │         FastAPI                 │  │
            │  │  /api/v1/*  → API REST pública  │  │
            │  │  /ws        → WebSocket         │  │
            │  │  /setup     → Wizard inicial    │  │
            │  │  /docs      → Swagger           │  │
            │  └──────────┬──────────────────────┘  │
            │             │ httpx async             │
            │             ▼                         │
            │  ┌─────────────────────────────────┐  │
            │  │         Chatwoot                │  │
            │  │   (red interna Docker :3000)    │  │
            │  │                                 │  │
            │  │   - Canales (WhatsApp, IG, etc) │  │
            │  │   - Webhooks → FastAPI          │  │
            │  │   - Contactos, conversaciones   │  │
            │  └─────────────────────────────────┘  │
            │             │                         │
            │             ▼                         │
            │       Meta / Twilio / SMTP            │
            │                                       │
            │  ┌─────────────────────────────────┐  │
            │  │  Postgres (pgvector) + Redis    │  │
            │  │  compartidos entre FastAPI y    │  │
            │  │  Chatwoot (databases separadas) │  │
            │  └─────────────────────────────────┘  │
            │                                       │
            └───────────────────────────────────────┘
```

---

## Principios de construcción

1. **No duplicar lo que Chatwoot ya resuelve**. Si Chatwoot maneja adjuntos, contactos, canales — se delega. ChatStudio solo expone, enriquece o automatiza encima.
2. **Chatwoot es una dependencia, no un subsistema interno**. Nunca tocar su código ni su base de datos directamente — solo API y webhooks.
3. **Backend-first, contract-first**. El contrato de API se diseña antes de escribir endpoints.
4. **Reutilizar Seguros-BK sin sus costuras de multi-tenancy**. Copia limpia como punto de partida, no dependencia compartida.
5. **Ops scripts desde el día 1**. Provisioning manual pero documentado desde el primer cliente.

---

## Fases

### Fase 0 — Spike técnico (1 semana)

**Objetivo**: validar supuestos antes de comprometerse al desarrollo. Sin construir producto, solo aprender.

Entregables:
- Documento corto con el mapeo de la API de Chatwoot: qué endpoints cubren cada caso de uso previsto, cuáles tienen gaps, cuáles requieren query adicional.
- Prueba de webhook end-to-end: WhatsApp sandbox → Chatwoot → FastAPI stub → log.
- Prueba de envío: FastAPI stub → Chatwoot API → WhatsApp sandbox → teléfono real.
- Investigación de Embedded Signup de Meta: requisitos, App Review, tiempos estimados.
- Spike de despliegue: docker-compose con los 5 servicios arrancando en un VPS de prueba.
- Decisión documentada sobre reverse proxy (Caddy vs Traefik vs nginx).
- Decisión documentada sobre gestión de secretos (archivo .env vs variables Docker vs Vault).

**Criterio de salida**: sabemos exactamente qué podemos y qué no podemos hacer con Chatwoot + Meta. Si hay bloqueantes, se replantea el scope.

---

### Fase 1 — Núcleo funcional (MVP vendible)

**Objetivo**: un backend que recibe mensajes de WhatsApp vía Chatwoot, los procesa con un agente AI básico y responde. Expuesto vía REST y WebSocket. Sin UI.

Entregables:
- [ ] Copia limpia de Seguros-BK como base, eliminando multi-tenancy y modelos de dominio anteriores
- [ ] `docker-compose.yml` con los 5 servicios (Postgres+pgvector, Redis, Chatwoot, Chatwoot-sidekiq, FastAPI)
- [ ] Script `scripts/init.sql` que crea las dos databases (`chatwoot`, `chatstudio`)
- [ ] Cliente async de Chatwoot (`app/chatwoot/client.py`) con httpx
- [ ] Modelos Pydantic de eventos de webhook de Chatwoot (`app/chatwoot/schemas.py`)
- [ ] Endpoint `POST /api/v1/webhook/chatwoot` — recibe, valida, dispatch
- [ ] WebSocket manager hacia integradores (`/ws`) con canales por conversación
- [ ] Agente AI básico con LangGraph (1 nodo, respuesta directa, sin memoria)
- [ ] Tool para el agente: `send_message(conversation_id, text)` → Chatwoot API
- [ ] Setup Wizard adaptado: incluye configuración de Chatwoot API token, Meta tokens, claves de LLM
- [ ] Endpoints básicos de lectura: listar conversaciones, mensajes, contactos
- [ ] Tests E2E del flujo webhook → agente → respuesta (con Chatwoot mockeado)
- [ ] Documentación OpenAPI completa
- [ ] `deploy.sh` manual: script para desplegar el stack completo en un VPS fresh

**Criterio de salida**: un cliente ficticio puede mandar un mensaje a un número de WhatsApp de prueba y recibir una respuesta AI en < 15 segundos.

---

### Fase 2 — API pública completa sobre Chatwoot

**Objetivo**: exponer vía REST toda la funcionalidad que un integrador necesita, sin que tenga que hablar nunca con Chatwoot directamente.

Entregables:
- [ ] CRUD de inboxes vía API (crea inbox en Chatwoot + persiste metadata propia)
- [ ] CRUD de webhooks vía API (registra en Chatwoot automáticamente)
- [ ] Endpoints de contactos (listar, buscar, crear, actualizar, etiquetar)
- [ ] Endpoints de conversaciones (listar, filtrar por estado/inbox/etiqueta, asignar, cerrar)
- [ ] Endpoints de mensajes (enviar, listar, adjuntos)
- [ ] Sistema de etiquetas y custom attributes
- [ ] Endpoints de equipos y asignación
- [ ] Paginación consistente (cursor-based) en todos los listados
- [ ] Filtros avanzados reutilizando `FilterMixin` de Seguros-BK
- [ ] API keys con scopes por endpoint (reutilizando infra de Seguros-BK)

**Criterio de salida**: Swagger tiene todos los endpoints documentados y un test E2E los recorre todos.

---

### Fase 3 — Agentes AI avanzados

**Objetivo**: sistema de agentes configurables con memoria, RAG y escalación.

Entregables:
- [ ] LangGraph multi-nodo: clasificación → ruteo → respuesta → evaluación
- [ ] Memoria de conversación con embeddings en pgvector
- [ ] Knowledge base por inbox/canal (RAG) con ingesta de documentos
- [ ] Configuración de personalidad/tono/restricciones por inbox desde la API
- [ ] Handoff a humano con resumen de contexto generado
- [ ] Modo "manual" por etiqueta (si conversación tiene tag `manual`, el bot no responde)
- [ ] Tool de acceso a información externa (HTTP calls, parametrizable)
- [ ] Tool de pagos: generar link de Mercado Pago / Stripe desde el flujo (reutilizando la integración base de Seguros-BK)
- [ ] Métricas por agente: conversaciones atendidas, tasa de escalación, latencia promedio
- [ ] Audit log completo de decisiones del agente

**Criterio de salida**: un cliente puede configurar un agente de ventas que clasifica leads, responde FAQs, envía links de pago y escala a humano cuando hace falta — todo vía API.

---

### Fase 4 — Extensiones propias (Instagram posts, WhatsApp templates)

**Objetivo**: features que Chatwoot no cubre.

Entregables:
- [ ] Instagram Graph API: programar y publicar posts (imágenes, carruseles, reels)
- [ ] Calendario editorial con ARQ workers (scheduled posts)
- [ ] Métricas básicas de engagement por post
- [ ] WhatsApp Templates: generación asistida con LLM
- [ ] Submit de templates a Meta vía API, tracking de estado de aprobación
- [ ] Envío masivo de templates aprobados (HSM) con rate limiting
- [ ] Sistema de campañas con segmentación básica

**Criterio de salida**: un cliente puede publicar un post en Instagram y enviar una campaña de WhatsApp desde la API, sin tocar nunca Business Manager después del setup inicial.

---

### Fase 5 — Embedded Signup + App Review Meta

**Objetivo**: reducir el onboarding de clientes de 2-4 semanas a 1-2 días.

Entregables:
- [ ] Integración con el flujo de Embedded Signup de Meta
- [ ] Documentación exhaustiva para pasar App Review (privacy policy, terms, data deletion endpoints, demo video)
- [ ] Endpoints de data deletion compliant (reutilizando GDPR de Seguros-BK)
- [ ] Flujo guiado de primer inbox conectado vía API
- [ ] Submission del App Review

**Criterio de salida**: Meta aprueba el App Review y un cliente nuevo puede conectar su WhatsApp en minutos.

---

## Stack técnico (confirmado)

| Capa | Tecnología |
|---|---|
| Backend API | FastAPI (Python 3.13+) |
| ORM | SQLModel + SQLAlchemy async |
| Base de datos | PostgreSQL 16 + pgvector |
| Cache / colas | Redis 7 |
| Jobs async | ARQ |
| AI Agents | LangGraph + LangChain |
| LLM | OpenAI GPT-4o / Anthropic Claude (configurable) |
| HTTP client | httpx async |
| Real-time | WebSockets nativos FastAPI |
| Canal engine | Chatwoot (imagen oficial, sin modificar) |
| Contenedores | Docker + Docker Compose |
| Reverse proxy | Caddy (decisión tentativa, validar en Fase 0) |
| Observabilidad | Structured logging (JSON) + Prometheus metrics + Sentry |
| Tests | pytest + httpx TestClient |
| Migraciones | Alembic |

---

## Decisiones explícitas de NO hacer

- ❌ **No portamos Chatwoot a Python**. Ver ADR-003.
- ❌ **No construimos UI en el scope de ChatStudio**. Si se necesita, es un proyecto separado.
- ❌ **No hacemos multi-tenancy dentro de ChatStudio**. Cada cliente es una instancia.
- ❌ **No construimos Control Plane al principio**. Primeros clientes son manuales.
- ❌ **No integramos todos los canales de Chatwoot en Fase 1**. Solo WhatsApp. El resto llega en fases posteriores o según demanda.
- ❌ **No optimizamos prematuramente** recursos de infra. 8GB VPS es suficiente.

---

## Orden de ejecución sugerido

1. Fase 0 completa antes de tocar código de producto
2. Fase 1 hasta tener MVP vendible (primer cliente real)
3. Fase 2 en paralelo con soporte a primeros clientes
4. Fase 3 cuando haya 2-3 clientes pidiendo funcionalidades AI más ricas
5. Fase 4 oportunista (cuando un cliente lo pague como feature custom)
6. Fase 5 cuando el dolor de onboarding Meta sea mayor que el esfuerzo de App Review

---

*Documento generado: 2026-04-08 · Reemplaza versión anterior del 2026-04-06*
