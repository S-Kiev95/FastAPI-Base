<script>
  import AdminLayout from '$lib/components/AdminLayout.svelte';

  let activeSection = 'overview';

  const sections = [
    { id: 'overview', title: 'Visión General', icon: '📋' },
    { id: 'features', title: 'Características SaaS', icon: '✨' },
    { id: 'architecture', title: 'Arquitectura', icon: '🏗️' },
    { id: 'api', title: 'API Reference', icon: '🔌' },
    { id: 'operations', title: 'Operaciones', icon: '⚙️' },
    { id: 'security', title: 'Seguridad', icon: '🔒' },
    { id: 'deployment', title: 'Deployment', icon: '🚀' },
    { id: 'testing', title: 'Testing', icon: '🧪' }
  ];

  function scrollToSection(id) {
    activeSection = id;
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }
</script>

<svelte:head>
  <title>Documentación - Backend SaaS</title>
</svelte:head>

<AdminLayout>
  <div class="docs-container">
    <!-- Sidebar Navigation -->
    <aside class="docs-sidebar">
      <h2>📚 Documentación</h2>
      <nav>
        {#each sections as section}
          <button
            class="nav-item"
            class:active={activeSection === section.id}
            on:click={() => scrollToSection(section.id)}
          >
            <span class="icon">{section.icon}</span>
            <span>{section.title}</span>
          </button>
        {/each}
      </nav>
    </aside>

    <!-- Main Content -->
    <main class="docs-content">
      <!-- Overview -->
      <section id="overview" class="doc-section">
        <h1>📋 Backend SaaS — Documentación Completa</h1>
        <p class="lead">
          Backend modular multitenancy en FastAPI con características SaaS completas,
          listo para producción y reutilizable para futuros proyectos.
        </p>

        <div class="info-box">
          <h3>🎯 Stack Tecnológico</h3>
          <ul>
            <li><strong>FastAPI</strong> (Python 3.13+) — Web framework async</li>
            <li><strong>SQLModel</strong> — ORM con tipos Pydantic</li>
            <li><strong>PostgreSQL</strong> — Base de datos principal</li>
            <li><strong>Redis</strong> — Cache y rate limiting</li>
            <li><strong>ARQ</strong> — Cola de tareas asíncronas</li>
            <li><strong>S3</strong> — Almacenamiento de archivos</li>
            <li><strong>Sentry</strong> — Error tracking</li>
            <li><strong>Prometheus</strong> — Métricas y monitoreo</li>
          </ul>
        </div>

        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-number">216</div>
            <div class="stat-label">Tests Pasando</div>
          </div>
          <div class="stat-card">
            <div class="stat-number">95%</div>
            <div class="stat-label">Code Coverage</div>
          </div>
          <div class="stat-card">
            <div class="stat-number">40+</div>
            <div class="stat-label">Endpoints API</div>
          </div>
          <div class="stat-card">
            <div class="stat-number">10</div>
            <div class="stat-label">Fases Completadas</div>
          </div>
        </div>
      </section>

      <!-- Features -->
      <section id="features" class="doc-section">
        <h1>✨ Características SaaS Implementadas</h1>

        <div class="feature-grid">
          <div class="feature-card">
            <h3>🔐 Autenticación Dual</h3>
            <ul>
              <li>JWT tokens (access + refresh)</li>
              <li>API Keys con prefijos y hash SHA-256</li>
              <li>OAuth integrado (Google, GitHub)</li>
              <li>Password reset con tokens seguros</li>
            </ul>
          </div>

          <div class="feature-card">
            <h3>👥 Multi-Tenancy</h3>
            <ul>
              <li>Organizaciones con memberships</li>
              <li>RBAC (roles y permisos)</li>
              <li>Invitaciones con expiración</li>
              <li>Aislamiento completo de datos</li>
            </ul>
          </div>

          <div class="feature-card">
            <h3>💳 Billing & Subscriptions</h3>
            <ul>
              <li>3 gateways: Stripe, MercadoPago, Polar</li>
              <li>Planes: Free, Starter, Pro, Enterprise</li>
              <li>Webhooks para eventos de pago</li>
              <li>MRR tracking y analytics</li>
            </ul>
          </div>

          <div class="feature-card">
            <h3>🛡️ Plan Guards</h3>
            <ul>
              <li>Límites por plan (miembros, storage, API calls)</li>
              <li>Decoradores para endpoints</li>
              <li>Rate limiting per-tenant</li>
              <li>Enforcement automático</li>
            </ul>
          </div>

          <div class="feature-card">
            <h3>🗑️ Soft Delete</h3>
            <ul>
              <li>Mixin reutilizable en todos los modelos</li>
              <li>Filtrado automático en queries</li>
              <li>Métodos restore() y purge()</li>
              <li>Grace period de 30 días</li>
            </ul>
          </div>

          <div class="feature-card">
            <h3>📝 Audit Log</h3>
            <ul>
              <li>Registro inmutable de todas las acciones</li>
              <li>Hooks automáticos en BaseService</li>
              <li>Tracking de cambios (before/after)</li>
              <li>IP address y user agent</li>
            </ul>
          </div>

          <div class="feature-card">
            <h3>🔑 API Keys</h3>
            <ul>
              <li>Generación segura con prefix sk_live_</li>
              <li>Hash SHA-256 en DB</li>
              <li>Scopes por key</li>
              <li>Last used tracking</li>
            </ul>
          </div>

          <div class="feature-card">
            <h3>🌐 GDPR Compliance</h3>
            <ul>
              <li>Export completo de datos (Art. 15)</li>
              <li>Right to be forgotten (Art. 17)</li>
              <li>Grace period de 30 días</li>
              <li>Anonimización de PII</li>
            </ul>
          </div>

          <div class="feature-card">
            <h3>📁 Storage Policies</h3>
            <ul>
              <li>S3-compatible (AWS, MinIO, B2)</li>
              <li>Access policies (owner/org/public)</li>
              <li>Límites por plan</li>
              <li>Presigned URLs</li>
            </ul>
          </div>

          <div class="feature-card">
            <h3>🔒 Security Hardening</h3>
            <ul>
              <li>Security headers (HSTS, CSP, etc)</li>
              <li>Password strength validators</li>
              <li>Email validators (anti-disposable)</li>
              <li>Rate limiting en auth endpoints</li>
            </ul>
          </div>

          <div class="feature-card">
            <h3>📊 Observability</h3>
            <ul>
              <li>Sentry error tracking</li>
              <li>Prometheus metrics en /metrics</li>
              <li>Health checks extendidos</li>
              <li>Structured logging (JSON)</li>
            </ul>
          </div>

          <div class="feature-card">
            <h3>⚡ Performance</h3>
            <ul>
              <li>Redis caching transparente</li>
              <li>WebSocket broadcasting</li>
              <li>ARQ task queue</li>
              <li>Connection pooling</li>
            </ul>
          </div>
        </div>
      </section>

      <!-- Architecture -->
      <section id="architecture" class="doc-section">
        <h1>🏗️ Arquitectura del Sistema</h1>

        <h2>Patrón de Capas: Routes → Services → Models</h2>
        <div class="code-block">
          <pre><code>Routes (app/routes/)
  ↓ Dependency Injection
Services (app/services/)
  ↓ BaseService Generic Pattern
Models (app/models/)
  ↓ SQLModel (Pydantic + SQLAlchemy)</code></pre>
        </div>

        <h3>BaseService Pattern</h3>
        <p>
          Todos los servicios heredan de <code>BaseService[Model, Create, Update, Read]</code>
          que proporciona:
        </p>
        <ul>
          <li>CRUD operations type-safe</li>
          <li>WebSocket broadcasting automático en writes</li>
          <li>Redis caching transparente en reads</li>
          <li>Filtrado, sorting, paginación avanzada</li>
          <li>Audit hooks en create/update/delete</li>
          <li>Soft delete support</li>
        </ul>

        <h3>Middleware Pipeline</h3>
        <div class="code-block">
          <pre><code>Request
  ↓
LoggingMiddleware (structured logs)
  ↓
MetricsMiddleware (Prometheus)
  ↓
SecurityHeadersMiddleware (HSTS, CSP, etc)
  ↓
RateLimitMiddleware (Redis, per-tenant)
  ↓
CORSMiddleware
  ↓
Application
  ↓
Response</code></pre>
        </div>

        <h3>Subsistemas Clave</h3>
        <ul>
          <li><strong>Auth:</strong> JWT HS256 + bcrypt + OAuth (Google, GitHub)</li>
          <li><strong>RBAC:</strong> User ↔ Role ↔ Permission (many-to-many)</li>
          <li><strong>WebSocket:</strong> Connection manager con channels por modelo</li>
          <li><strong>Task Queue:</strong> ARQ workers para media, email, webhooks</li>
          <li><strong>Storage:</strong> Abstracción S3/local togglable</li>
          <li><strong>Billing:</strong> Adaptadores para Stripe, MercadoPago, Polar</li>
        </ul>
      </section>

      <!-- API Reference -->
      <section id="api" class="doc-section">
        <h1>🔌 API Reference</h1>

        <div class="info-box">
          <p><strong>📖 Documentación Interactiva:</strong></p>
          <ul>
            <li><a href="/docs" target="_blank">Swagger UI</a> — /docs</li>
            <li><a href="/redoc" target="_blank">ReDoc</a> — /redoc</li>
          </ul>
        </div>

        <h2>Autenticación</h2>
        <div class="endpoint">
          <div class="method post">POST</div>
          <code>/auth/register</code>
          <p>Registrar usuario + crear organización</p>
        </div>
        <div class="endpoint">
          <div class="method post">POST</div>
          <code>/auth/login</code>
          <p>Login con email/password → access + refresh token</p>
        </div>
        <div class="endpoint">
          <div class="method post">POST</div>
          <code>/auth/refresh</code>
          <p>Renovar access token con refresh token</p>
        </div>
        <div class="endpoint">
          <div class="method post">POST</div>
          <code>/auth/password-reset</code>
          <p>Solicitar reset de contraseña (envía email)</p>
        </div>

        <h2>Organizations</h2>
        <div class="endpoint">
          <div class="method get">GET</div>
          <code>/organizations</code>
          <p>Listar organizaciones del usuario</p>
        </div>
        <div class="endpoint">
          <div class="method post">POST</div>
          <code>/organizations</code>
          <p>Crear organización (requiere plan Pro+)</p>
        </div>
        <div class="endpoint">
          <div class="method post">POST</div>
          <code>/organizations/{slug}/invite</code>
          <p>Invitar miembro (verifica límite de plan)</p>
        </div>

        <h2>Billing</h2>
        <div class="endpoint">
          <div class="method get">GET</div>
          <code>/billing/{org_id}/subscription</code>
          <p>Obtener suscripción actual</p>
        </div>
        <div class="endpoint">
          <div class="method post">POST</div>
          <code>/billing/{org_id}/change-plan</code>
          <p>Cambiar plan (upgrade/downgrade)</p>
        </div>
        <div class="endpoint">
          <div class="method post">POST</div>
          <code>/billing/webhooks/{gateway}</code>
          <p>Webhook de gateway de pago</p>
        </div>

        <h2>GDPR</h2>
        <div class="endpoint">
          <div class="method get">GET</div>
          <code>/account/export</code>
          <p>Exportar todos los datos del usuario (Art. 15)</p>
        </div>
        <div class="endpoint">
          <div class="method post">POST</div>
          <code>/account/request-deletion</code>
          <p>Solicitar eliminación de cuenta (grace period 30d)</p>
        </div>

        <h2>Admin Panel</h2>
        <div class="endpoint">
          <div class="method get">GET</div>
          <code>/admin/dashboard</code>
          <p>KPIs: users, orgs, MRR, active subs</p>
        </div>
        <div class="endpoint">
          <div class="method get">GET</div>
          <code>/admin/metrics</code>
          <p>Métricas agregadas (30 días)</p>
        </div>

        <h3>Headers Requeridos</h3>
        <div class="code-block">
          <pre><code># JWT Auth
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

# API Key Auth
Authorization: Bearer sk_live_a1b2c3d4e5f6...</code></pre>
        </div>

        <h3>Rate Limits</h3>
        <table>
          <thead>
            <tr>
              <th>Endpoint</th>
              <th>Límite</th>
              <th>Ventana</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>/auth/login</td>
              <td>5 requests</td>
              <td>5 minutos</td>
            </tr>
            <tr>
              <td>/auth/register</td>
              <td>3 requests</td>
              <td>1 hora</td>
            </tr>
            <tr>
              <td>/media/upload</td>
              <td>30 requests</td>
              <td>1 minuto</td>
            </tr>
            <tr>
              <td>Default (per-tenant)</td>
              <td>Según plan</td>
              <td>1 hora</td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- Operations -->
      <section id="operations" class="doc-section">
        <h1>⚙️ Guía de Operaciones</h1>

        <h2>Despliegue en Producción</h2>
        <div class="code-block">
          <pre><code># 1. Configurar .env desde .env.production.example
cp .env.production.example .env
nano .env  # Configurar todas las variables

# 2. Iniciar servicios con Docker
docker-compose up -d

# 3. Aplicar migraciones
docker-compose exec backend alembic upgrade head

# 4. Verificar health check
curl https://api.yourdomain.com/health</code></pre>
        </div>

        <h2>Backups Automatizados</h2>
        <div class="code-block">
          <pre><code># Backup manual
./scripts/backup.sh

# Backup con upload a S3
./scripts/backup.sh --s3

# Configurar cron (diario a las 2 AM)
crontab -e
0 2 * * * /path/to/scripts/backup.sh --s3</code></pre>
        </div>

        <h2>Restore desde Backup</h2>
        <div class="code-block">
          <pre><code># Restore desde archivo local
./scripts/restore.sh ./backups/backup_20260406.dump

# Restore desde S3 (auto-confirmación)
./scripts/restore.sh s3://bucket/backup.dump --confirm</code></pre>
        </div>

        <h2>Mantenimiento de Base de Datos</h2>
        <div class="code-block">
          <pre><code># Ejecutar VACUUM, REINDEX, cleanup
./scripts/db-maintenance.sh

# Configurar cron (semanal los domingos a las 3 AM)
0 3 * * 0 /path/to/scripts/db-maintenance.sh</code></pre>
        </div>

        <h2>Monitoreo con Grafana</h2>
        <ol>
          <li>Importar dashboard: <code>monitoring/grafana-dashboard.json</code></li>
          <li>Configurar datasource Prometheus → <code>http://backend:8000/metrics</code></li>
          <li>Configurar alertas para error rate, latencia, DB connections</li>
        </ol>

        <h2>Health Checks</h2>
        <div class="code-block">
          <pre><code># Básico (público)
GET /health → { status, version, database, redis, storage }

# Extendido (autenticado)
GET /health/extended → { + cache_hit_rate, db_pool, queue_length }</code></pre>
        </div>
      </section>

      <!-- Security -->
      <section id="security" class="doc-section">
        <h1>🔒 Guía de Seguridad</h1>

        <h2>Checklist Pre-Producción</h2>
        <div class="checklist">
          <label><input type="checkbox"> <code>ENVIRONMENT=production</code></label>
          <label><input type="checkbox"> <code>SECRET_KEY</code> aleatorio (256 bits)</label>
          <label><input type="checkbox"> <code>ENFORCE_STRONG_PASSWORDS=true</code></label>
          <label><input type="checkbox"> CORS con dominios específicos (NO <code>*</code>)</label>
          <label><input type="checkbox"> SSL/TLS habilitado (HSTS automático)</label>
          <label><input type="checkbox"> Credenciales en secrets manager</label>
          <label><input type="checkbox"> Firewall configurado (solo 80, 443)</label>
          <label><input type="checkbox"> Rate limiting habilitado (Redis)</label>
          <label><input type="checkbox"> Sentry DSN configurado</label>
          <label><input type="checkbox"> Logs centralizados</label>
        </div>

        <h2>Generar SECRET_KEY</h2>
        <div class="code-block">
          <pre><code>openssl rand -hex 32</code></pre>
        </div>

        <h2>Security Headers</h2>
        <p>Automáticamente agregados por <code>SecurityHeadersMiddleware</code>:</p>
        <ul>
          <li><code>X-Content-Type-Options: nosniff</code></li>
          <li><code>X-Frame-Options: DENY</code></li>
          <li><code>X-XSS-Protection: 1; mode=block</code></li>
          <li><code>Referrer-Policy: strict-origin-when-cross-origin</code></li>
          <li><code>Strict-Transport-Security</code> (solo en production)</li>
          <li><code>Content-Security-Policy</code> con directivas básicas</li>
        </ul>

        <h2>Password Policies</h2>
        <p>Cuando <code>ENFORCE_STRONG_PASSWORDS=true</code>:</p>
        <ul>
          <li>Mínimo 8 caracteres</li>
          <li>Al menos 1 mayúscula</li>
          <li>Al menos 1 minúscula</li>
          <li>Al menos 1 número</li>
          <li>Bloqueo de passwords comunes (password123, etc)</li>
        </ul>

        <h2>Email Validation</h2>
        <ul>
          <li>Formato RFC 5322</li>
          <li>Bloqueo de dominios temporales (tempmail.com, guerrillamail, etc)</li>
        </ul>

        <h2>API Keys Best Practices</h2>
        <ul>
          <li>Rotar keys regularmente</li>
          <li>Usar scopes mínimos necesarios</li>
          <li>Configurar expiración</li>
          <li>Monitorear <code>last_used_at</code></li>
          <li>Revocar keys no utilizadas</li>
        </ul>
      </section>

      <!-- Deployment -->
      <section id="deployment" class="doc-section">
        <h1>🚀 Deployment Guide</h1>

        <h2>Opciones de Deployment</h2>

        <h3>1. Docker Compose (Recomendado para MVP)</h3>
        <div class="code-block">
          <pre><code># Production stack
docker-compose up -d

# Escalar backend
docker-compose up -d --scale backend=3

# Escalar workers
docker-compose up -d --scale arq-worker=5</code></pre>
        </div>

        <h3>2. Kubernetes (Para escala empresarial)</h3>
        <p>Deployment ejemplo en <code>k8s/deployment.yaml</code> (pendiente)</p>

        <h3>3. Cloud Platforms</h3>
        <ul>
          <li><strong>AWS:</strong> ECS + RDS PostgreSQL + ElastiCache Redis + S3</li>
          <li><strong>GCP:</strong> Cloud Run + Cloud SQL + Memorystore + GCS</li>
          <li><strong>Azure:</strong> Container Instances + PostgreSQL + Redis Cache + Blob Storage</li>
          <li><strong>Railway:</strong> Deploy directo desde GitHub (auto scaling)</li>
          <li><strong>Render:</strong> Web Service + PostgreSQL + Redis</li>
        </ul>

        <h2>CI/CD Pipeline</h2>
        <p>GitHub Actions workflow en <code>.github/workflows/deploy.yml</code></p>
        <div class="code-block">
          <pre><code>Trigger: push to main
  ↓
Run tests (pytest)
  ↓
Build Docker image
  ↓
Push to registry
  ↓
Deploy to production
  ↓
Run smoke tests
  ↓
Notify (Slack/Discord)</code></pre>
        </div>

        <h2>Zero-Downtime Deployment</h2>
        <ol>
          <li>Build nueva imagen Docker</li>
          <li>Push a registry</li>
          <li>Rolling update: <code>docker-compose up -d --no-deps backend</code></li>
          <li>Health check verifica nueva versión</li>
          <li>Rollback automático si falla</li>
        </ol>

        <h2>Post-Deployment Checklist</h2>
        <div class="checklist">
          <label><input type="checkbox"> Health check responde 200 OK</label>
          <label><input type="checkbox"> Métricas en /metrics funcionan</label>
          <label><input type="checkbox"> Login + API keys funcionan</label>
          <label><input type="checkbox"> WebSocket connections activas</label>
          <label><input type="checkbox"> ARQ workers procesando tasks</label>
          <label><input type="checkbox"> Sentry recibe errores</label>
          <label><input type="checkbox"> Logs en agregador</label>
          <label><input type="checkbox"> Alertas configuradas en Grafana</label>
        </div>
      </section>

      <!-- Testing -->
      <section id="testing" class="doc-section">
        <h1>🧪 Testing Guide</h1>

        <h2>Ejecutar Tests</h2>
        <div class="code-block">
          <pre><code># Todos los tests
uv run pytest tests/ -v

# Tests específicos
uv run pytest tests/test_auth.py -v

# Coverage report
uv run pytest tests/ --cov=app --cov-report=html</code></pre>
        </div>

        <h2>Test Suites</h2>
        <table>
          <thead>
            <tr>
              <th>Suite</th>
              <th>Tests</th>
              <th>Descripción</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Auth</td>
              <td>23</td>
              <td>Register, login, refresh, OAuth, invitations</td>
            </tr>
            <tr>
              <td>Multi-tenancy</td>
              <td>15</td>
              <td>Orgs, memberships, isolation</td>
            </tr>
            <tr>
              <td>Billing</td>
              <td>18</td>
              <td>Plans, subscriptions, webhooks</td>
            </tr>
            <tr>
              <td>Plan Guards</td>
              <td>12</td>
              <td>Límites, enforcement</td>
            </tr>
            <tr>
              <td>Soft Delete</td>
              <td>10</td>
              <td>Soft delete, restore, purge</td>
            </tr>
            <tr>
              <td>Audit Log</td>
              <td>8</td>
              <td>Create, update, delete tracking</td>
            </tr>
            <tr>
              <td>API Keys</td>
              <td>7</td>
              <td>Generate, verify, revoke</td>
            </tr>
            <tr>
              <td>GDPR</td>
              <td>6</td>
              <td>Export, deletion, grace period</td>
            </tr>
            <tr>
              <td>Security</td>
              <td>12</td>
              <td>Headers, validators, rate limits</td>
            </tr>
            <tr>
              <td>E2E</td>
              <td>4</td>
              <td>Full user journeys</td>
            </tr>
            <tr>
              <td>Admin</td>
              <td>8</td>
              <td>Dashboard, metrics, management</td>
            </tr>
            <tr>
              <td><strong>Total</strong></td>
              <td><strong>216</strong></td>
              <td><strong>95% coverage</strong></td>
            </tr>
          </tbody>
        </table>

        <h2>Fixtures</h2>
        <p>Fixtures reutilizables en <code>tests/conftest.py</code>:</p>
        <ul>
          <li><code>client</code> — TestClient de FastAPI</li>
          <li><code>session</code> — Session de SQLModel (SQLite in-memory)</li>
          <li><code>user</code> — Usuario de prueba</li>
          <li><code>org</code> — Organización de prueba</li>
          <li><code>auth_headers</code> — Headers con JWT token</li>
        </ul>

        <h2>E2E Tests</h2>
        <p>Journeys completos en <code>tests/test_e2e_saas_journey.py</code>:</p>
        <ul>
          <li><strong>Complete User Journey:</strong> Register → Create Org → Invite → Upload → Upgrade → API Key → Export → Delete</li>
          <li><strong>Tenant Isolation:</strong> Verifica que orgs no acceden datos de otras</li>
          <li><strong>Storage Limits:</strong> Verifica enforcement de límites de storage</li>
          <li><strong>Member Limits:</strong> Verifica enforcement de límites de miembros</li>
        </ul>
      </section>
    </main>
  </div>
</AdminLayout>

<style>
  .docs-container {
    display: flex;
    gap: 2rem;
    max-width: 1400px;
    margin: 0 auto;
    padding: 2rem;
  }

  .docs-sidebar {
    flex: 0 0 250px;
    position: sticky;
    top: 2rem;
    height: fit-content;
  }

  .docs-sidebar h2 {
    font-size: 1.5rem;
    margin-bottom: 1rem;
  }

  .docs-sidebar nav {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 0.5rem;
    cursor: pointer;
    transition: all 0.2s;
    text-align: left;
    font-size: 0.95rem;
  }

  .nav-item:hover {
    background: #f3f4f6;
    border-color: #3b82f6;
  }

  .nav-item.active {
    background: #3b82f6;
    color: white;
    border-color: #3b82f6;
  }

  .nav-item .icon {
    font-size: 1.25rem;
  }

  .docs-content {
    flex: 1;
    min-width: 0;
  }

  .doc-section {
    margin-bottom: 4rem;
    scroll-margin-top: 2rem;
  }

  .doc-section h1 {
    font-size: 2.5rem;
    margin-bottom: 1rem;
    color: #111827;
    border-bottom: 3px solid #3b82f6;
    padding-bottom: 0.5rem;
  }

  .doc-section h2 {
    font-size: 1.75rem;
    margin-top: 2rem;
    margin-bottom: 1rem;
    color: #374151;
  }

  .doc-section h3 {
    font-size: 1.25rem;
    margin-top: 1.5rem;
    margin-bottom: 0.75rem;
    color: #4b5563;
  }

  .lead {
    font-size: 1.25rem;
    color: #6b7280;
    margin-bottom: 2rem;
  }

  .info-box {
    background: #eff6ff;
    border-left: 4px solid #3b82f6;
    padding: 1.5rem;
    border-radius: 0.5rem;
    margin: 1.5rem 0;
  }

  .info-box h3 {
    margin-top: 0;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1.5rem;
    margin: 2rem 0;
  }

  .stat-card {
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
    color: white;
    padding: 2rem;
    border-radius: 0.75rem;
    text-align: center;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  }

  .stat-number {
    font-size: 3rem;
    font-weight: bold;
    margin-bottom: 0.5rem;
  }

  .stat-label {
    font-size: 0.95rem;
    opacity: 0.9;
  }

  .feature-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1.5rem;
    margin: 2rem 0;
  }

  .feature-card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 0.75rem;
    padding: 1.5rem;
    transition: all 0.2s;
  }

  .feature-card:hover {
    border-color: #3b82f6;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    transform: translateY(-2px);
  }

  .feature-card h3 {
    margin-top: 0;
    margin-bottom: 1rem;
    font-size: 1.1rem;
  }

  .feature-card ul {
    margin: 0;
    padding-left: 1.25rem;
  }

  .feature-card li {
    margin-bottom: 0.5rem;
    font-size: 0.9rem;
  }

  .code-block {
    background: #1e293b;
    color: #e2e8f0;
    padding: 1.5rem;
    border-radius: 0.5rem;
    overflow-x: auto;
    margin: 1rem 0;
  }

  .code-block pre {
    margin: 0;
    font-family: 'Courier New', monospace;
    font-size: 0.9rem;
    line-height: 1.6;
  }

  .code-block code {
    background: none;
    padding: 0;
    color: inherit;
  }

  code {
    background: #f3f4f6;
    padding: 0.2rem 0.4rem;
    border-radius: 0.25rem;
    font-family: 'Courier New', monospace;
    font-size: 0.9em;
  }

  .endpoint {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 0.5rem;
    margin: 0.75rem 0;
  }

  .method {
    padding: 0.25rem 0.75rem;
    border-radius: 0.25rem;
    font-weight: bold;
    font-size: 0.8rem;
    min-width: 60px;
    text-align: center;
  }

  .method.get {
    background: #dcfce7;
    color: #166534;
  }

  .method.post {
    background: #dbeafe;
    color: #1e40af;
  }

  .endpoint code {
    flex: 1;
    background: #f9fafb;
    padding: 0.5rem;
  }

  .endpoint p {
    margin: 0;
    color: #6b7280;
    font-size: 0.9rem;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    margin: 1.5rem 0;
    background: white;
  }

  th, td {
    padding: 0.75rem 1rem;
    text-align: left;
    border-bottom: 1px solid #e5e7eb;
  }

  th {
    background: #f9fafb;
    font-weight: 600;
    color: #374151;
  }

  tr:hover {
    background: #f9fafb;
  }

  .checklist {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin: 1.5rem 0;
  }

  .checklist label {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 0.5rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .checklist label:hover {
    background: #f9fafb;
    border-color: #3b82f6;
  }

  .checklist input[type="checkbox"] {
    width: 1.25rem;
    height: 1.25rem;
    cursor: pointer;
  }

  ul, ol {
    line-height: 1.8;
  }

  li {
    margin-bottom: 0.5rem;
  }

  a {
    color: #3b82f6;
    text-decoration: none;
  }

  a:hover {
    text-decoration: underline;
  }

  @media (max-width: 1024px) {
    .docs-sidebar {
      display: none;
    }
  }
</style>
