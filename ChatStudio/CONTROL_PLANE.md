# ChatStudio — Control Plane (Brief)

> **Proyecto futuro**. No se construye al inicio de ChatStudio. Este documento fija el alcance para cuando llegue el momento.

---

## Qué es

El **Control Plane** es un panel de administración **interno** (solo para el operador de ChatStudio, no para los clientes finales) que gestiona la flota de instancias de ChatStudio desplegadas en VPS.

Es un proyecto **separado**, con su propio repositorio y su propio ciclo de vida. Los clientes de ChatStudio no lo ven nunca.

---

## Por qué existe

El modelo single-tenant (ADR-001) significa que cada cliente tiene su propia instancia. Eso genera un problema de escala operativa: a partir del cliente ~5, gestionar todo manualmente se vuelve ineficiente.

El Control Plane resuelve:

- **Provisioning**: lanzar un nuevo VPS + stack ChatStudio desde un botón en lugar de 1 hora de trabajo manual.
- **Fleet awareness**: saber en tiempo real qué instancias están vivas, qué versión corren, qué uso de recursos tienen.
- **Fleet updates**: aplicar un parche de seguridad o una release a N instancias sin tocar cada una manualmente.
- **Billing B2B**: integración con Polar (Merchant of Record) para cobrar a los clientes mensualmente.
- **Ciclo de vida del cliente**: trial → activo → suspendido → cancelado, con automatización del acceso según estado de pago.
- **Soporte**: acceso rápido a logs, métricas y estado de cualquier instancia sin SSH manual.

---

## Cuándo construirlo

**NO al principio**. El Control Plane es over-engineering hasta que el dolor operativo lo justifique.

Heurística de decisión por cantidad de clientes:

| Clientes | Herramienta | Por qué |
|---|---|---|
| 1-3 | Spreadsheet + bash scripts | El costo de construir es mayor al dolor de gestionar |
| 4-10 | Spreadsheet + `deploy.sh` robusto + Makefile | Automatizás lo repetitivo sin framework |
| 10-30 | **Control Plane v1** (mínimo viable) | El dolor justifica el esfuerzo |
| 30+ | **Control Plane v2** (con monitorización centralizada) | Escalar soporte requiere observabilidad |

---

## Alcance del Control Plane v1 (MVP)

Cuando se construya, debería tener **solo esto**:

### Gestión de clientes
- CRUD de clientes con: nombre, contacto, plan, subdominio asignado, estado de billing
- Estados: `trial`, `active`, `past_due`, `suspended`, `cancelled`
- Historial de cambios de plan

### Provisioning
- Integración con Contabo API para lanzar VPS
- Trigger manual "Provisionar cliente X" → pipeline:
  1. Crear VPS via Contabo API
  2. Esperar a que esté accesible por SSH
  3. Correr playbook de bootstrap (instala Docker, Caddy, clona repo ChatStudio, levanta stack)
  4. Configurar DNS (subdominio apuntando a IP del VPS)
  5. Generar credenciales admin iniciales
  6. Enviar email al cliente con datos de acceso
- Pipeline idempotente y retry-friendly

### Monitorización básica
- Endpoint `/health` de cada instancia consumido periódicamente (cada 5 min)
- Dashboard con estado de cada instancia: up/down, versión, uptime
- Alertas por email/Telegram si una instancia cae

### Billing
- Integración con Polar (MoR) para facturación mensual
- Webhook de Polar → actualizar estado del cliente
- Automatización: cliente `past_due` → notificación → `suspended` tras N días → apagar VPS vía Contabo API

### Operaciones de flota
- Aplicar update de ChatStudio a todas las instancias (o subset filtrado)
- Backup on-demand de una instancia
- SSH session launcher (generar comando con la IP correcta)

---

## Alcance del Control Plane v2 (cuando duela)

- Observabilidad centralizada con Grafana + Loki (logs agregados)
- Métricas Prometheus federadas de toda la flota
- Alertas inteligentes (umbrales dinámicos, detección de anomalías)
- Blue/green deploys por instancia (sin downtime)
- Rollback automático si una instancia falla health check post-update
- Multi-región (instancias en distintos datacenters Contabo)
- Roles internos (operador, soporte, billing) con acceso segmentado

---

## Stack sugerido

**Reutiliza Seguros-BK sin modificaciones estructurales.** El Control Plane es *exactamente* el caso de uso para el que Seguros-BK fue diseñado:

| Seguros-BK feature | Uso en Control Plane |
|---|---|
| Multi-tenancy por Organization | Cada `Organization` = 1 cliente externo de ChatStudio |
| Auth JWT + roles | Tú + eventual equipo de soporte |
| API keys | Webhooks de Polar, integraciones |
| Billing + Gateway adapter | Facturación B2B via Polar |
| Rate limiting | Protección del panel |
| Audit log | Quién hizo qué en la flota |
| ARQ workers | Jobs de provisioning y mantenimiento |
| WebSocket manager | Updates en tiempo real del dashboard |
| Svelte admin panel | UI del Control Plane (ya existe en Seguros-BK) |
| Setup Wizard | Bootstrap del Control Plane mismo |

Es decir: **el Control Plane es un fork de Seguros-BK con modelos adicionales** (`ClientInstance`, `ProvisioningJob`, `FleetUpdate`, etc.) y tareas ARQ específicas para talk a Contabo/SSH/Chatwoot.

---

## Modelos de datos (borrador)

```
ClientInstance
├── id
├── organization_id (FK → Organization)
├── subdomain
├── vps_provider ("contabo")
├── vps_id (ID del VPS en Contabo)
├── vps_ip
├── ssh_key_id
├── chatstudio_version
├── chatwoot_version
├── status (provisioning | active | suspended | failed | decommissioned)
├── provisioned_at
├── last_health_check_at
├── last_health_check_status
└── metadata (JSON)

ProvisioningJob
├── id
├── client_instance_id
├── type (provision | update | backup | restore | destroy)
├── status (pending | running | success | failed)
├── started_at
├── finished_at
├── logs (texto completo del pipeline)
└── error (si falló)

FleetUpdate
├── id
├── from_version
├── to_version
├── started_at
├── target_instances (lista)
├── status
└── results (por instancia)
```

---

## Decisiones abiertas (para cuando se construya)

- ¿Ansible, Pyinfra o bash scripts para el playbook de provisioning?
- ¿SSH directo o Tailscale/WireGuard para acceso a las instancias?
- ¿Cómo gestionar secretos por cliente (API keys Meta, LLM)? ¿Vault, SOPS, variables Docker?
- ¿Los backups se almacenan centralizados (S3 tuyo) o por instancia?
- ¿El Control Plane expone una API pública para clientes (ej. para que vean su propio estado), o es 100% interno?

---

*Documento generado: 2026-04-08 · Brief inicial*
