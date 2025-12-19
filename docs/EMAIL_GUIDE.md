# Guía del Sistema de Emails (SMTP)

## 📧 Descripción General

Sistema completo para enviar correos electrónicos con plantillas HTML profesionales. Incluye:

- **Envío asíncrono** con `aiosmtplib` (no bloquea la aplicación)
- **Plantillas Jinja2** con variables dinámicas
- **Validación automática** de direcciones de correo
- **Soporte para adjuntos** y múltiples destinatarios
- **4 plantillas pre-diseñadas** listas para usar

---

## ⚙️ Configuración

### 1. Variables de Entorno

Agrega estas variables a tu archivo `.env`:

```env
# Configuración SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=tu-app-password
SMTP_FROM_EMAIL=tu-email@gmail.com
SMTP_FROM_NAME="Mi Aplicación"
SMTP_USE_TLS=True
```

### 2. Proveedores SMTP Populares

#### Gmail
- **Host:** `smtp.gmail.com`
- **Puerto:** `587`
- **TLS:** `True`
- **Nota:** Necesitas crear una "Contraseña de aplicación" (no uses tu contraseña normal)
  1. Ve a tu Cuenta de Google
  2. Seguridad → Verificación en 2 pasos (activar)
  3. Contraseñas de aplicaciones → Crear
  4. Usa esa contraseña en `SMTP_PASSWORD`

#### Outlook/Office 365
```env
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USE_TLS=True
```

#### SendGrid
```env
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key
SMTP_USE_TLS=True
```

#### Mailgun
```env
SMTP_HOST=smtp.mailgun.org
SMTP_PORT=587
SMTP_USER=postmaster@your-domain.mailgun.org
SMTP_PASSWORD=your-mailgun-password
SMTP_USE_TLS=True
```

---

## 📝 Plantillas Disponibles

### 1. **welcome.html** - Email de Bienvenida
Enviar cuando un usuario se registra en tu aplicación.

**Variables:**
- `name`: Nombre del usuario
- `verification_url` (opcional): URL de verificación de email
- `app_name`: Nombre de tu aplicación

**Ejemplo:**
```python
from app.services.email_service import email_service

await email_service.send_welcome_email(
    to="user@example.com",
    name="Juan Pérez",
    verification_url="https://tuapp.com/verify?token=abc123"
)
```

---

### 2. **verify_email.html** - Verificación de Email
Enviar para que el usuario verifique su dirección de correo.

**Variables:**
- `name`: Nombre del usuario
- `verification_url`: URL de verificación
- `app_name`: Nombre de tu aplicación

**Ejemplo:**
```python
await email_service.send_verification_email(
    to="user@example.com",
    name="Juan Pérez",
    verification_url="https://tuapp.com/verify?token=abc123"
)
```

---

### 3. **password_reset.html** - Recuperación de Contraseña
Enviar cuando un usuario solicita restablecer su contraseña.

**Variables:**
- `name`: Nombre del usuario
- `reset_url`: URL para restablecer contraseña
- `app_name`: Nombre de tu aplicación

**Ejemplo:**
```python
await email_service.send_password_reset_email(
    to="user@example.com",
    name="Juan Pérez",
    reset_url="https://tuapp.com/reset-password?token=xyz789"
)
```

---

### 4. **notification.html** - Notificación Genérica
Email genérico para cualquier tipo de notificación.

**Variables:**
- `name`: Nombre del usuario
- `title`: Título de la notificación
- `body`: Contenido de la notificación
- `app_name`: Nombre de tu aplicación

**Ejemplo:**
```python
await email_service.send_notification_email(
    to="user@example.com",
    name="Juan Pérez",
    notification_title="Nueva función disponible",
    notification_body="Hemos lanzado una nueva característica que te puede interesar..."
)
```

---

## 💻 Uso en el Código

### Enviar Email Simple

```python
from app.services.email_service import email_service

# HTML personalizado
await email_service.send_email(
    to=["user@example.com"],
    subject="Hola desde FastAPI",
    html_content="<h1>¡Hola!</h1><p>Este es un email de prueba.</p>",
    text_content="Hola! Este es un email de prueba.",  # Fallback
    cc=["otro@example.com"],  # Opcional
    bcc=["admin@example.com"]  # Opcional
)
```

### Enviar con Plantilla Personalizada

```python
# Usando una plantilla existente
await email_service.send_template_email(
    to=["user@example.com"],
    subject="Bienvenido a nuestra plataforma",
    template_name="welcome.html",
    context={
        "name": "Juan",
        "app_name": "Mi App",
        "verification_url": "https://example.com/verify?token=abc"
    }
)
```

### Enviar desde una Ruta FastAPI

```python
from fastapi import APIRouter
from app.services.email_service import email_service

router = APIRouter()

@router.post("/send-verification")
async def send_verification(email: str, name: str):
    # Generar token de verificación (ejemplo)
    verification_token = "abc123"
    verification_url = f"https://tuapp.com/verify?token={verification_token}"

    # Enviar email
    success = await email_service.send_verification_email(
        to=email,
        name=name,
        verification_url=verification_url
    )

    if not success:
        raise HTTPException(500, "Failed to send email")

    return {"message": "Email sent successfully"}
```

---

## 🎨 Crear Tu Propia Plantilla

Las plantillas se guardan en `app/templates/emails/`.

### 1. Crear el Archivo HTML

```html
<!-- app/templates/emails/mi_plantilla.html -->
{% extends "base.html" %}

{% block title %}Mi Título{% endblock %}

{% block header_title %}¡Hola!{% endblock %}

{% block content %}
<h2>Hola, {{ name }}!</h2>

<p>Este es el contenido de tu email.</p>

<div class="info-box">
    <p>Variable personalizada: {{ mi_variable }}</p>
</div>

<div style="text-align: center;">
    <a href="{{ mi_url }}" class="button">Mi Botón</a>
</div>

<p style="margin-top: 30px;">
    Saludos,<br>
    <strong>El equipo de {{ app_name }}</strong>
</p>
{% endblock %}
```

### 2. Usar la Plantilla

```python
await email_service.send_template_email(
    to=["user@example.com"],
    subject="Mi Asunto",
    template_name="mi_plantilla.html",
    context={
        "name": "Juan",
        "mi_variable": "Valor personalizado",
        "mi_url": "https://example.com",
        "app_name": "Mi App"
    }
)
```

---

## 🔌 API Endpoints

El sistema incluye endpoints REST para enviar emails sin código:

### Ver Configuración
```http
GET /email/config
```

Respuesta:
```json
{
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "from_email": "tu-email@gmail.com",
  "from_name": "FastAPI Base",
  "use_tls": true,
  "configured": true
}
```

### Listar Plantillas
```http
GET /email/templates
```

### Enviar Email de Bienvenida
```http
POST /email/send-welcome
Content-Type: application/json

{
  "to": "user@example.com",
  "name": "Juan Pérez",
  "verification_url": "https://tuapp.com/verify?token=abc123"
}
```

### Enviar Email de Verificación
```http
POST /email/send-verification
Content-Type: application/json

{
  "to": "user@example.com",
  "name": "Juan Pérez",
  "verification_url": "https://tuapp.com/verify?token=abc123"
}
```

### Enviar Email de Recuperación
```http
POST /email/send-password-reset
Content-Type: application/json

{
  "to": "user@example.com",
  "name": "Juan Pérez",
  "reset_url": "https://tuapp.com/reset?token=xyz789"
}
```

### Enviar Notificación
```http
POST /email/send-notification
Content-Type: application/json

{
  "to": "user@example.com",
  "name": "Juan Pérez",
  "notification_title": "Nueva característica",
  "notification_body": "Hemos lanzado algo nuevo..."
}
```

### Enviar Email Personalizado
```http
POST /email/send
Content-Type: application/json

{
  "to": ["user1@example.com", "user2@example.com"],
  "subject": "Mi asunto",
  "html_content": "<h1>Hola</h1><p>Contenido</p>",
  "text_content": "Hola, Contenido",
  "cc": ["cc@example.com"],
  "bcc": ["bcc@example.com"]
}
```

---

## 🧪 Probar el Sistema

### 1. Configurar Credenciales SMTP

Edita `.env` y agrega tus credenciales reales.

### 2. Iniciar el Servidor

```bash
python main.py
```

### 3. Ir a Swagger UI

Abre: http://localhost:8001/docs

### 4. Probar un Endpoint

En Swagger, ve a **email** → **POST /email/send-welcome** → Try it out

Cambia el email a uno tuyo y ejecuta.

---

## 🔒 Mejores Prácticas

### 1. No Expongas Credenciales
✅ **CORRECTO:** Usa variables de entorno (`.env`)
❌ **INCORRECTO:** Hardcodear credenciales en el código

### 2. Usa App Passwords (Gmail)
Para Gmail, NUNCA uses tu contraseña real. Siempre crea una contraseña de aplicación.

### 3. Maneja Errores
```python
success = await email_service.send_email(...)
if not success:
    # Log error, notificar al admin, reintentarbackground task
    logger.error(f"Failed to send email to {to}")
```

### 4. Usa Queue para Envíos Masivos
Para enviar muchos emails, usa Celery o similar:

```python
# En lugar de:
for user in users:
    await email_service.send_email(...)  # Lento

# Mejor:
send_email_task.delay(user.email, ...)  # Background
```

### 5. Personaliza las Plantillas
Modifica los colores, estilos, logos en `app/templates/emails/base.html` para que coincidan con tu marca.

---

## 🐛 Troubleshooting

### Error: "SMTP credentials not configured"
**Solución:** Verifica que `SMTP_USER` y `SMTP_PASSWORD` estén configurados en `.env`

### Error: "Authentication failed"
**Solución (Gmail):** Asegúrate de usar una contraseña de aplicación, no tu contraseña normal.

### Error: "Connection refused"
**Solución:** Verifica:
- `SMTP_HOST` y `SMTP_PORT` son correctos
- Tu firewall no está bloqueando el puerto
- El servidor SMTP está disponible

### Los Emails no Llegan
**Solución:**
1. Revisa la carpeta de SPAM
2. Verifica que `SMTP_FROM_EMAIL` sea válido
3. Asegúrate de que el servidor SMTP permite envío desde tu IP
4. Revisa los logs del servidor para errores

### Error: "Email template not found"
**Solución:** Verifica que:
- El archivo existe en `app/templates/emails/`
- El nombre del archivo es correcto (con extensión `.html`)
- `EMAIL_TEMPLATES_DIR` en config apunta a la carpeta correcta

---

## 📚 Recursos Adicionales

- [aiosmtplib Documentation](https://aiosmtplib.readthedocs.io/)
- [Jinja2 Template Documentation](https://jinja.palletsprojects.com/)
- [Email Validator](https://github.com/JoshData/python-email-validator)
- [Gmail App Passwords](https://support.google.com/accounts/answer/185833)
- [SendGrid SMTP](https://docs.sendgrid.com/for-developers/sending-email/integrating-with-the-smtp-api)

---

## 💡 Ideas de Uso

- ✉️ Email de bienvenida al registrarse
- ✅ Verificación de email
- 🔐 Recuperación de contraseña
- 📊 Reportes periódicos
- 🎉 Notificaciones de eventos
- 💰 Facturas y recibos
- 🔔 Alertas del sistema
- 📧 Newsletter/Boletines
- ⭐ Solicitar feedback/reviews
- 🎁 Promociones y ofertas
