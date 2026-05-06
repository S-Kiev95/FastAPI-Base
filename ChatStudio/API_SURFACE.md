# ChatStudio — API Surface (Borrador)

Este documento es el **contrato público** de la API REST y WebSocket que ChatStudio expone a sus integradores. Se diseña antes de implementar para detectar gaps con la API de Chatwoot.

**Estado**: borrador. Sujeto a cambios durante Fase 0 (spike técnico).

---

## Convenciones

- Base URL: `https://{instance}.chatstudio.example/api/v1`
- Autenticación: `Authorization: Bearer <API_KEY>` (API keys gestionadas por la misma capa de Seguros-BK)
- Content-Type: `application/json`
- Fechas: ISO 8601 UTC (`2026-04-08T10:30:00Z`)
- Paginación: cursor-based (`?cursor=...&limit=50`)
- Errores: estructura estándar FastAPI + código interno
  ```json
  { "detail": "mensaje humano", "code": "CHATSTUDIO_ERR_001", "field": "optional" }
  ```
- Versionado: `/api/v1` desde el día 1. Breaking changes → `/api/v2`.

---

## Recursos

### Inboxes

Un `Inbox` representa un canal conectado (ej. un número de WhatsApp, una cuenta de Instagram).

| Método | Path | Descripción |
|---|---|---|
| `GET` | `/inboxes` | Listar todos los inboxes |
| `POST` | `/inboxes` | Crear un nuevo inbox (delega en Chatwoot API) |
| `GET` | `/inboxes/{id}` | Detalle de un inbox |
| `PATCH` | `/inboxes/{id}` | Actualizar configuración |
| `DELETE` | `/inboxes/{id}` | Eliminar inbox |
| `POST` | `/inboxes/{id}/test` | Enviar mensaje de prueba al canal |

Payload de creación:
```json
{
  "name": "Ventas WhatsApp",
  "channel_type": "whatsapp" | "instagram" | "email" | "api",
  "config": {
    "phone_number_id": "...",
    "access_token": "...",
    "business_account_id": "..."
  }
}
```

---

### Conversations

| Método | Path | Descripción |
|---|---|---|
| `GET` | `/conversations` | Listar conversaciones (filtros: inbox, status, assignee, labels, date range) |
| `GET` | `/conversations/{id}` | Detalle de conversación |
| `GET` | `/conversations/{id}/messages` | Mensajes de una conversación |
| `POST` | `/conversations/{id}/messages` | Enviar mensaje (texto, adjunto) |
| `POST` | `/conversations/{id}/assign` | Asignar a agente humano o bot |
| `PATCH` | `/conversations/{id}/status` | Cambiar estado (open/resolved/pending/snoozed) |
| `POST` | `/conversations/{id}/labels` | Agregar etiquetas |
| `DELETE` | `/conversations/{id}/labels/{label}` | Quitar etiqueta |
| `POST` | `/conversations/{id}/notes` | Agregar nota interna |
| `GET` | `/conversations/{id}/summary` | **Extra**: resumen AI generado |
| `POST` | `/conversations/{id}/handoff` | **Extra**: transferir de bot a humano con contexto |

Filtros soportados (query params):
- `status` (open, resolved, pending, snoozed)
- `inbox_id`
- `assignee_type` (bot, human, unassigned)
- `labels` (lista separada por coma)
- `updated_after`, `updated_before`
- `has_unread`

---

### Contacts

| Método | Path | Descripción |
|---|---|---|
| `GET` | `/contacts` | Listar contactos con búsqueda full-text |
| `POST` | `/contacts` | Crear contacto |
| `GET` | `/contacts/{id}` | Detalle |
| `PATCH` | `/contacts/{id}` | Actualizar |
| `DELETE` | `/contacts/{id}` | Eliminar |
| `GET` | `/contacts/{id}/conversations` | Todas las conversaciones del contacto |
| `POST` | `/contacts/{id}/custom_attributes` | Agregar atributo custom |

---

### Messages (directos)

| Método | Path | Descripción |
|---|---|---|
| `POST` | `/messages/send` | Enviar mensaje proactivo (crea conversación si no existe) |
| `GET` | `/messages/{id}` | Detalle de mensaje |
| `GET` | `/messages/{id}/status` | Estado de entrega (sent/delivered/read/failed) |

---

### Agents (Humanos)

| Método | Path | Descripción |
|---|---|---|
| `GET` | `/agents` | Listar agentes humanos |
| `POST` | `/agents` | Crear agente humano |
| `PATCH` | `/agents/{id}` | Actualizar |
| `DELETE` | `/agents/{id}` | Eliminar |
| `GET` | `/agents/{id}/stats` | Estadísticas (conversaciones atendidas, tiempo promedio) |

---

### AI Agents (Bots)

Esta es la capa propia de ChatStudio, no existe en Chatwoot.

| Método | Path | Descripción |
|---|---|---|
| `GET` | `/ai-agents` | Listar agentes AI configurados |
| `POST` | `/ai-agents` | Crear agente AI |
| `GET` | `/ai-agents/{id}` | Detalle (config, prompts, tools habilitados) |
| `PATCH` | `/ai-agents/{id}` | Actualizar configuración |
| `DELETE` | `/ai-agents/{id}` | Eliminar |
| `POST` | `/ai-agents/{id}/test` | Probar con un mensaje de ejemplo |
| `GET` | `/ai-agents/{id}/metrics` | Métricas: mensajes procesados, tasa escalación, latencia |
| `POST` | `/ai-agents/{id}/assign-inbox/{inbox_id}` | Asociar agente a inbox |

Payload de creación:
```json
{
  "name": "Vendedor Soleadita",
  "model": "gpt-4o" | "claude-opus-4-6",
  "system_prompt": "Eres un vendedor amigable de seguros...",
  "temperature": 0.7,
  "tools": ["web_search", "send_payment_link", "schedule_callback"],
  "knowledge_base_id": "kb_123",
  "handoff_triggers": ["keyword:supervisor", "sentiment:angry", "intent:complaint"]
}
```

---

### Knowledge Base (RAG)

| Método | Path | Descripción |
|---|---|---|
| `GET` | `/knowledge-bases` | Listar KBs |
| `POST` | `/knowledge-bases` | Crear KB |
| `DELETE` | `/knowledge-bases/{id}` | Eliminar |
| `POST` | `/knowledge-bases/{id}/documents` | Ingestar documento (PDF, TXT, URL) |
| `GET` | `/knowledge-bases/{id}/documents` | Listar documentos |
| `DELETE` | `/knowledge-bases/{id}/documents/{doc_id}` | Eliminar documento |
| `POST` | `/knowledge-bases/{id}/query` | Búsqueda semántica manual |

---

### Labels

| Método | Path | Descripción |
|---|---|---|
| `GET` | `/labels` | Listar |
| `POST` | `/labels` | Crear |
| `DELETE` | `/labels/{id}` | Eliminar |

---

### Webhooks (Salientes hacia integradores)

Permite a integradores suscribirse a eventos de ChatStudio.

| Método | Path | Descripción |
|---|---|---|
| `GET` | `/webhooks` | Listar webhooks configurados |
| `POST` | `/webhooks` | Registrar webhook |
| `DELETE` | `/webhooks/{id}` | Eliminar |

Eventos soportados:
- `conversation.created`
- `conversation.resolved`
- `message.received`
- `message.sent`
- `message.delivery_failed`
- `ai_agent.escalated`
- `contact.created`

---

### Webhooks entrantes (desde Chatwoot)

No son API pública — son endpoints internos. Documentados aquí para completitud.

| Método | Path | Descripción |
|---|---|---|
| `POST` | `/internal/webhook/chatwoot` | Recibe eventos de Chatwoot, valida firma |

---

### WhatsApp Templates

| Método | Path | Descripción |
|---|---|---|
| `GET` | `/whatsapp/templates` | Listar templates |
| `POST` | `/whatsapp/templates` | Crear y enviar a Meta para aprobación |
| `GET` | `/whatsapp/templates/{id}` | Detalle + estado de aprobación |
| `DELETE` | `/whatsapp/templates/{id}` | Eliminar |
| `POST` | `/whatsapp/templates/{id}/generate` | **Extra**: generar con AI |
| `POST` | `/whatsapp/campaigns` | Envío masivo de template aprobado |

---

### Instagram Posts

| Método | Path | Descripción |
|---|---|---|
| `GET` | `/instagram/posts` | Listar posts programados/publicados |
| `POST` | `/instagram/posts` | Crear post (inmediato o programado) |
| `PATCH` | `/instagram/posts/{id}` | Modificar (solo si no publicado) |
| `DELETE` | `/instagram/posts/{id}` | Cancelar/eliminar |
| `GET` | `/instagram/posts/{id}/metrics` | Métricas de engagement |

---

### Analytics

| Método | Path | Descripción |
|---|---|---|
| `GET` | `/analytics/conversations` | Volumen por fecha/canal/estado |
| `GET` | `/analytics/messages` | Volumen de mensajes entrantes/salientes |
| `GET` | `/analytics/response-time` | Tiempos de respuesta (bot vs humano) |
| `GET` | `/analytics/ai-performance` | Métricas agregadas de agentes AI |

---

### System

| Método | Path | Descripción |
|---|---|---|
| `GET` | `/health` | Health check (incluye estado de Chatwoot + DB + Redis) |
| `GET` | `/version` | Versión del backend |
| `GET` | `/setup/status` | Estado del wizard inicial |

---

## WebSocket API

Path: `wss://{instance}.chatstudio.example/ws?token={API_KEY}`

### Canales

- `conversation:{id}` — eventos de una conversación específica
- `inbox:{id}` — eventos de todas las conversaciones de un inbox
- `global` — eventos del sistema

### Eventos emitidos por el servidor

```json
{ "type": "message.received", "channel": "conversation:123", "data": {...} }
{ "type": "message.sent", "channel": "conversation:123", "data": {...} }
{ "type": "conversation.created", "channel": "inbox:5", "data": {...} }
{ "type": "conversation.status_changed", "channel": "conversation:123", "data": {...} }
{ "type": "ai_agent.thinking", "channel": "conversation:123", "data": {"agent_id": "..."} }
{ "type": "ai_agent.responded", "channel": "conversation:123", "data": {...} }
{ "type": "ai_agent.escalated", "channel": "conversation:123", "data": {"reason": "..."} }
```

### Comandos del cliente

```json
{ "action": "subscribe", "channel": "conversation:123" }
{ "action": "unsubscribe", "channel": "conversation:123" }
{ "action": "ping" }
```

---

## Gaps conocidos con la API de Chatwoot (a validar en Fase 0)

Esta sección se completará durante el spike técnico. Lista inicial de sospechas:

- ¿La API de Chatwoot soporta crear inboxes de WhatsApp Cloud API programáticamente, o solo por UI?
- ¿El webhook de Chatwoot incluye todo el contexto del mensaje, o hace falta query adicional?
- ¿Cómo se maneja la autenticación al API de Chatwoot (user access token) en un despliegue automatizado?
- ¿Hay eventos granulares de estado de mensaje (sent → delivered → read) o solo agregados?
- ¿La API expone los custom attributes de forma que podamos leerlos/escribirlos?
- ¿Cómo se gestionan los adjuntos grandes (>25MB) en el webhook?
- ¿La API permite búsqueda full-text en conversaciones?
- ¿Hay rate limits en la API de Chatwoot que afecten bursts de envío masivo?

**Cada uno de estos gaps debe cerrarse con una decisión explícita antes de Fase 1**: o confiamos en la API, o implementamos un workaround, o acotamos scope.

---

## Pendientes de diseño

- Esquema exacto de los DTOs de request/response (Pydantic schemas)
- Estrategia de rate limiting por endpoint
- Política de retención de datos (GDPR)
- Esquema de API keys con scopes granulares
- Idempotency keys para operaciones de envío
- Paginación: cursor-based exacto (¿sort by updated_at + id como tiebreaker?)

---

*Documento generado: 2026-04-08 · Versión inicial*
