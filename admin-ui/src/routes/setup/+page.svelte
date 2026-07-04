<script>
  import { onMount } from 'svelte';

  // ============================================================================
  // Estado del wizard
  // ============================================================================
  let currentStep = 0;
  let loading = false;
  let setupStatus = null;
  let alreadyConfigured = false;

  const steps = [
    { id: 'welcome', title: 'Bienvenida', icon: '👋', required: false, skippable: false },
    { id: 'database', title: 'Base de Datos', icon: '🗄️', required: true, skippable: false },
    { id: 'security', title: 'Seguridad', icon: '🔐', required: true, skippable: false },
    { id: 'redis', title: 'Redis (Cache)', icon: '⚡', required: false, skippable: true },
    { id: 'storage', title: 'Storage (S3)', icon: '📦', required: false, skippable: true },
    { id: 'email', title: 'Email (SMTP)', icon: '📧', required: false, skippable: true },
    { id: 'payment', title: 'Pagos', icon: '💳', required: false, skippable: true },
    { id: 'observability', title: 'Monitoreo', icon: '📊', required: false, skippable: true },
    { id: 'admin', title: 'Admin User', icon: '👤', required: true, skippable: false },
    { id: 'review', title: 'Revisión', icon: '✅', required: true, skippable: false }
  ];

  // ============================================================================
  // Datos de configuración
  // ============================================================================
  let config = {
    environment: 'production',

    // Database
    database_url: 'postgresql://postgres:password@localhost:5432/myapp',

    // Security
    secret_key: '',
    enforce_strong_passwords: true,
    cors_origins: '*',

    // Redis
    redis_enabled: true,
    redis_host: 'localhost',
    redis_port: 6379,
    redis_password: '',

    // Storage
    use_s3: false,
    s3_bucket_name: '',
    s3_region: 'us-east-1',
    s3_access_key: '',
    s3_secret_key: '',
    s3_endpoint_url: '',

    // SMTP
    smtp_host: '',
    smtp_port: 587,
    smtp_user: '',
    smtp_password: '',
    smtp_from_email: '',
    smtp_use_tls: true,

    // Payment
    active_payment_gateway: '',
    stripe_secret_key: '',
    stripe_webhook_secret: '',

    // Observability
    sentry_dsn: '',

    // Admin
    admin_email: '',
    admin_password: '',
    admin_name: 'System Admin'
  };

  // Estado de validaciones
  let validations = {
    database: null,
    redis: null,
    s3: null,
    smtp: null,
    stripe: null
  };

  // ============================================================================
  // Lifecycle
  // ============================================================================
  onMount(async () => {
    try {
      const res = await fetch('/setup/status');
      setupStatus = await res.json();
      alreadyConfigured = setupStatus.configured;
    } catch (e) {
      console.error('Error fetching setup status:', e);
    }

    // Generar SECRET_KEY automáticamente
    try {
      const res = await fetch('/setup/generate-secret-key');
      const data = await res.json();
      config.secret_key = data.secret_key;
    } catch (e) {
      console.error('Error generating secret key:', e);
    }
  });

  // ============================================================================
  // Navegación
  // ============================================================================
  function nextStep() {
    if (currentStep < steps.length - 1) {
      currentStep++;
    }
  }

  function prevStep() {
    if (currentStep > 0) {
      currentStep--;
    }
  }

  function skipStep() {
    const step = steps[currentStep];
    // Resetear config del step si es skippable
    if (step.id === 'redis') config.redis_enabled = false;
    if (step.id === 'storage') config.use_s3 = false;
    if (step.id === 'email') {
      config.smtp_host = '';
      config.smtp_user = '';
      config.smtp_password = '';
      config.smtp_from_email = '';
    }
    if (step.id === 'payment') {
      config.active_payment_gateway = '';
      config.stripe_secret_key = '';
    }
    if (step.id === 'observability') config.sentry_dsn = '';
    nextStep();
  }

  // ============================================================================
  // Validaciones
  // ============================================================================
  async function validateDatabase() {
    loading = true;
    validations.database = null;
    try {
      const res = await fetch('/setup/validate/database', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ database_url: config.database_url })
      });
      validations.database = await res.json();
    } catch (e) {
      validations.database = {
        success: false,
        message: 'Error de red: ' + e.message
      };
    }
    loading = false;
  }

  async function validateRedis() {
    loading = true;
    validations.redis = null;
    try {
      const res = await fetch('/setup/validate/redis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          redis_host: config.redis_host,
          redis_port: config.redis_port,
          redis_password: config.redis_password || null,
          redis_db: 0
        })
      });
      validations.redis = await res.json();
    } catch (e) {
      validations.redis = {
        success: false,
        message: 'Error de red: ' + e.message
      };
    }
    loading = false;
  }

  async function validateS3() {
    loading = true;
    validations.s3 = null;
    try {
      const res = await fetch('/setup/validate/s3', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          s3_bucket_name: config.s3_bucket_name,
          s3_region: config.s3_region,
          s3_access_key: config.s3_access_key,
          s3_secret_key: config.s3_secret_key,
          s3_endpoint_url: config.s3_endpoint_url || null
        })
      });
      validations.s3 = await res.json();
    } catch (e) {
      validations.s3 = {
        success: false,
        message: 'Error de red: ' + e.message
      };
    }
    loading = false;
  }

  async function validateSmtp() {
    loading = true;
    validations.smtp = null;
    try {
      const res = await fetch('/setup/validate/smtp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          smtp_host: config.smtp_host,
          smtp_port: config.smtp_port,
          smtp_user: config.smtp_user,
          smtp_password: config.smtp_password,
          smtp_from_email: config.smtp_from_email,
          smtp_use_tls: config.smtp_use_tls
        })
      });
      validations.smtp = await res.json();
    } catch (e) {
      validations.smtp = {
        success: false,
        message: 'Error de red: ' + e.message
      };
    }
    loading = false;
  }

  async function validateStripe() {
    loading = true;
    validations.stripe = null;
    try {
      const res = await fetch('/setup/validate/stripe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stripe_secret_key: config.stripe_secret_key,
          stripe_webhook_secret: config.stripe_webhook_secret || null
        })
      });
      validations.stripe = await res.json();
    } catch (e) {
      validations.stripe = {
        success: false,
        message: 'Error de red: ' + e.message
      };
    }
    loading = false;
  }

  async function generateSecretKey() {
    try {
      const res = await fetch('/setup/generate-secret-key');
      const data = await res.json();
      config.secret_key = data.secret_key;
    } catch (e) {
      alert('Error generando secret key: ' + e.message);
    }
  }

  // ============================================================================
  // Finalizar setup
  // ============================================================================
  let saveResult = null;

  async function saveConfiguration() {
    loading = true;
    saveResult = null;

    try {
      const res = await fetch('/setup/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      saveResult = await res.json();
    } catch (e) {
      saveResult = {
        success: false,
        message: 'Error guardando: ' + e.message
      };
    }
    loading = false;
  }

  // ============================================================================
  // Helpers
  // ============================================================================
  function canAdvance() {
    const step = steps[currentStep];
    if (step.id === 'database') return validations.database?.success;
    if (step.id === 'security') return config.secret_key && config.secret_key.length >= 32;
    if (step.id === 'redis' && config.redis_enabled) return validations.redis?.success;
    if (step.id === 'storage' && config.use_s3) return validations.s3?.success;
    if (step.id === 'email' && config.smtp_host) return validations.smtp?.success;
    if (step.id === 'payment' && config.stripe_secret_key) return validations.stripe?.success;
    if (step.id === 'admin') {
      return config.admin_email && config.admin_password && config.admin_password.length >= 8;
    }
    return true;
  }
</script>

<svelte:head>
  <title>Setup Wizard - Backend SaaS</title>
</svelte:head>

{#if alreadyConfigured}
  <div class="container">
    <div class="card alert">
      <h1>⚠️ Sistema ya configurado</h1>
      <p>El sistema ya está configurado. Para reconfigurarlo, elimina el archivo <code>.env</code> y reinicia el backend.</p>
      <a href="/admin" class="btn">Ir al Admin Panel</a>
    </div>
  </div>
{:else}
  <div class="container">
    <div class="wizard-header">
      <h1>🚀 Setup Wizard</h1>
      <p>Configura tu backend SaaS paso a paso</p>
    </div>

    <!-- Progress Bar -->
    <div class="progress-bar">
      {#each steps as step, i}
        <div class="progress-step" class:active={i === currentStep} class:completed={i < currentStep}>
          <div class="step-circle">
            {#if i < currentStep}✓{:else}{step.icon}{/if}
          </div>
          <div class="step-label">{step.title}</div>
        </div>
      {/each}
    </div>

    <div class="wizard-content">
      <!-- ======================================================================== -->
      <!-- Step 0: Welcome -->
      <!-- ======================================================================== -->
      {#if currentStep === 0}
        <div class="step welcome">
          <h2>👋 Bienvenido al Setup Wizard</h2>
          <p class="lead">
            Este asistente te guiará a través de la configuración de tu backend SaaS.
            El proceso toma aproximadamente 5-10 minutos.
          </p>

          <div class="info-grid">
            <div class="info-card">
              <h3>🎯 Lo que configuraremos</h3>
              <ul>
                <li><strong>Obligatorio:</strong> Base de datos, Seguridad, Admin</li>
                <li><strong>Opcional:</strong> Redis, S3, SMTP, Stripe, Sentry</li>
              </ul>
            </div>

            <div class="info-card">
              <h3>✨ Características</h3>
              <ul>
                <li>Validación automática de cada config</li>
                <li>Generación segura de SECRET_KEY</li>
                <li>Posibilidad de omitir pasos opcionales</li>
                <li>Guardado automático en archivo <code>.env</code></li>
              </ul>
            </div>
          </div>

          <div class="environment-selector">
            <label>Entorno de despliegue:</label>
            <div class="radio-group">
              <label class="radio">
                <input type="radio" bind:group={config.environment} value="development" />
                <span>Development</span>
              </label>
              <label class="radio">
                <input type="radio" bind:group={config.environment} value="staging" />
                <span>Staging</span>
              </label>
              <label class="radio">
                <input type="radio" bind:group={config.environment} value="production" />
                <span>Production</span>
              </label>
            </div>
          </div>
        </div>
      {/if}

      <!-- ======================================================================== -->
      <!-- Step 1: Database -->
      <!-- ======================================================================== -->
      {#if currentStep === 1}
        <div class="step">
          <h2>🗄️ Configuración de Base de Datos</h2>
          <p class="lead">PostgreSQL es requerido. Se recomienda tener la extensión <code>pgvector</code> instalada.</p>

          <div class="badge badge-required">Obligatorio</div>

          <div class="form-group">
            <label>
              DATABASE_URL
              <span class="required">*</span>
            </label>
            <input
              type="text"
              bind:value={config.database_url}
              placeholder="postgresql://user:password@host:5432/dbname"
              class="input"
            />
            <small>Formato: <code>postgresql://usuario:contraseña@host:puerto/basededatos</code></small>
          </div>

          <button
            class="btn btn-validate"
            on:click={validateDatabase}
            disabled={loading || !config.database_url}
          >
            {#if loading}⏳ Validando...{:else}🔍 Validar Conexión{/if}
          </button>

          {#if validations.database}
            <div class="validation-result" class:success={validations.database.success} class:error={!validations.database.success}>
              <h4>{validations.database.success ? '✅' : '❌'} {validations.database.message}</h4>

              {#if validations.database.details}
                <div class="details">
                  {#if validations.database.details.postgresql_version}
                    <div class="detail-row">
                      <span>PostgreSQL:</span>
                      <strong>{validations.database.details.postgresql_version}</strong>
                    </div>
                  {/if}
                  {#if validations.database.details.pgvector_available !== undefined}
                    <div class="detail-row">
                      <span>pgvector disponible:</span>
                      <strong class:yes={validations.database.details.pgvector_available} class:no={!validations.database.details.pgvector_available}>
                        {validations.database.details.pgvector_available ? '✓ Sí' : '✗ No'}
                      </strong>
                    </div>
                  {/if}
                  {#if validations.database.details.pgvector_installed !== undefined}
                    <div class="detail-row">
                      <span>pgvector instalado:</span>
                      <strong class:yes={validations.database.details.pgvector_installed} class:no={!validations.database.details.pgvector_installed}>
                        {validations.database.details.pgvector_installed ? '✓ Sí' : '✗ No (ejecuta: CREATE EXTENSION vector;)'}
                      </strong>
                    </div>
                  {/if}
                  {#if validations.database.details.can_create_tables !== undefined}
                    <div class="detail-row">
                      <span>Permisos de creación:</span>
                      <strong class:yes={validations.database.details.can_create_tables} class:no={!validations.database.details.can_create_tables}>
                        {validations.database.details.can_create_tables ? '✓ Sí' : '✗ No'}
                      </strong>
                    </div>
                  {/if}
                </div>
              {/if}

              {#if validations.database.warnings && validations.database.warnings.length > 0}
                <div class="warnings">
                  <h5>⚠️ Advertencias:</h5>
                  <ul>
                    {#each validations.database.warnings as warning}
                      <li>{warning}</li>
                    {/each}
                  </ul>
                </div>
              {/if}
            </div>
          {/if}
        </div>
      {/if}

      <!-- ======================================================================== -->
      <!-- Step 2: Security -->
      <!-- ======================================================================== -->
      {#if currentStep === 2}
        <div class="step">
          <h2>🔐 Configuración de Seguridad</h2>
          <p class="lead">Configura la clave secreta para firmar JWT tokens y políticas de seguridad.</p>

          <div class="badge badge-required">Obligatorio</div>

          <div class="form-group">
            <label>
              SECRET_KEY
              <span class="required">*</span>
            </label>
            <div class="input-with-button">
              <input
                type="text"
                bind:value={config.secret_key}
                placeholder="Se generará automáticamente..."
                class="input mono"
              />
              <button class="btn btn-small" on:click={generateSecretKey}>🎲 Generar</button>
            </div>
            <small>Debe tener al menos 32 caracteres. Se ha generado una clave segura automáticamente.</small>
          </div>

          <div class="form-group">
            <label class="checkbox">
              <input type="checkbox" bind:checked={config.enforce_strong_passwords} />
              <span>Requerir contraseñas fuertes (min 8 chars, mayúscula, número)</span>
            </label>
            <small>Recomendado para producción</small>
          </div>

          <div class="form-group">
            <label>
              CORS_ORIGINS
            </label>
            <input
              type="text"
              bind:value={config.cors_origins}
              placeholder="https://yourdomain.com,https://app.yourdomain.com"
              class="input"
            />
            <small>Dominios permitidos separados por coma. Usa <code>*</code> solo para desarrollo.</small>
          </div>

          {#if config.environment === 'production' && config.cors_origins === '*'}
            <div class="warning-box">
              ⚠️ Usar <code>*</code> en CORS_ORIGINS en producción es inseguro. Especifica dominios concretos.
            </div>
          {/if}
        </div>
      {/if}

      <!-- ======================================================================== -->
      <!-- Step 3: Redis -->
      <!-- ======================================================================== -->
      {#if currentStep === 3}
        <div class="step">
          <h2>⚡ Redis (Cache & Rate Limiting)</h2>
          <p class="lead">Redis habilita caching, rate limiting per-tenant y notificaciones de tareas.</p>

          <div class="badge badge-optional">Opcional pero recomendado</div>

          <div class="form-group">
            <label class="checkbox">
              <input type="checkbox" bind:checked={config.redis_enabled} />
              <span>Habilitar Redis</span>
            </label>
          </div>

          {#if config.redis_enabled}
            <div class="form-group">
              <label>REDIS_HOST</label>
              <input type="text" bind:value={config.redis_host} class="input" />
            </div>

            <div class="form-group">
              <label>REDIS_PORT</label>
              <input type="number" bind:value={config.redis_port} class="input" />
            </div>

            <div class="form-group">
              <label>REDIS_PASSWORD <small>(opcional)</small></label>
              <input type="password" bind:value={config.redis_password} class="input" />
            </div>

            <button class="btn btn-validate" on:click={validateRedis} disabled={loading}>
              {#if loading}⏳ Validando...{:else}🔍 Validar Conexión{/if}
            </button>

            {#if validations.redis}
              <div class="validation-result" class:success={validations.redis.success} class:error={!validations.redis.success}>
                <h4>{validations.redis.success ? '✅' : '❌'} {validations.redis.message}</h4>
                {#if validations.redis.details}
                  <div class="details">
                    {#if validations.redis.details.redis_version}
                      <div class="detail-row"><span>Versión:</span><strong>{validations.redis.details.redis_version}</strong></div>
                    {/if}
                    {#if validations.redis.details.mode}
                      <div class="detail-row"><span>Modo:</span><strong>{validations.redis.details.mode}</strong></div>
                    {/if}
                    {#if validations.redis.details.used_memory_human}
                      <div class="detail-row"><span>Memoria:</span><strong>{validations.redis.details.used_memory_human}</strong></div>
                    {/if}
                  </div>
                {/if}
              </div>
            {/if}
          {:else}
            <div class="info-box">
              ℹ️ Sin Redis, las siguientes funciones estarán deshabilitadas:
              <ul>
                <li>Cache de queries</li>
                <li>Rate limiting</li>
                <li>Task queue (ARQ)</li>
                <li>Notificaciones en tiempo real</li>
              </ul>
            </div>
          {/if}
        </div>
      {/if}

      <!-- ======================================================================== -->
      <!-- Step 4: Storage -->
      <!-- ======================================================================== -->
      {#if currentStep === 4}
        <div class="step">
          <h2>📦 Storage (S3)</h2>
          <p class="lead">Configura S3 para almacenamiento de archivos. Compatible con AWS S3, MinIO, Backblaze B2.</p>

          <div class="badge badge-optional">Opcional</div>

          <div class="form-group">
            <label class="checkbox">
              <input type="checkbox" bind:checked={config.use_s3} />
              <span>Usar S3 para almacenamiento (recomendado en producción)</span>
            </label>
            <small>Si no activas esto, los archivos se guardarán en el filesystem local.</small>
          </div>

          {#if config.use_s3}
            <div class="form-group">
              <label>S3_BUCKET_NAME <span class="required">*</span></label>
              <input type="text" bind:value={config.s3_bucket_name} class="input" />
            </div>

            <div class="form-group">
              <label>S3_REGION</label>
              <input type="text" bind:value={config.s3_region} class="input" placeholder="us-east-1" />
            </div>

            <div class="form-group">
              <label>S3_ACCESS_KEY <span class="required">*</span></label>
              <input type="text" bind:value={config.s3_access_key} class="input mono" />
            </div>

            <div class="form-group">
              <label>S3_SECRET_KEY <span class="required">*</span></label>
              <input type="password" bind:value={config.s3_secret_key} class="input mono" />
            </div>

            <div class="form-group">
              <label>S3_ENDPOINT_URL <small>(solo para MinIO/B2)</small></label>
              <input type="text" bind:value={config.s3_endpoint_url} class="input" placeholder="Dejar vacío para AWS S3" />
            </div>

            <button class="btn btn-validate" on:click={validateS3} disabled={loading || !config.s3_bucket_name}>
              {#if loading}⏳ Validando...{:else}🔍 Validar S3{/if}
            </button>

            {#if validations.s3}
              <div class="validation-result" class:success={validations.s3.success} class:error={!validations.s3.success}>
                <h4>{validations.s3.success ? '✅' : '❌'} {validations.s3.message}</h4>
                {#if validations.s3.details}
                  <div class="details">
                    {#if validations.s3.details.can_put_object !== undefined}
                      <div class="detail-row">
                        <span>PutObject:</span>
                        <strong class:yes={validations.s3.details.can_put_object} class:no={!validations.s3.details.can_put_object}>
                          {validations.s3.details.can_put_object ? '✓' : '✗'}
                        </strong>
                      </div>
                    {/if}
                    {#if validations.s3.details.can_get_object !== undefined}
                      <div class="detail-row">
                        <span>GetObject:</span>
                        <strong class:yes={validations.s3.details.can_get_object} class:no={!validations.s3.details.can_get_object}>
                          {validations.s3.details.can_get_object ? '✓' : '✗'}
                        </strong>
                      </div>
                    {/if}
                  </div>
                {/if}
                {#if validations.s3.warnings && validations.s3.warnings.length > 0}
                  <div class="warnings">
                    <ul>
                      {#each validations.s3.warnings as warning}<li>{warning}</li>{/each}
                    </ul>
                  </div>
                {/if}
              </div>
            {/if}
          {/if}
        </div>
      {/if}

      <!-- ======================================================================== -->
      <!-- Step 5: SMTP -->
      <!-- ======================================================================== -->
      {#if currentStep === 5}
        <div class="step">
          <h2>📧 Email (SMTP)</h2>
          <p class="lead">Configura un servidor SMTP para enviar emails (reset password, invitaciones, etc).</p>

          <div class="badge badge-optional">Opcional</div>

          <div class="form-group">
            <label>SMTP_HOST</label>
            <input type="text" bind:value={config.smtp_host} class="input" placeholder="smtp.sendgrid.net" />
          </div>

          <div class="form-group">
            <label>SMTP_PORT</label>
            <input type="number" bind:value={config.smtp_port} class="input" placeholder="587" />
          </div>

          <div class="form-group">
            <label>SMTP_USER</label>
            <input type="text" bind:value={config.smtp_user} class="input" />
          </div>

          <div class="form-group">
            <label>SMTP_PASSWORD</label>
            <input type="password" bind:value={config.smtp_password} class="input" />
          </div>

          <div class="form-group">
            <label>SMTP_FROM_EMAIL</label>
            <input type="email" bind:value={config.smtp_from_email} class="input" placeholder="noreply@yourdomain.com" />
          </div>

          <div class="form-group">
            <label class="checkbox">
              <input type="checkbox" bind:checked={config.smtp_use_tls} />
              <span>Usar TLS (recomendado)</span>
            </label>
          </div>

          {#if config.smtp_host && config.smtp_user}
            <button class="btn btn-validate" on:click={validateSmtp} disabled={loading}>
              {#if loading}⏳ Validando...{:else}🔍 Validar SMTP{/if}
            </button>

            {#if validations.smtp}
              <div class="validation-result" class:success={validations.smtp.success} class:error={!validations.smtp.success}>
                <h4>{validations.smtp.success ? '✅' : '❌'} {validations.smtp.message}</h4>
              </div>
            {/if}
          {/if}

          <div class="info-box">
            💡 <strong>Proveedores recomendados:</strong>
            <ul>
              <li>SendGrid (gratis hasta 100/día)</li>
              <li>AWS SES (casi gratis)</li>
              <li>Mailgun</li>
              <li>Postmark</li>
            </ul>
          </div>
        </div>
      {/if}

      <!-- ======================================================================== -->
      <!-- Step 6: Payment -->
      <!-- ======================================================================== -->
      {#if currentStep === 6}
        <div class="step">
          <h2>💳 Pagos (Stripe)</h2>
          <p class="lead">Configura Stripe para procesar pagos y suscripciones.</p>

          <div class="badge badge-optional">Opcional</div>

          <div class="form-group">
            <label>Gateway de pago</label>
            <select bind:value={config.active_payment_gateway} class="input">
              <option value="">-- Sin pagos --</option>
              <option value="stripe">Stripe</option>
              <option value="mercadopago">MercadoPago (soportado)</option>
              <option value="polar">Polar (soportado)</option>
            </select>
          </div>

          {#if config.active_payment_gateway === 'stripe'}
            <div class="form-group">
              <label>STRIPE_SECRET_KEY <span class="required">*</span></label>
              <input type="password" bind:value={config.stripe_secret_key} class="input mono" placeholder="sk_test_... o sk_live_..." />
              <small>Obtén tu key en <a href="https://dashboard.stripe.com/apikeys" target="_blank">dashboard.stripe.com/apikeys</a></small>
            </div>

            <div class="form-group">
              <label>STRIPE_WEBHOOK_SECRET <small>(opcional)</small></label>
              <input type="password" bind:value={config.stripe_webhook_secret} class="input mono" placeholder="whsec_..." />
              <small>Para validar webhooks. Configura en dashboard después del deploy.</small>
            </div>

            <button class="btn btn-validate" on:click={validateStripe} disabled={loading || !config.stripe_secret_key}>
              {#if loading}⏳ Validando...{:else}🔍 Validar Stripe{/if}
            </button>

            {#if validations.stripe}
              <div class="validation-result" class:success={validations.stripe.success} class:error={!validations.stripe.success}>
                <h4>{validations.stripe.success ? '✅' : '❌'} {validations.stripe.message}</h4>
                {#if validations.stripe.details}
                  <div class="details">
                    {#if validations.stripe.details.mode}
                      <div class="detail-row"><span>Modo:</span><strong>{validations.stripe.details.mode}</strong></div>
                    {/if}
                    {#if validations.stripe.details.country}
                      <div class="detail-row"><span>País:</span><strong>{validations.stripe.details.country}</strong></div>
                    {/if}
                    {#if validations.stripe.details.charges_enabled !== undefined}
                      <div class="detail-row">
                        <span>Charges:</span>
                        <strong class:yes={validations.stripe.details.charges_enabled}>
                          {validations.stripe.details.charges_enabled ? '✓ Activos' : '✗ Inactivos'}
                        </strong>
                      </div>
                    {/if}
                  </div>
                {/if}
              </div>
            {/if}
          {/if}
        </div>
      {/if}

      <!-- ======================================================================== -->
      <!-- Step 7: Observability -->
      <!-- ======================================================================== -->
      {#if currentStep === 7}
        <div class="step">
          <h2>📊 Monitoreo y Observabilidad</h2>
          <p class="lead">Configura Sentry para error tracking en producción.</p>

          <div class="badge badge-optional">Opcional</div>

          <div class="form-group">
            <label>SENTRY_DSN</label>
            <input type="text" bind:value={config.sentry_dsn} class="input mono" placeholder="https://xxx@sentry.io/xxx" />
            <small>Obtén tu DSN creando un proyecto en <a href="https://sentry.io" target="_blank">sentry.io</a></small>
          </div>

          <div class="info-box">
            📈 <strong>Monitoreo incluido out-of-the-box:</strong>
            <ul>
              <li>Prometheus metrics en <code>/metrics</code></li>
              <li>Health checks en <code>/health</code></li>
              <li>Dashboard de Grafana en <code>monitoring/grafana-dashboard.json</code></li>
              <li>Logs estructurados (JSON)</li>
            </ul>
          </div>
        </div>
      {/if}

      <!-- ======================================================================== -->
      <!-- Step 8: Admin User -->
      <!-- ======================================================================== -->
      {#if currentStep === 8}
        <div class="step">
          <h2>👤 Usuario Administrador</h2>
          <p class="lead">Crea el primer usuario admin. Podrás agregar más después desde el admin panel.</p>

          <div class="badge badge-required">Obligatorio</div>

          <div class="form-group">
            <label>Email del Admin <span class="required">*</span></label>
            <input type="email" bind:value={config.admin_email} class="input" placeholder="admin@yourdomain.com" />
          </div>

          <div class="form-group">
            <label>Nombre</label>
            <input type="text" bind:value={config.admin_name} class="input" />
          </div>

          <div class="form-group">
            <label>Contraseña <span class="required">*</span></label>
            <input type="password" bind:value={config.admin_password} class="input" placeholder="Mínimo 8 caracteres" />
            {#if config.admin_password && config.admin_password.length < 8}
              <small class="error">❌ La contraseña debe tener al menos 8 caracteres</small>
            {/if}
            {#if config.enforce_strong_passwords && config.admin_password}
              <small>Debe contener: mayúscula, minúscula, número</small>
            {/if}
          </div>

          <div class="warning-box">
            ⚠️ <strong>IMPORTANTE:</strong> Guarda estas credenciales en un lugar seguro. Las necesitarás para acceder al admin panel.
          </div>
        </div>
      {/if}

      <!-- ======================================================================== -->
      <!-- Step 9: Review -->
      <!-- ======================================================================== -->
      {#if currentStep === 9}
        <div class="step">
          <h2>✅ Revisión Final</h2>
          <p class="lead">Verifica la configuración antes de guardar.</p>

          {#if !saveResult}
            <div class="review-grid">
              <div class="review-card">
                <h3>🗄️ Base de Datos</h3>
                <p class="status success">✓ Configurada</p>
                <small>{config.database_url.replace(/:[^@]+@/, ':****@')}</small>
              </div>

              <div class="review-card">
                <h3>🔐 Seguridad</h3>
                <p class="status success">✓ SECRET_KEY generada</p>
                <small>Passwords fuertes: {config.enforce_strong_passwords ? '✓' : '✗'}</small>
              </div>

              <div class="review-card">
                <h3>⚡ Redis</h3>
                <p class="status" class:success={config.redis_enabled} class:disabled={!config.redis_enabled}>
                  {config.redis_enabled ? '✓ Habilitado' : '○ Deshabilitado'}
                </p>
              </div>

              <div class="review-card">
                <h3>📦 Storage</h3>
                <p class="status" class:success={config.use_s3} class:disabled={!config.use_s3}>
                  {config.use_s3 ? '✓ S3' : '○ Local'}
                </p>
              </div>

              <div class="review-card">
                <h3>📧 Email</h3>
                <p class="status" class:success={config.smtp_host} class:disabled={!config.smtp_host}>
                  {config.smtp_host ? '✓ ' + config.smtp_host : '○ No configurado'}
                </p>
              </div>

              <div class="review-card">
                <h3>💳 Pagos</h3>
                <p class="status" class:success={config.active_payment_gateway} class:disabled={!config.active_payment_gateway}>
                  {config.active_payment_gateway || '○ No configurado'}
                </p>
              </div>

              <div class="review-card">
                <h3>📊 Sentry</h3>
                <p class="status" class:success={config.sentry_dsn} class:disabled={!config.sentry_dsn}>
                  {config.sentry_dsn ? '✓ Configurado' : '○ No configurado'}
                </p>
              </div>

              <div class="review-card">
                <h3>👤 Admin</h3>
                <p class="status success">✓ {config.admin_email}</p>
              </div>
            </div>

            <button class="btn btn-primary btn-large" on:click={saveConfiguration} disabled={loading}>
              {#if loading}⏳ Guardando configuración...{:else}💾 Guardar y Finalizar{/if}
            </button>
          {:else}
            <!-- Resultado del guardado -->
            <div class="validation-result" class:success={saveResult.success} class:error={!saveResult.success}>
              <h3>{saveResult.success ? '🎉' : '❌'} {saveResult.message}</h3>

              {#if saveResult.success}
                <div class="next-steps">
                  <h4>📋 Próximos pasos:</h4>
                  <ol>
                    <li><strong>Reinicia el backend</strong> para aplicar la configuración:
                      <div class="code-block">uv run python main.py</div>
                    </li>
                    <li>Accede al admin panel: <a href="/admin">/admin</a></li>
                    <li>Inicia sesión con tu cuenta admin</li>
                    <li>Revisa la <a href="/admin/docs">documentación</a> en el admin panel</li>
                  </ol>
                </div>

                {#if saveResult.warnings && saveResult.warnings.length > 0}
                  <div class="warnings">
                    {#each saveResult.warnings as warning}
                      <p>{warning}</p>
                    {/each}
                  </div>
                {/if}
              {/if}
            </div>
          {/if}
        </div>
      {/if}
    </div>

    <!-- Navigation -->
    {#if !saveResult}
      <div class="wizard-nav">
        <button class="btn btn-secondary" on:click={prevStep} disabled={currentStep === 0}>
          ← Anterior
        </button>

        <div class="nav-info">
          Paso {currentStep + 1} de {steps.length}
        </div>

        {#if currentStep < steps.length - 1}
          {#if steps[currentStep].skippable}
            <button class="btn btn-ghost" on:click={skipStep}>
              Omitir →
            </button>
          {/if}
          <button class="btn btn-primary" on:click={nextStep} disabled={!canAdvance()}>
            Siguiente →
          </button>
        {/if}
      </div>
    {/if}
  </div>
{/if}

<style>
  :global(body) {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    margin: 0;
    min-height: 100vh;
    font-family: system-ui, -apple-system, sans-serif;
  }

  .container {
    max-width: 1100px;
    margin: 0 auto;
    padding: 2rem;
    color: #e2e8f0;
  }

  .wizard-header {
    text-align: center;
    margin-bottom: 2rem;
  }

  .wizard-header h1 {
    font-size: 2.5rem;
    margin: 0;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .wizard-header p {
    color: #94a3b8;
    font-size: 1.1rem;
  }

  .progress-bar {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 2rem;
    padding: 1.5rem;
    background: rgba(30, 41, 59, 0.5);
    border-radius: 1rem;
    backdrop-filter: blur(10px);
    overflow-x: auto;
  }

  .progress-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
    min-width: 80px;
    opacity: 0.5;
    transition: opacity 0.3s;
  }

  .progress-step.active, .progress-step.completed {
    opacity: 1;
  }

  .step-circle {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background: #334155;
    border: 2px solid #475569;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    margin-bottom: 0.5rem;
    transition: all 0.3s;
  }

  .progress-step.active .step-circle {
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    border-color: #3b82f6;
    box-shadow: 0 0 20px rgba(59, 130, 246, 0.5);
  }

  .progress-step.completed .step-circle {
    background: #10b981;
    border-color: #10b981;
  }

  .step-label {
    font-size: 0.8rem;
    color: #cbd5e1;
    text-align: center;
  }

  .wizard-content {
    background: rgba(30, 41, 59, 0.7);
    border-radius: 1rem;
    padding: 2.5rem;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    min-height: 500px;
  }

  .step h2 {
    font-size: 2rem;
    margin-top: 0;
    margin-bottom: 0.5rem;
    color: #f1f5f9;
  }

  .lead {
    font-size: 1.1rem;
    color: #94a3b8;
    margin-bottom: 1.5rem;
  }

  .badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.8rem;
    font-weight: 600;
    margin-bottom: 1.5rem;
  }

  .badge-required {
    background: rgba(239, 68, 68, 0.2);
    color: #fca5a5;
    border: 1px solid rgba(239, 68, 68, 0.3);
  }

  .badge-optional {
    background: rgba(59, 130, 246, 0.2);
    color: #93c5fd;
    border: 1px solid rgba(59, 130, 246, 0.3);
  }

  .info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1rem;
    margin: 2rem 0;
  }

  .info-card {
    background: rgba(15, 23, 42, 0.5);
    padding: 1.5rem;
    border-radius: 0.75rem;
    border: 1px solid rgba(255, 255, 255, 0.05);
  }

  .info-card h3 {
    margin-top: 0;
    color: #e2e8f0;
    font-size: 1rem;
  }

  .info-card ul {
    margin: 0;
    padding-left: 1.25rem;
    color: #94a3b8;
    font-size: 0.9rem;
  }

  .environment-selector {
    margin-top: 2rem;
    padding: 1.5rem;
    background: rgba(15, 23, 42, 0.5);
    border-radius: 0.75rem;
  }

  .environment-selector label {
    display: block;
    margin-bottom: 0.75rem;
    font-weight: 600;
  }

  .radio-group {
    display: flex;
    gap: 1rem;
  }

  .radio {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
    padding: 0.75rem 1.25rem;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 0.5rem;
    transition: all 0.2s;
  }

  .radio:hover {
    background: rgba(255, 255, 255, 0.1);
  }

  .radio input[type="radio"] {
    cursor: pointer;
  }

  .form-group {
    margin-bottom: 1.25rem;
  }

  .form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: #cbd5e1;
  }

  .form-group small {
    display: block;
    margin-top: 0.5rem;
    color: #64748b;
    font-size: 0.85rem;
  }

  .form-group small.error {
    color: #f87171;
  }

  .input {
    width: 100%;
    padding: 0.75rem 1rem;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 0.5rem;
    color: #f1f5f9;
    font-size: 0.95rem;
    box-sizing: border-box;
    transition: all 0.2s;
  }

  .input:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
  }

  .input.mono {
    font-family: 'Courier New', monospace;
    font-size: 0.85rem;
  }

  .input-with-button {
    display: flex;
    gap: 0.5rem;
  }

  .input-with-button .input {
    flex: 1;
  }

  .checkbox {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    cursor: pointer;
    padding: 0.75rem;
    background: rgba(15, 23, 42, 0.5);
    border-radius: 0.5rem;
    transition: background 0.2s;
  }

  .checkbox:hover {
    background: rgba(15, 23, 42, 0.7);
  }

  .checkbox input[type="checkbox"] {
    width: 1.25rem;
    height: 1.25rem;
    cursor: pointer;
  }

  select.input {
    cursor: pointer;
  }

  .required {
    color: #f87171;
  }

  .btn {
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 0.5rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 0.95rem;
  }

  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-primary {
    background: linear-gradient(135deg, #3b82f6, #2563eb);
    color: white;
  }

  .btn-primary:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 10px 20px rgba(59, 130, 246, 0.3);
  }

  .btn-secondary {
    background: rgba(255, 255, 255, 0.1);
    color: #cbd5e1;
  }

  .btn-secondary:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.15);
  }

  .btn-ghost {
    background: transparent;
    color: #94a3b8;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }

  .btn-ghost:hover {
    background: rgba(255, 255, 255, 0.05);
  }

  .btn-validate {
    background: rgba(59, 130, 246, 0.2);
    color: #93c5fd;
    border: 1px solid rgba(59, 130, 246, 0.3);
    margin-top: 1rem;
  }

  .btn-validate:hover:not(:disabled) {
    background: rgba(59, 130, 246, 0.3);
  }

  .btn-small {
    padding: 0.5rem 1rem;
    font-size: 0.85rem;
  }

  .btn-large {
    padding: 1rem 2rem;
    font-size: 1.1rem;
    width: 100%;
    margin-top: 2rem;
  }

  .validation-result {
    margin-top: 1.5rem;
    padding: 1.25rem;
    border-radius: 0.75rem;
    border: 1px solid;
  }

  .validation-result.success {
    background: rgba(16, 185, 129, 0.1);
    border-color: rgba(16, 185, 129, 0.3);
  }

  .validation-result.error {
    background: rgba(239, 68, 68, 0.1);
    border-color: rgba(239, 68, 68, 0.3);
  }

  .validation-result h4 {
    margin: 0 0 0.75rem 0;
  }

  .details {
    background: rgba(0, 0, 0, 0.3);
    padding: 0.75rem;
    border-radius: 0.5rem;
    margin-top: 0.75rem;
  }

  .detail-row {
    display: flex;
    justify-content: space-between;
    padding: 0.4rem 0;
    font-size: 0.9rem;
  }

  .detail-row span {
    color: #94a3b8;
  }

  .detail-row strong {
    color: #e2e8f0;
  }

  .detail-row strong.yes {
    color: #34d399;
  }

  .detail-row strong.no {
    color: #f87171;
  }

  .warnings {
    margin-top: 1rem;
    padding: 0.75rem;
    background: rgba(251, 191, 36, 0.1);
    border-radius: 0.5rem;
    border: 1px solid rgba(251, 191, 36, 0.3);
  }

  .warnings h5 {
    margin: 0 0 0.5rem 0;
    color: #fcd34d;
  }

  .warnings ul {
    margin: 0;
    padding-left: 1.25rem;
    font-size: 0.9rem;
    color: #fde68a;
  }

  .info-box {
    margin-top: 1rem;
    padding: 1rem;
    background: rgba(59, 130, 246, 0.1);
    border: 1px solid rgba(59, 130, 246, 0.3);
    border-radius: 0.5rem;
    color: #bfdbfe;
    font-size: 0.9rem;
  }

  .info-box ul {
    margin: 0.5rem 0 0 0;
    padding-left: 1.25rem;
  }

  .warning-box {
    margin-top: 1rem;
    padding: 1rem;
    background: rgba(251, 191, 36, 0.1);
    border: 1px solid rgba(251, 191, 36, 0.3);
    border-radius: 0.5rem;
    color: #fde68a;
    font-size: 0.9rem;
  }

  code {
    background: rgba(0, 0, 0, 0.3);
    padding: 0.2rem 0.4rem;
    border-radius: 0.25rem;
    font-family: monospace;
    font-size: 0.85em;
    color: #93c5fd;
  }

  .review-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin: 2rem 0;
  }

  .review-card {
    padding: 1.25rem;
    background: rgba(15, 23, 42, 0.5);
    border-radius: 0.75rem;
    border: 1px solid rgba(255, 255, 255, 0.05);
  }

  .review-card h3 {
    margin: 0 0 0.5rem 0;
    font-size: 0.95rem;
    color: #cbd5e1;
  }

  .review-card .status {
    margin: 0.5rem 0;
    font-weight: 600;
  }

  .review-card .status.success {
    color: #34d399;
  }

  .review-card .status.disabled {
    color: #64748b;
  }

  .review-card small {
    color: #64748b;
    font-size: 0.8rem;
    word-break: break-all;
  }

  .wizard-nav {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 2rem;
    padding: 1.5rem;
    background: rgba(30, 41, 59, 0.5);
    border-radius: 1rem;
    backdrop-filter: blur(10px);
    gap: 1rem;
  }

  .nav-info {
    color: #94a3b8;
    font-size: 0.9rem;
  }

  .next-steps {
    margin-top: 1.5rem;
  }

  .next-steps ol {
    padding-left: 1.5rem;
    color: #cbd5e1;
  }

  .next-steps li {
    margin-bottom: 1rem;
    line-height: 1.6;
  }

  .code-block {
    background: rgba(0, 0, 0, 0.5);
    padding: 0.75rem 1rem;
    border-radius: 0.5rem;
    font-family: monospace;
    margin-top: 0.5rem;
    color: #93c5fd;
    font-size: 0.9rem;
  }

  .alert {
    text-align: center;
    padding: 3rem;
  }

  .alert h1 {
    color: #fcd34d;
  }

  .card {
    background: rgba(30, 41, 59, 0.7);
    border-radius: 1rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
  }

  a {
    color: #93c5fd;
    text-decoration: none;
  }

  a:hover {
    text-decoration: underline;
  }

  @media (max-width: 768px) {
    .container {
      padding: 1rem;
    }

    .wizard-content {
      padding: 1.5rem;
    }

    .progress-bar {
      padding: 1rem;
    }

    .step-label {
      display: none;
    }

    .review-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
