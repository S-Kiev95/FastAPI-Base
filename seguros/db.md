# Refactorizacion del Schema de Base de Datos - Seguros SaaS

## 1. Analisis del Schema Actual

### Problemas identificados

| Problema | Tabla(s) afectada(s) | Descripcion |
|----------|---------------------|-------------|
| Tabla `usuarios` duplica `auth.users` | `usuarios` | Supabase ya provee autenticacion via `auth.users`. La tabla custom almacena contrasenas en texto y no aprovecha JWT, OAuth, ni RLS |
| Tabla `asegurados` desnormalizada | `asegurados` | Mezcla datos del cliente, la poliza, el vehiculo y el estado de pagos en una sola fila. Si un cliente tiene 2 polizas, se duplica nombre/telefono |
| Enums hardcodeados | `asegurados`, `siniestro` | `tipo_seguro`, `estado_vencimiento`, `asegurador`, `estado_cliente`, `tipo_dano` son `USER-DEFINED` sin flexibilidad para agregar valores desde la app |
| Sin soporte multi-tenant | todas | Para SaaS necesitamos aislar datos por organizacion (correduria) |
| Sin timestamps de auditoria | todas | No hay `created_at` / `updated_at` para trazabilidad |
| Documentos de siniestro como booleanos | `siniestro` | 7 columnas booleanas que no escalan si se agregan nuevos tipos de documento |
| Tabla `corredor` minima | `corredor` | Solo tiene nombre, sin datos de contacto ni relacion con `auth.users` |
| Nombres inconsistentes | varias | Mezcla singular/plural (`aseguradora` vs `asegurados`), y prefijos `id_` vs sin prefijo |

---

## 2. Schema Refactorizado

### 2.1 Modelo de datos

```
organizacion (tenant)
  ├── perfil (auth.users) ─── roles: administrador, corredor, vendedor, empleado, visualizador
  ├── cliente
  │     ├── vehiculo
  │     └── poliza (vincula cliente + vehiculo + aseguradora)
  │           ├── cuota (plan de pagos)
  │           └── siniestro
  │                 └── siniestro_documento (checklist dinamico)
  ├── aseguradora
  │     └── aseguradora_taller (acreditaciones por zona)
  ├── taller (talleres mecanicos por departamento/ciudad)
  ├── tarea (calendario interno, vinculable a cliente/poliza/siniestro)
  ├── mensaje (mensajeria interna entre usuarios)
  └── suscripcion → plan_suscripcion (facturacion SaaS via Mercado Pago)
        └── pago_suscripcion
```

### 2.2 Convenciones

- Nombres en **singular**, en **espanol**, en **snake_case**
- Toda tabla tiene `id` (UUID), `created_at`, `updated_at`
- Foreign keys: `<tabla>_id`
- Multi-tenancy via columna `organizacion_id` + RLS
- Enums como tablas de lookup cuando necesiten ser editables desde la app, o como `CHECK` constraints cuando sean fijos

---

### 2.3 Definicion de tablas

#### `organizacion` — Tenant (correduria de seguros)

```sql
CREATE TABLE public.organizacion (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nombre text NOT NULL,
  rut text,                          -- identificador fiscal
  direccion text,
  telefono text,
  email text,
  activa boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
```

> Cada correduria que contrate el SaaS es una organizacion. Todos los datos se aislan por `organizacion_id`.

---

#### `perfil` — Extiende `auth.users` (reemplaza `usuarios`)

```sql
CREATE TABLE public.perfil (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  organizacion_id uuid NOT NULL REFERENCES public.organizacion(id),
  nombre text NOT NULL,
  apellido text,
  telefono text,
  rol text NOT NULL DEFAULT 'empleado'
    CHECK (rol IN ('administrador', 'corredor', 'vendedor', 'empleado', 'visualizador')),
  activo boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
```

> - Elimina la tabla `usuarios`. La autenticacion la maneja Supabase (`auth.users`).
> - El `id` es el mismo UUID de `auth.users`.
> - Roles: `administrador` (gestion total), `corredor` (gestiona polizas), `vendedor` (vende seguros, visible en sidebar), `empleado` (operativo), `visualizador` (solo lectura).

---

#### `aseguradora` — Companias de seguros

```sql
CREATE TABLE public.aseguradora (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organizacion_id uuid NOT NULL REFERENCES public.organizacion(id),
  nombre text NOT NULL,
  telefono text,
  email text,
  direccion text,
  contactos jsonb NOT NULL DEFAULT '[]'::jsonb,  -- array de {nombre, cargo, telefono, email}
  activa boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organizacion_id, nombre)
);
```

> Se mantiene `contactos` como JSONB (util para lista variable de contactos), pero se agregan campos top-level para el contacto principal.

---

#### `cliente` — Personas aseguradas (reemplaza datos personales de `asegurados`)

```sql
CREATE TABLE public.cliente (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organizacion_id uuid NOT NULL REFERENCES public.organizacion(id),
  numero_cliente text,               -- codigo interno del corredor
  nombre text NOT NULL,
  apellido text NOT NULL,
  documento_identidad text,          -- CI / cedula
  telefono text,
  email text,
  direccion text,
  fecha_nacimiento date,
  notas text,
  activo boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_cliente_org ON public.cliente(organizacion_id);
CREATE INDEX idx_cliente_nombre ON public.cliente(organizacion_id, apellido, nombre);
```

> Separa los datos de la persona de los datos de la poliza. Un cliente puede tener multiples polizas y vehiculos.

---

#### `vehiculo` — Vehiculos asegurados

```sql
CREATE TABLE public.vehiculo (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organizacion_id uuid NOT NULL REFERENCES public.organizacion(id),
  cliente_id uuid NOT NULL REFERENCES public.cliente(id),
  marca text NOT NULL,
  modelo text,
  anio integer,
  matricula text NOT NULL,
  tipo text NOT NULL DEFAULT 'auto'
    CHECK (tipo IN ('auto', 'moto', 'camion', 'utilitario', 'otro')),
  color text,
  numero_motor text,
  numero_chasis text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organizacion_id, matricula)
);
```

> Normaliza `marca_vehiculo` y `matricula` que estaban embebidos en `asegurados`.

---

#### `poliza` — Contratos de seguro (reemplaza datos de poliza de `asegurados`)

```sql
CREATE TABLE public.poliza (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organizacion_id uuid NOT NULL REFERENCES public.organizacion(id),
  cliente_id uuid NOT NULL REFERENCES public.cliente(id),
  vehiculo_id uuid REFERENCES public.vehiculo(id),        -- nullable para seguros no vehiculares
  aseguradora_id uuid NOT NULL REFERENCES public.aseguradora(id),
  corredor_id uuid REFERENCES public.perfil(id),           -- quien gestiona esta poliza

  numero_poliza text NOT NULL,
  tipo_seguro text NOT NULL DEFAULT 'auto'
    CHECK (tipo_seguro IN ('auto', 'moto', 'hogar', 'vida', 'comercio', 'responsabilidad_civil', 'otro')),

  vigente_desde date NOT NULL,
  vigente_hasta date NOT NULL,

  prima_total numeric(12,2),          -- monto total de la poliza
  moneda text NOT NULL DEFAULT 'UYU'
    CHECK (moneda IN ('UYU', 'USD')),

  total_cuotas integer NOT NULL DEFAULT 1,

  estado text NOT NULL DEFAULT 'activa'
    CHECK (estado IN ('activa', 'vencida', 'cancelada', 'suspendida', 'renovada')),

  notas text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),

  UNIQUE (organizacion_id, numero_poliza)
);

CREATE INDEX idx_poliza_cliente ON public.poliza(cliente_id);
CREATE INDEX idx_poliza_vencimiento ON public.poliza(organizacion_id, vigente_hasta);
CREATE INDEX idx_poliza_estado ON public.poliza(organizacion_id, estado);
```

> - Separa la poliza como entidad propia.
> - `vehiculo_id` es nullable para permitir seguros que no son de vehiculo (hogar, vida, etc.) — pensando en la expansion futura.
> - `corredor_id` referencia a `perfil` (que es `auth.users`), reemplazando la tabla `corredor`.
> - El campo `estado_vencimiento` se elimina: se puede calcular comparando `vigente_hasta` con `CURRENT_DATE`.

---

#### `cuota` — Plan de pagos por poliza

```sql
CREATE TABLE public.cuota (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  poliza_id uuid NOT NULL REFERENCES public.poliza(id) ON DELETE CASCADE,
  numero_cuota integer NOT NULL,      -- 1, 2, 3...
  monto numeric(12,2) NOT NULL,
  fecha_vencimiento date NOT NULL,
  fecha_pago date,                    -- null = no pagada
  pagada boolean NOT NULL DEFAULT false,
  metodo_pago text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (poliza_id, numero_cuota)
);

CREATE INDEX idx_cuota_vencimiento ON public.cuota(fecha_vencimiento) WHERE NOT pagada;
```

> Reemplaza `cuotas_pagadas`, `cuotas_por_pagar` y `vencimiento_cuotas` de la tabla `asegurados`. Ahora cada cuota es un registro individual con su fecha y estado.

---

#### `siniestro` — Reclamos / siniestros

```sql
CREATE TABLE public.siniestro (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organizacion_id uuid NOT NULL REFERENCES public.organizacion(id),
  poliza_id uuid NOT NULL REFERENCES public.poliza(id),
  aseguradora_id uuid NOT NULL REFERENCES public.aseguradora(id),

  numero_siniestro text NOT NULL,
  fecha_ocurrencia date,
  fecha_denuncia date,

  tipo_dano text NOT NULL DEFAULT 'dano_propio'
    CHECK (tipo_dano IN ('dano_propio', 'dano_tercero', 'robo_total', 'robo_parcial', 'incendio', 'otro')),

  estado text NOT NULL DEFAULT 'abierto'
    CHECK (estado IN ('abierto', 'en_tramite', 'liquidado', 'rechazado', 'cerrado')),

  monto_reclamado numeric(12,2),
  monto_liquidado numeric(12,2),

  descripcion text,
  observaciones text,

  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),

  UNIQUE (organizacion_id, numero_siniestro)
);
```

> - La FK ahora es a `poliza` en vez de a `asegurado` + `aseguradora` por separado, ya que la poliza ya contiene ambas relaciones.
> - Se mantiene `aseguradora_id` como FK directa para facilitar queries.
> - `observaciones` pasa de JSONB a texto plano (mas simple). Si se necesita historial de observaciones, se puede crear una tabla separada.

---

#### `siniestro_documento` — Checklist de documentos por siniestro

```sql
CREATE TABLE public.siniestro_documento (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  siniestro_id uuid NOT NULL REFERENCES public.siniestro(id) ON DELETE CASCADE,
  tipo_documento text NOT NULL,       -- 'denuncia', 'presupuesto_taller', 'cedula', 'libreta_propiedad', etc.
  recibido boolean NOT NULL DEFAULT false,
  fecha_recepcion date,
  archivo_url text,                   -- link al storage de Supabase
  notas text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (siniestro_id, tipo_documento)
);
```

> Reemplaza las 7+ columnas booleanas (`denuncia`, `presupuesto_taller`, `cedula`, etc.). Ahora se pueden agregar nuevos tipos de documento sin modificar el schema.

---

#### `taller` — Talleres mecanicos acreditados por aseguradoras

```sql
CREATE TABLE public.taller (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organizacion_id uuid NOT NULL REFERENCES public.organizacion(id),
  nombre text NOT NULL,
  direccion text,
  departamento text NOT NULL,         -- 'Montevideo', 'Canelones', 'Maldonado', etc.
  ciudad text,
  telefono text,
  telefono2 text,                     -- muchos talleres manejan 2+ lineas
  email text,
  especialidad text NOT NULL DEFAULT 'general'
    CHECK (especialidad IN ('general', 'chapa_pintura', 'mecanica', 'electricidad', 'cristales', 'multimarca', 'oficial')),
  marcas_atendidas text[],            -- array: {'Toyota', 'VW', 'Chevrolet'} o null si es multimarca
  horario text,                       -- ej: 'Lun-Vie 8:00-18:00'
  activo boolean NOT NULL DEFAULT true,
  notas text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_taller_depto ON public.taller(organizacion_id, departamento);
```

> Cada taller tiene departamento y ciudad para filtrar por zona (requisito de las aseguradoras en Uruguay). `marcas_atendidas` como array de texto permite talleres multimarca y oficiales. `telefono2` porque en la data real (Porto Seguro, MAPFRE) la mayoria tiene 2 numeros.

---

#### `aseguradora_taller` — Relacion entre aseguradoras y sus talleres acreditados

```sql
CREATE TABLE public.aseguradora_taller (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  aseguradora_id uuid NOT NULL REFERENCES public.aseguradora(id) ON DELETE CASCADE,
  taller_id uuid NOT NULL REFERENCES public.taller(id) ON DELETE CASCADE,
  zona text,                          -- 'Montevideo', 'Interior', 'Nacional'
  prioridad integer DEFAULT 0,        -- orden de preferencia para la aseguradora
  vigente_desde date,
  vigente_hasta date,
  activo boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (aseguradora_id, taller_id)
);
```

> Relacion muchos-a-muchos: un taller puede estar acreditado por varias aseguradoras (ej: Kostel trabaja con Porto y MAPFRE), y cada aseguradora tiene su red de talleres. `zona` y `prioridad` permiten filtrar por ubicacion y orden de preferencia.

---

#### `tarea` — Tareas y calendario interno

```sql
CREATE TABLE public.tarea (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organizacion_id uuid NOT NULL REFERENCES public.organizacion(id),
  creado_por uuid NOT NULL REFERENCES public.perfil(id),
  asignado_a uuid REFERENCES public.perfil(id),            -- nullable si no esta asignada

  titulo text NOT NULL,
  descripcion text,

  prioridad text NOT NULL DEFAULT 'media'
    CHECK (prioridad IN ('alta', 'media', 'baja')),

  estado text NOT NULL DEFAULT 'pendiente'
    CHECK (estado IN ('pendiente', 'en_progreso', 'completada', 'cancelada')),

  fecha_vencimiento date,             -- cuando vence la tarea
  fecha_completada timestamptz,

  -- Vinculacion opcional a entidades del sistema
  cliente_id uuid REFERENCES public.cliente(id),
  poliza_id uuid REFERENCES public.poliza(id),
  siniestro_id uuid REFERENCES public.siniestro(id),

  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_tarea_asignado ON public.tarea(asignado_a, estado);
CREATE INDEX idx_tarea_vencimiento ON public.tarea(organizacion_id, fecha_vencimiento)
  WHERE estado NOT IN ('completada', 'cancelada');
```

> - Soporta el calendario interno que el corredor pidio en el wireframe.
> - Las tareas como "Hacer seguro Nuevo a Juan" o "Hacer cotizacion VW Carlos" se vinculan opcionalmente a `cliente`, `poliza` o `siniestro`.
> - `prioridad` permite mostrar las tareas prioritarias en el dashboard de inicio.
> - `asignado_a` referencia a `perfil`, permitiendo asignar tareas a vendedores/corredores.

---

#### `mensaje` — Mensajeria interna

```sql
CREATE TABLE public.mensaje (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organizacion_id uuid NOT NULL REFERENCES public.organizacion(id),
  remitente_id uuid NOT NULL REFERENCES public.perfil(id),
  destinatario_id uuid NOT NULL REFERENCES public.perfil(id),

  asunto text,
  contenido text NOT NULL,
  leido boolean NOT NULL DEFAULT false,
  fecha_leido timestamptz,

  -- Vinculacion opcional a entidades
  cliente_id uuid REFERENCES public.cliente(id),
  poliza_id uuid REFERENCES public.poliza(id),
  siniestro_id uuid REFERENCES public.siniestro(id),

  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_mensaje_destinatario ON public.mensaje(destinatario_id, leido);
```

> Corresponde a "Mensajeros" del sidebar. Permite comunicacion interna entre usuarios de la misma organizacion, con referencia opcional a entidades del sistema para dar contexto al mensaje.

---

### 2.4 Row Level Security (RLS)

Cada tabla con `organizacion_id` debe tener RLS habilitado para aislar datos entre tenants:

```sql
-- Ejemplo para la tabla cliente
ALTER TABLE public.cliente ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tenant_isolation" ON public.cliente
  USING (
    organizacion_id = (
      SELECT organizacion_id FROM public.perfil WHERE id = auth.uid()
    )
  );
```

> Este patron se replica en **todas** las tablas que tengan `organizacion_id`. Garantiza que un usuario solo ve datos de su organizacion.

---

### 2.5 Triggers de auditoria

```sql
-- Funcion reutilizable para actualizar updated_at
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplicar a cada tabla (ejemplo)
CREATE TRIGGER set_updated_at
  BEFORE UPDATE ON public.cliente
  FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- Repetir para: organizacion, perfil, aseguradora, vehiculo, poliza, cuota, siniestro
```

---

## 3. Mapa de migracion

| Tabla actual | Destino en schema nuevo | Notas |
|---|---|---|
| `usuarios` | **Eliminar**. Usar `auth.users` + `perfil` | Migrar `nombre_usuario` → `perfil.nombre`, `rol` → `perfil.rol` |
| `corredor` | **Eliminar**. Absorbido por `perfil` con rol `corredor` | Migrar `corredor.nombre` → `perfil.nombre` |
| `profiles` | **Renombrar** a `perfil`, agregar campos | Agregar `organizacion_id`, `rol`, `activo` |
| `asegurados` (datos persona) | `cliente` | Migrar `nombre_asegurado` → `cliente.nombre`, `apellido_asegurado` → `cliente.apellido`, `telefono`, `numero_cliente` |
| `asegurados` (datos vehiculo) | `vehiculo` | Migrar `marca_vehiculo` → `vehiculo.marca`, `matricula` → `vehiculo.matricula` |
| `asegurados` (datos poliza) | `poliza` | Migrar `poliza` → `poliza.numero_poliza`, `tipo_seguro`, fechas de vigencia, `asegurador` → `aseguradora_id` |
| `asegurados` (datos pago) | `cuota` | Generar N registros de cuota basados en `cuotas_pagadas` + `cuotas_por_pagar` |
| `aseguradora` | `aseguradora` | Agregar `organizacion_id`, migrar `contacto` → `contactos` |
| `siniestro` | `siniestro` + `siniestro_documento` | FK cambia de `id_asegurado` a `poliza_id`. Booleanos migran a filas en `siniestro_documento` |

---

## 4. Diagrama de relaciones

```
organizacion
  │
  ├── perfil ──── auth.users
  │
  ├── aseguradora ──── aseguradora_taller (N:M) ──── taller
  │
  ├── cliente
  │     ├── vehiculo
  │     └── poliza ──┬── aseguradora
  │                  ├── vehiculo (opcional)
  │                  ├── perfil (corredor/vendedor)
  │                  ├── cuota (1..N)
  │                  └── siniestro
  │                        └── siniestro_documento (1..N)
  │
  ├── tarea ──┬── perfil (creado_por / asignado_a)
  │           └── cliente / poliza / siniestro (opcional)
  │
  ├── mensaje ── perfil (remitente / destinatario)
  │
  └── suscripcion ── plan_suscripcion
        └── pago_suscripcion
```

---

## 5. Consideraciones para el futuro

- **Renovaciones**: Cuando una poliza se renueva, crear nueva `poliza` con estado `activa` y marcar la anterior como `renovada`. Se puede agregar `poliza_anterior_id` para trazabilidad.
- **Historial de cambios**: Considerar una tabla `audit_log` con trigger generico para registrar cambios en tablas criticas.
- **Notificaciones**: Tabla `notificacion` para alertas de vencimiento de cuotas/polizas.
- **Archivos adjuntos**: Tabla generica `archivo` vinculable a cualquier entidad via polimorfismo (`entidad_tipo` + `entidad_id`) o tablas de union especificas.
- **Reportes**: Views materializadas para dashboards de cada organizacion.
- **Planes/Suscripciones SaaS**: Tabla `plan` y `suscripcion` para manejar facturacion del SaaS mismo.
