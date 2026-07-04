# 🏗️ Arquitectura del Sistema

Documentación técnica completa del backend SaaS. Esta guía está diseñada para que cualquier desarrollador pueda entender el proyecto sin conocimiento previo.

---

## 📑 Tabla de Contenidos

1. [Visión General](#visión-general)
2. [Stack Tecnológico](#stack-tecnológico)
3. [Arquitectura de Alto Nivel](#arquitectura-de-alto-nivel)
4. [Estructura de Capas](#estructura-de-capas)
5. [Flujo de Autenticación](#flujo-de-autenticación)
6. [Modelo de Datos](#modelo-de-datos)
7. [Multi-Tenancy](#multi-tenancy)
8. [Sistema de Billing](#sistema-de-billing)
9. [Pipeline de Middleware](#pipeline-de-middleware)
10. [WebSockets y Broadcasting](#websockets-y-broadcasting)
11. [Task Queue Asíncrona](#task-queue-asíncrona)
12. [Storage y Media](#storage-y-media)
13. [Deployment Architecture](#deployment-architecture)
14. [Observabilidad](#observabilidad)

---

## 🎯 Visión General

Este proyecto es un **backend SaaS modular** construido como un monolito bien estructurado. Está diseñado para ser:

- **Reutilizable**: Template base para cualquier proyecto SaaS
- **Multi-tenant**: Aislamiento completo de datos entre organizaciones
- **Production-ready**: Seguridad, observabilidad, tests completos
- **Escalable**: Soporta horizontal scaling y async processing
- **GDPR-compliant**: Export, deletion, audit trails

```mermaid
graph TB
    subgraph "Clientes"
        WEB[Web App]
        MOBILE[Mobile App]
        API_CLIENT[API Clients]
    end

    subgraph "Backend SaaS"
        BACKEND[FastAPI Backend]
        ADMIN[Admin Panel Svelte]
        WS[WebSocket Server]
    end

    subgraph "Infrastructure"
        DB[(PostgreSQL<br/>+ pgvector)]
        REDIS[(Redis<br/>Cache + Queue)]
        S3[S3 Storage]
        SMTP[SMTP Server]
    end

    subgraph "Third-party"
        STRIPE[Stripe]
        MP[MercadoPago]
        POLAR[Polar]
        SENTRY[Sentry]
    end

    WEB --> BACKEND
    MOBILE --> BACKEND
    API_CLIENT --> BACKEND
    BACKEND --> ADMIN
    BACKEND --> WS

    BACKEND --> DB
    BACKEND --> REDIS
    BACKEND --> S3
    BACKEND --> SMTP

    BACKEND --> STRIPE
    BACKEND --> MP
    BACKEND --> POLAR
    BACKEND --> SENTRY

    style BACKEND fill:#3b82f6,color:#fff
    style DB fill:#10b981,color:#fff
    style REDIS fill:#ef4444,color:#fff
```

---

## 🔧 Stack Tecnológico

| Capa | Tecnología | Propósito |
|------|------------|-----------|
| **Runtime** | Python 3.13+ | Lenguaje base |
| **Framework** | FastAPI | Web framework async |
| **ORM** | SQLModel | Type-safe (Pydantic + SQLAlchemy) |
| **Database** | PostgreSQL 15+ | DB principal con pgvector |
| **Cache** | Redis 7+ | Cache, rate limiting, task queue |
| **Task Queue** | ARQ | Tareas async en background |
| **Storage** | S3-compatible | Archivos y media |
| **Migrations** | Alembic | Migraciones de schema |
| **Auth** | JWT + bcrypt | Tokens + password hashing |
| **Admin UI** | SvelteKit | Panel de administración |
| **Monitoring** | Prometheus + Grafana | Métricas y dashboards |
| **Error Tracking** | Sentry | Error reporting |
| **Testing** | pytest | 216 tests |

---

## 🏛️ Arquitectura de Alto Nivel

El backend sigue una arquitectura de **monolito modular** con separación clara de responsabilidades:

```mermaid
graph LR
    subgraph "Presentation Layer"
        R1[Routes]
        R2[WebSocket Endpoints]
        R3[Admin Panel]
    end

    subgraph "Business Logic Layer"
        S1[Services]
        S2[BaseService Generic]
        S3[Plan Guards]
        S4[Validators]
    end

    subgraph "Data Access Layer"
        M1[SQLModel Models]
        M2[Alembic Migrations]
        M3[Cache Layer]
    end

    subgraph "Infrastructure"
        I1[Database Engine]
        I2[Redis Client]
        I3[S3 Client]
        I4[ARQ Workers]
    end

    R1 --> S1
    R2 --> S1
    R3 --> S1
    S1 --> S2
    S1 --> S3
    S1 --> S4
    S2 --> M1
    S2 --> M3
    M1 --> I1
    M3 --> I2
    S1 --> I3
    S1 --> I4

    style S2 fill:#3b82f6,color:#fff
```

---

## 📚 Estructura de Capas

### Patrón: Routes → Services → Models

Todas las operaciones siguen el mismo flujo:

```mermaid
sequenceDiagram
    autonumber
    participant C as Cliente
    participant R as Route
    participant D as Dependencies
    participant S as Service
    participant M as Model
    participant DB as Database
    participant CA as Cache
    participant WS as WebSocket

    C->>R: HTTP Request
    R->>D: Resolve dependencies
    D->>D: Auth + Permissions
    D-->>R: User + Session
    R->>S: Call service method
    S->>CA: Check cache
    alt Cache hit
        CA-->>S: Return cached data
    else Cache miss
        S->>M: Query model
        M->>DB: SQL query
        DB-->>M: Result
        M-->>S: Model instance
        S->>CA: Store in cache
    end
    S->>WS: Broadcast change (if write)
    S-->>R: Return data
    R-->>C: HTTP Response
```

### BaseService Pattern

Todos los servicios heredan de `BaseService[Model, Create, Update, Read]`:

```mermaid
classDiagram
    class BaseService~ModelT, CreateT, UpdateT, ReadT~ {
        +model: Type[ModelT]
        +create_schema: Type[CreateT]
        +update_schema: Type[UpdateT]
        +read_schema: Type[ReadT]
        +cache_prefix: str
        +channel: WebSocketChannel
        +get_by_id(id) ModelT
        +list(filters, sort, page) Page~ReadT~
        +create(data, audit) ModelT
        +update(id, data, audit) ModelT
        +delete(id, audit) bool
        +soft_delete(id) bool
        +restore(id) bool
        -_audit(action, changes)
        -_cache_invalidate()
        -_broadcast(event, data)
    }

    class UserService {
        +get_user_by_email()
        +verify_password()
        +update_last_login()
    }

    class OrganizationService {
        +create_with_owner()
        +invite_member()
        +remove_member()
    }

    class BillingService {
        +change_plan()
        +cancel_subscription()
        +handle_webhook()
    }

    BaseService <|-- UserService
    BaseService <|-- OrganizationService
    BaseService <|-- BillingService
```

**Beneficios:**
- ✅ CRUD automático en todos los modelos
- ✅ Cache transparente (Redis)
- ✅ WebSocket broadcasting automático
- ✅ Audit log automático
- ✅ Soft delete integrado
- ✅ Filtros, sorting, paginación

---

## 🔐 Flujo de Autenticación

El sistema soporta **autenticación dual**: JWT tokens y API Keys.

### Flujo JWT (usuarios web)

```mermaid
sequenceDiagram
    autonumber
    participant U as Usuario
    participant F as Frontend
    participant B as Backend
    participant DB as Database
    participant R as Redis

    U->>F: Ingresa email + password
    F->>B: POST /auth/login
    B->>DB: Buscar usuario por email
    DB-->>B: User record
    B->>B: bcrypt.verify(password, hash)
    alt Password válido
        B->>B: Crear JWT access token (15 min)
        B->>B: Crear refresh token (30 días)
        B->>DB: Guardar refresh token
        B->>R: Check rate limit
        B-->>F: access + refresh tokens
        F->>F: Guardar tokens (httpOnly cookie)
        F-->>U: Redirect al dashboard
    else Password inválido
        B->>R: Incrementar intentos fallidos
        B-->>F: 401 Unauthorized
        F-->>U: Mostrar error
    end
```

### Flujo API Key (integraciones)

```mermaid
sequenceDiagram
    autonumber
    participant C as Cliente API
    participant B as Backend
    participant DB as Database

    C->>B: Request con header<br/>Authorization: Bearer sk_live_...
    B->>B: Detectar prefijo sk_live_
    B->>B: Hash SHA-256 de la key
    B->>DB: Buscar API key por hash
    alt Key válida y activa
        DB-->>B: API key + user info
        B->>DB: Actualizar last_used_at
        B->>B: Verificar scopes
        B-->>C: Response con datos
    else Key inválida/revocada
        B-->>C: 401 Unauthorized
    end
```

### Autenticación Dual en Dependency

```mermaid
flowchart TD
    START[Request recibido] --> EXTRACT[Extraer Bearer token]
    EXTRACT --> CHECK{Empieza con<br/>sk_live_?}
    CHECK -->|Sí| APIKEY[API Key Auth]
    CHECK -->|No| JWT[JWT Auth]

    APIKEY --> HASH[SHA-256 hash]
    HASH --> LOOKUP_KEY[Buscar en DB]
    LOOKUP_KEY --> VALID_KEY{Válida?}

    JWT --> DECODE[Decodificar JWT]
    DECODE --> VERIFY[Verificar signature]
    VERIFY --> VALID_JWT{Válido?}

    VALID_KEY -->|Sí| GET_USER[Obtener usuario]
    VALID_JWT -->|Sí| GET_USER
    VALID_KEY -->|No| DENY[401 Unauthorized]
    VALID_JWT -->|No| DENY

    GET_USER --> CHECK_ACTIVE{Usuario activo?}
    CHECK_ACTIVE -->|Sí| ALLOW[Permitir acceso]
    CHECK_ACTIVE -->|No| DENY

    style ALLOW fill:#10b981,color:#fff
    style DENY fill:#ef4444,color:#fff
```

---

## 💾 Modelo de Datos

### Diagrama de Entidades Principal

```mermaid
erDiagram
    USER ||--o{ MEMBERSHIP : has
    USER ||--o{ API_KEY : owns
    USER ||--o{ AUDIT_LOG : generates
    USER ||--o{ REFRESH_TOKEN : has
    USER }o--o{ ROLE : has

    ORGANIZATION ||--o{ MEMBERSHIP : has
    ORGANIZATION ||--|| SUBSCRIPTION : has
    ORGANIZATION ||--o{ INVITATION : sends
    ORGANIZATION ||--o{ MEDIA : owns
    ORGANIZATION ||--o{ PAYMENT : has

    ROLE }o--o{ PERMISSION : has

    SUBSCRIPTION ||--o{ PAYMENT : has

    USER {
        int id PK
        string email UK
        string hashed_password
        string name
        bool is_active
        bool is_verified
        bool is_superadmin
        datetime deleted_at
        datetime created_at
    }

    ORGANIZATION {
        int id PK
        string name
        string slug UK
        bool is_active
        datetime deleted_at
        datetime created_at
    }

    MEMBERSHIP {
        int id PK
        int user_id FK
        int organization_id FK
        string role
        datetime joined_at
    }

    SUBSCRIPTION {
        int id PK
        int organization_id FK
        string plan
        string status
        datetime current_period_end
        datetime cancelled_at
    }

    API_KEY {
        uuid id PK
        int user_id FK
        string name
        string key_hash
        string key_prefix
        json scopes
        datetime last_used_at
        datetime expires_at
    }

    AUDIT_LOG {
        int id PK
        int user_id FK
        string action
        string resource_type
        string resource_id
        json changes
        string ip_address
        datetime created_at
    }

    MEDIA {
        int id PK
        int user_id FK
        int organization_id FK
        string filename
        string s3_key
        int file_size
        string mime_type
        datetime deleted_at
    }
```

### Campos Comunes en Modelos

Todos los modelos incluyen campos base del `BaseModel`:

```mermaid
classDiagram
    class BaseModel {
        +id: int
        +created_at: datetime
        +updated_at: datetime
    }

    class SoftDeleteMixin {
        +deleted_at: Optional[datetime]
        +is_deleted: bool
        +soft_delete()
        +restore()
    }

    class TimestampMixin {
        +created_at: datetime
        +updated_at: datetime
    }

    class OrganizationScopedMixin {
        +organization_id: int
    }

    BaseModel <|-- User
    BaseModel <|-- Organization
    BaseModel <|-- Media
    SoftDeleteMixin <|-- User
    SoftDeleteMixin <|-- Organization
    SoftDeleteMixin <|-- Media
    OrganizationScopedMixin <|-- Media
```

---

## 🏢 Multi-Tenancy

El sistema implementa multi-tenancy a nivel de aplicación con **aislamiento completo** entre organizaciones.

### Modelo de Aislamiento

```mermaid
graph TB
    subgraph "Tenant A - Organization 1"
        U1[Users]
        M1[Media]
        S1[Subscription]
    end

    subgraph "Tenant B - Organization 2"
        U2[Users]
        M2[Media]
        S2[Subscription]
    end

    subgraph "Shared Infrastructure"
        DB[(PostgreSQL)]
        R[(Redis)]
        S3[S3]
    end

    U1 --> DB
    M1 --> DB
    S1 --> DB
    U2 --> DB
    M2 --> DB
    S2 --> DB

    U1 -.-> R
    U2 -.-> R

    M1 --> S3
    M2 --> S3

    style U1 fill:#3b82f6,color:#fff
    style U2 fill:#10b981,color:#fff
```

### Permisos y Roles (RBAC)

```mermaid
graph LR
    U[User] -->|has many| M[Membership]
    M -->|belongs to| O[Organization]
    M -->|has| R[Role]
    R -->|has many| P[Permission]

    subgraph "Roles predefinidos"
        OWNER[owner]
        ADMIN[admin]
        MEMBER[member]
        VIEWER[viewer]
    end

    subgraph "Permissions"
        P1[organization:read]
        P2[organization:write]
        P3[organization:delete]
        P4[member:invite]
        P5[member:remove]
        P6[billing:manage]
    end

    OWNER --> P1
    OWNER --> P2
    OWNER --> P3
    OWNER --> P4
    OWNER --> P5
    OWNER --> P6

    ADMIN --> P1
    ADMIN --> P2
    ADMIN --> P4

    MEMBER --> P1
    VIEWER --> P1
```

---

## 💳 Sistema de Billing

Soporta múltiples gateways con patrón Adapter:

```mermaid
classDiagram
    class PaymentGateway {
        <<interface>>
        +create_checkout(plan, org) CheckoutSession
        +cancel_subscription(sub_id) bool
        +handle_webhook(payload) WebhookEvent
        +get_subscription(id) SubscriptionInfo
    }

    class StripeAdapter {
        -stripe_client
        +create_checkout()
        +cancel_subscription()
        +handle_webhook()
    }

    class MercadoPagoAdapter {
        -mp_client
        +create_checkout()
        +cancel_subscription()
        +handle_webhook()
    }

    class PolarAdapter {
        -polar_client
        +create_checkout()
        +cancel_subscription()
        +handle_webhook()
    }

    class BillingService {
        -gateway: PaymentGateway
        +change_plan(org_id, plan)
        +get_or_create_subscription()
        +cancel(org_id)
    }

    PaymentGateway <|.. StripeAdapter
    PaymentGateway <|.. MercadoPagoAdapter
    PaymentGateway <|.. PolarAdapter
    BillingService --> PaymentGateway
```

### Flujo de Cambio de Plan

```mermaid
sequenceDiagram
    autonumber
    participant U as Usuario
    participant B as Backend
    participant GW as Payment Gateway
    participant DB as Database
    participant W as Worker ARQ

    U->>B: POST /billing/change-plan
    B->>DB: Verificar permisos
    B->>GW: Crear checkout session
    GW-->>B: Checkout URL
    B-->>U: Redirect a checkout

    U->>GW: Completar pago
    GW->>B: Webhook: subscription.updated
    B->>B: Verificar signature
    B->>DB: Actualizar subscription
    B->>W: Encolar task: send_confirmation_email
    W->>W: Enviar email
    B-->>GW: 200 OK
```

### Planes y Límites

```mermaid
graph TB
    subgraph "Plan Free"
        F1[3 miembros]
        F2[100 MB storage]
        F3[100 API calls/hora]
        F4[$0/mes]
    end

    subgraph "Plan Starter"
        S1[10 miembros]
        S2[1 GB storage]
        S3[1000 API calls/hora]
        S4[$29/mes]
    end

    subgraph "Plan Pro"
        P1[50 miembros]
        P2[10 GB storage]
        P3[10000 API calls/hora]
        P4[$99/mes]
    end

    subgraph "Plan Enterprise"
        E1[Ilimitado]
        E2[100 GB storage]
        E3[Sin rate limit]
        E4[Custom]
    end

    style F4 fill:#94a3b8,color:#fff
    style S4 fill:#3b82f6,color:#fff
    style P4 fill:#8b5cf6,color:#fff
    style E4 fill:#ec4899,color:#fff
```

---

## 🔄 Pipeline de Middleware

Cada request pasa por una cadena de middlewares:

```mermaid
flowchart TD
    REQ[Request HTTP] --> LOG[LoggingMiddleware]
    LOG --> MET[MetricsMiddleware]
    MET --> SEC[SecurityHeadersMiddleware]
    SEC --> RL[RateLimitMiddleware]
    RL --> CORS[CORSMiddleware]
    CORS --> APP[FastAPI App]
    APP --> ROUTE[Route Handler]
    ROUTE --> DEP[Dependencies]
    DEP --> AUTH[Auth Check]
    AUTH --> PERM[Permission Check]
    PERM --> SVC[Service Call]
    SVC --> RESP[Response]
    RESP --> CORS2[CORS Headers]
    CORS2 --> RL2[Rate Limit Headers]
    RL2 --> SEC2[Security Headers]
    SEC2 --> MET2[Metrics update]
    MET2 --> LOG2[Log response]
    LOG2 --> END[Client]

    style LOG fill:#3b82f6,color:#fff
    style MET fill:#8b5cf6,color:#fff
    style SEC fill:#ef4444,color:#fff
    style RL fill:#f59e0b,color:#fff
```

### Rate Limiting Per-Tenant

```mermaid
flowchart LR
    REQ[Request] --> EXTRACT[Extraer org del token]
    EXTRACT --> GETPLAN[Obtener plan de org]
    GETPLAN --> CHECKLIMIT{Rate limit<br/>excedido?}
    CHECKLIMIT -->|No| ALLOW[Permitir request]
    CHECKLIMIT -->|Sí| DENY[429 Too Many Requests]
    ALLOW --> INCR[Incrementar contador Redis]
    INCR --> NEXT[Next middleware]

    style DENY fill:#ef4444,color:#fff
    style ALLOW fill:#10b981,color:#fff
```

---

## 🔌 WebSockets y Broadcasting

Sistema de notificaciones en tiempo real usando canales por modelo:

```mermaid
graph TB
    subgraph "Connection Manager"
        CM[ConnectionManager]
        C1[Client 1]
        C2[Client 2]
        C3[Client 3]
    end

    subgraph "Channels"
        CH1[users channel]
        CH2[organizations channel]
        CH3[media channel]
    end

    subgraph "Services"
        S1[UserService]
        S2[OrgService]
        S3[MediaService]
    end

    C1 -.->|subscribe| CH1
    C2 -.->|subscribe| CH2
    C3 -.->|subscribe| CH3

    S1 -->|broadcast| CH1
    S2 -->|broadcast| CH2
    S3 -->|broadcast| CH3

    CH1 -->|notify| C1
    CH2 -->|notify| C2
    CH3 -->|notify| C3

    CM --- CH1
    CM --- CH2
    CM --- CH3
```

### Flujo de Broadcasting

```mermaid
sequenceDiagram
    autonumber
    participant C1 as Cliente 1
    participant C2 as Cliente 2
    participant WS as WebSocket Manager
    participant S as Service
    participant DB as Database

    C1->>WS: Connect /ws/users
    WS->>WS: Registrar en canal "users"
    C2->>WS: Connect /ws/users
    WS->>WS: Registrar en canal "users"

    Note over C1,C2: Ambos suscritos al canal "users"

    C1->>S: POST /users (crear)
    S->>DB: INSERT
    DB-->>S: User creado
    S->>WS: broadcast("users", "created", data)
    WS->>C1: Event: user_created
    WS->>C2: Event: user_created

    Note over C1,C2: Ambos reciben la notificación
```

---

## ⚙️ Task Queue Asíncrona

ARQ workers procesan tareas en background:

```mermaid
graph LR
    subgraph "Producers"
        R1[Auth Service]
        R2[Billing Service]
        R3[Media Service]
    end

    subgraph "Redis Queue"
        Q[(ARQ Queue)]
    end

    subgraph "Workers"
        W1[Worker 1]
        W2[Worker 2]
        W3[Worker 3]
    end

    subgraph "Tasks"
        T1[send_email]
        T2[process_image]
        T3[send_webhook]
        T4[generate_report]
    end

    R1 -->|enqueue| Q
    R2 -->|enqueue| Q
    R3 -->|enqueue| Q

    Q --> W1
    Q --> W2
    Q --> W3

    W1 --> T1
    W2 --> T2
    W3 --> T3
    W1 --> T4

    style Q fill:#ef4444,color:#fff
```

---

## 📁 Storage y Media

Abstracción sobre S3-compatible storage:

```mermaid
flowchart TD
    U[Usuario] -->|Upload file| R[/media/upload]
    R --> CHECK[Verificar plan limit]
    CHECK --> VALID{Tamaño OK?}
    VALID -->|No| ERR[402 Payment Required]
    VALID -->|Sí| UPLOAD[StorageService.upload]

    UPLOAD --> TYPE{Tipo de storage?}
    TYPE -->|USE_S3=true| S3[S3 Client]
    TYPE -->|USE_S3=false| LOCAL[Local Filesystem]

    S3 --> SAVE[Save to bucket]
    LOCAL --> SAVE2[Save to disk]

    SAVE --> META[Guardar metadata DB]
    SAVE2 --> META
    META --> URL[Generate presigned URL]
    URL --> RESP[Return Media object]

    style ERR fill:#ef4444,color:#fff
    style RESP fill:#10b981,color:#fff
```

### Storage Policies

```mermaid
graph TB
    M[Media Upload Request] --> CHECK[Check policies]

    CHECK --> SIZE{File size<br/>within limit?}
    CHECK --> QUOTA{Org quota<br/>available?}
    CHECK --> TYPE{MIME type<br/>allowed?}

    SIZE -->|Yes| PASS1[✓]
    QUOTA -->|Yes| PASS2[✓]
    TYPE -->|Yes| PASS3[✓]

    SIZE -->|No| FAIL1[✗ Too large]
    QUOTA -->|No| FAIL2[✗ Quota exceeded]
    TYPE -->|No| FAIL3[✗ Type not allowed]

    PASS1 & PASS2 & PASS3 --> UPLOAD[Upload OK]

    style UPLOAD fill:#10b981,color:#fff
    style FAIL1 fill:#ef4444,color:#fff
    style FAIL2 fill:#ef4444,color:#fff
    style FAIL3 fill:#ef4444,color:#fff
```

---

## 🚀 Deployment Architecture

### Producción con Docker Compose

```mermaid
graph TB
    subgraph "Load Balancer"
        LB[Nginx/Traefik]
    end

    subgraph "Application Tier"
        B1[Backend Instance 1]
        B2[Backend Instance 2]
        B3[Backend Instance 3]
    end

    subgraph "Worker Tier"
        W1[ARQ Worker 1]
        W2[ARQ Worker 2]
    end

    subgraph "Data Tier"
        DB_PRIMARY[(PostgreSQL<br/>Primary)]
        DB_REPLICA[(PostgreSQL<br/>Replica)]
        REDIS_PRIMARY[(Redis<br/>Primary)]
        REDIS_REPLICA[(Redis<br/>Replica)]
    end

    subgraph "Storage Tier"
        S3[(S3 Bucket)]
    end

    subgraph "Monitoring"
        PROM[Prometheus]
        GRAF[Grafana]
        SENTRY[Sentry]
    end

    CLIENT[Clients] --> LB
    LB --> B1
    LB --> B2
    LB --> B3

    B1 --> DB_PRIMARY
    B2 --> DB_PRIMARY
    B3 --> DB_PRIMARY

    B1 -.->|read| DB_REPLICA
    B2 -.->|read| DB_REPLICA
    B3 -.->|read| DB_REPLICA

    B1 --> REDIS_PRIMARY
    B2 --> REDIS_PRIMARY
    B3 --> REDIS_PRIMARY

    B1 --> S3
    B2 --> S3
    B3 --> S3

    REDIS_PRIMARY --> W1
    REDIS_PRIMARY --> W2

    B1 -.->|metrics| PROM
    B2 -.->|metrics| PROM
    B3 -.->|metrics| PROM

    PROM --> GRAF

    B1 -.->|errors| SENTRY
    B2 -.->|errors| SENTRY
    B3 -.->|errors| SENTRY

    DB_PRIMARY -.->|replica| DB_REPLICA
    REDIS_PRIMARY -.->|replica| REDIS_REPLICA

    style LB fill:#3b82f6,color:#fff
    style DB_PRIMARY fill:#10b981,color:#fff
    style REDIS_PRIMARY fill:#ef4444,color:#fff
    style S3 fill:#f59e0b,color:#fff
```

### Zero-Downtime Deployment

```mermaid
sequenceDiagram
    autonumber
    participant CI as CI/CD
    participant REG as Registry
    participant LB as Load Balancer
    participant B1 as Backend v1
    participant B2 as Backend v2
    participant HC as Health Check

    CI->>REG: Push nueva imagen
    CI->>B2: Iniciar nueva versión
    B2->>HC: Esperar health check
    HC-->>B2: Healthy
    CI->>LB: Agregar B2 al pool
    LB->>B2: Empezar a rutear tráfico
    CI->>LB: Drenar tráfico de B1
    LB->>B1: No más requests nuevos
    B1->>B1: Completar requests activos
    CI->>B1: Detener B1
    CI->>REG: Deployment completo

    Note over B1,B2: No downtime durante el switch
```

---

## 📊 Observabilidad

### Pipeline de Métricas

```mermaid
graph LR
    subgraph "Backend"
        M[MetricsMiddleware]
        E[/metrics endpoint]
    end

    subgraph "Collection"
        P[Prometheus]
    end

    subgraph "Visualization"
        G[Grafana]
        D1[Dashboard Requests]
        D2[Dashboard Errors]
        D3[Dashboard Performance]
    end

    subgraph "Alerting"
        A[Alertmanager]
        S[Slack]
        PD[PagerDuty]
    end

    M --> E
    E -->|scrape| P
    P --> G
    G --> D1
    G --> D2
    G --> D3
    P --> A
    A --> S
    A --> PD

    style P fill:#f59e0b,color:#fff
    style G fill:#3b82f6,color:#fff
```

### Health Checks

```mermaid
flowchart LR
    HC[/health] --> DB[Check DB]
    HC --> REDIS[Check Redis]
    HC --> S3[Check S3]
    HC --> SMTP[Check SMTP]

    DB --> S1{OK?}
    REDIS --> S2{OK?}
    S3 --> S3C{OK?}
    SMTP --> S4{OK?}

    S1 -->|Yes| R1[✓]
    S2 -->|Yes| R2[✓]
    S3C -->|Yes| R3[✓]
    S4 -->|Yes| R4[✓]

    S1 -->|No| F1[✗]
    S2 -->|No| F2[✗]
    S3C -->|No| F3[✗]
    S4 -->|No| F4[✗]

    R1 & R2 & R3 & R4 --> HEALTHY[200 OK]
    F1 --> UNHEALTHY[503 Unavailable]
    F2 --> UNHEALTHY
    F3 --> UNHEALTHY
    F4 --> UNHEALTHY

    style HEALTHY fill:#10b981,color:#fff
    style UNHEALTHY fill:#ef4444,color:#fff
```

---

## 📂 Estructura de Directorios

```
Seguros-BK/
├── app/
│   ├── config.py              # Settings (Pydantic)
│   ├── database/
│   │   └── connection.py      # SQLModel engine
│   ├── core/
│   │   ├── security.py        # JWT + bcrypt
│   │   ├── dependencies.py    # FastAPI dependencies
│   │   ├── permissions.py     # RBAC
│   │   └── plan_guards.py     # Plan limits
│   ├── models/                # SQLModel models
│   │   ├── user.py
│   │   ├── organization.py
│   │   ├── subscription.py
│   │   ├── api_key.py
│   │   ├── audit_log.py
│   │   └── media.py
│   ├── services/              # Business logic
│   │   ├── base_service.py    # Generic BaseService
│   │   ├── user_service.py
│   │   ├── organization_service.py
│   │   ├── billing/           # Payment adapters
│   │   ├── gdpr_service.py
│   │   └── websocket/         # WS manager
│   ├── routes/                # API endpoints
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── organizations.py
│   │   ├── billing.py
│   │   ├── gdpr.py
│   │   ├── admin.py
│   │   └── setup.py           # First-time setup
│   ├── middleware/            # Custom middleware
│   │   ├── logging.py
│   │   ├── metrics.py
│   │   ├── rate_limit.py
│   │   └── security_headers.py
│   ├── workers/               # ARQ workers
│   │   └── worker_config.py
│   └── utils/
├── admin-ui/                  # SvelteKit admin panel
│   ├── src/
│   │   ├── routes/
│   │   │   ├── +page.svelte         # Dashboard
│   │   │   ├── docs/+page.svelte    # Documentation
│   │   │   └── setup/+page.svelte   # Setup wizard
│   │   └── lib/
│   └── package.json
├── tests/                     # 216 tests
├── alembic/                   # Migrations
├── scripts/                   # Operations scripts
│   ├── backup.sh
│   ├── restore.sh
│   └── db-maintenance.sh
├── monitoring/
│   └── grafana-dashboard.json
├── docs/
│   ├── ARCHITECTURE.md        # Este archivo
│   ├── DEPLOYMENT.md          # Guía de deploy
│   └── OPERATIONS.md          # Operaciones
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── main.py                    # Entry point
```

---

## 🎓 Conceptos Clave para Nuevos Desarrolladores

### 1. **¿Por qué monolito modular en vez de microservicios?**
- Más simple de desarrollar y desplegar
- Mejor para equipos pequeños/medianos
- Fácil refactor a microservicios cuando sea necesario
- Menos complejidad operacional

### 2. **¿Por qué SQLModel en vez de SQLAlchemy puro?**
- Type-safety con Pydantic
- Menos boilerplate (modelos unificados)
- Mejor integración con FastAPI
- Auto-completado en IDEs

### 3. **¿Por qué BaseService genérico?**
- DRY: evita repetir CRUD en cada servicio
- Features transversales (cache, audit, WebSocket) automáticas
- Facilita agregar nuevos modelos
- Type-safety con genéricos

### 4. **¿Por qué Redis para rate limiting?**
- Atómico (INCR + EXPIRE)
- Persistente a nivel de servidor
- Compartido entre instancias (horizontal scaling)
- Fast (in-memory)

### 5. **¿Por qué ARQ en vez de Celery?**
- Nativo async/await (integra bien con FastAPI)
- Menos dependencias
- API más simple
- Suficiente para la mayoría de casos

---

## 🔗 Enlaces Relacionados

- [DEPLOYMENT.md](./DEPLOYMENT.md) - Guía completa de deployment
- [OPERATIONS.md](./OPERATIONS.md) - Operaciones y mantenimiento
- [API Docs](http://localhost:8000/docs) - Swagger UI
- [Admin Docs](http://localhost:8000/admin/docs) - Documentación en admin panel

---

## 📝 Notas Finales

Este backend está diseñado para ser un **template reutilizable**. Al iniciar un nuevo proyecto SaaS:

1. Clonar el repositorio
2. Ejecutar el **Setup Wizard** visual (`/setup`) para configurar variables
3. Personalizar modelos según el dominio del proyecto
4. Agregar nuevas rutas y servicios siguiendo el patrón establecido
5. Los tests, seguridad, monitoring y observability ya están incluidos

**El código está listo para producción desde el día 1.**
