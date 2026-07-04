"""
Seed de datos de demostración para el dominio de seguros.

Crea aseguradoras, talleres, clientes con vehículos, pólizas con cuotas,
siniestros y tareas para una organización, de modo que el portal se vea
poblado y los KPIs del dashboard den valores reales.

Las fechas son relativas a hoy (date.today()) para que siempre haya pólizas
"por vencer" y cuotas "vencidas" sin importar cuándo se ejecute.

Uso:
    uv run python -m app.services.seguros.seed                # org por defecto: seguros-bk
    uv run python -m app.services.seguros.seed --org otra-org
    uv run python -m app.services.seguros.seed --force        # borra datos previos de la org y recarga
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta

from sqlmodel import Session, select

from app.database import engine
from app.models.organization import Organization, Membership
from app.models.seguros.insurer import Insurer
from app.models.seguros.workshop import Workshop, WorkshopSpecialty
from app.models.seguros.client import Client
from app.models.seguros.vehicle import Vehicle, VehicleType
from app.models.seguros.policy import Policy, InsuranceType, PolicyStatus, Currency
from app.models.seguros.installment import Installment
from app.models.seguros.claim import Claim, DamageType, ClaimStatus
from app.models.seguros.insurance_task import InsuranceTask, TaskPriority, TaskStatus
from app.models.seguros.message import Message


# Tablas del dominio que se limpian con --force (orden respeta FKs)
_SEGUROS_TABLES = [
    Message, InsuranceTask, Claim, Installment, Policy, Vehicle, Client, Workshop, Insurer
]


def _resolve_org_and_user(session: Session, org_slug: str):
    org = session.exec(select(Organization).where(Organization.slug == org_slug)).first()
    if not org:
        raise SystemExit(f"[ERROR] No existe la organización con slug '{org_slug}'.")

    membership = session.exec(
        select(Membership).where(Membership.organization_id == org.id)
    ).first()
    if not membership:
        raise SystemExit(f"[ERROR] La organización '{org_slug}' no tiene miembros (no hay corredor).")

    return org, membership.user_id


def _wipe(session: Session, org_id) -> None:
    for model in _SEGUROS_TABLES:
        rows = session.exec(select(model).where(model.organization_id == org_id)).all()
        for r in rows:
            session.delete(r)
    session.commit()


def seed_seguros_demo(org_slug: str = "seguros-bk", force: bool = False) -> dict:
    """Carga datos de demo para la organización indicada. Devuelve un resumen de conteos."""
    today = date.today()

    with Session(engine) as session:
        org, corredor_id = _resolve_org_and_user(session, org_slug)
        oid = org.id

        existing = session.exec(select(Client).where(Client.organization_id == oid)).first()
        if existing and not force:
            raise SystemExit(
                f"[ABORTADO] La organización '{org_slug}' ya tiene datos de seguros. "
                f"Usá --force para borrarlos y recargar."
            )
        if force:
            _wipe(session, oid)

        # ── Aseguradoras ─────────────────────────────────────────────
        aseguradoras = [
            Insurer(organization_id=oid, nombre="Banco de Seguros del Estado",
                    telefono="2908 0000", email="contacto@bse.com.uy", direccion="Av. Libertador 1465, Montevideo"),
            Insurer(organization_id=oid, nombre="Sura Seguros",
                    telefono="2902 1234", email="info@sura.com.uy", direccion="Br. Artigas 1234, Montevideo"),
            Insurer(organization_id=oid, nombre="Mapfre Uruguay",
                    telefono="2487 5500", email="atencion@mapfre.com.uy", direccion="Av. Italia 2356, Montevideo"),
            Insurer(organization_id=oid, nombre="Porto Seguro",
                    telefono="2600 7788", email="clientes@portoseguro.com.uy", direccion="26 de Marzo 3456, Montevideo"),
        ]
        session.add_all(aseguradoras)
        session.flush()

        # ── Talleres ─────────────────────────────────────────────────
        talleres = [
            Workshop(organization_id=oid, nombre="Taller Centro", departamento="Montevideo",
                     ciudad="Montevideo", telefono="2901 2233", especialidad=WorkshopSpecialty.chapa_pintura,
                     marcas_atendidas="Chevrolet,Fiat,Volkswagen", horario="Lun-Vie 8-18"),
            Workshop(organization_id=oid, nombre="Mecánica del Sur", departamento="Canelones",
                     ciudad="Las Piedras", telefono="2364 5566", especialidad=WorkshopSpecialty.mecanica,
                     marcas_atendidas="Toyota,Nissan,Hyundai", horario="Lun-Sab 8-17"),
            Workshop(organization_id=oid, nombre="Cristales Express", departamento="Montevideo",
                     ciudad="Montevideo", telefono="2200 9988", especialidad=WorkshopSpecialty.cristales,
                     marcas_atendidas="Multimarca", horario="Lun-Vie 9-19"),
        ]
        session.add_all(talleres)
        session.flush()

        # ── Clientes + vehículos ─────────────────────────────────────
        # (nombre, apellido, doc, tel, email, marca, modelo, anio, matricula, tipo, color)
        clientes_data = [
            ("María", "González", "3.456.789-0", "099 111 222", "maria.gonzalez@mail.com",
             "Chevrolet", "Onix", 2021, "SAB1234", VehicleType.auto, "Gris"),
            ("Juan", "Pérez", "4.123.456-7", "098 333 444", "juan.perez@mail.com",
             "Volkswagen", "Gol", 2019, "SAC5678", VehicleType.auto, "Blanco"),
            ("Lucía", "Rodríguez", "2.987.654-3", "091 555 666", "lucia.rodriguez@mail.com",
             "Yamaha", "FZ", 2022, "SBM9012", VehicleType.moto, "Azul"),
            ("Diego", "Fernández", "5.234.567-8", "094 777 888", "diego.fernandez@mail.com",
             "Toyota", "Hilux", 2020, "SAD3456", VehicleType.camion, "Negro"),
            ("Sofía", "Martínez", "3.765.432-1", "099 999 000", "sofia.martinez@mail.com",
             "Fiat", "Cronos", 2023, "SAE7890", VehicleType.auto, "Rojo"),
            ("Andrés", "López", "4.876.543-2", "092 222 111", "andres.lopez@mail.com",
             "Nissan", "Frontier", 2018, "SAF2345", VehicleType.utilitario, "Plata"),
        ]
        clientes: list[Client] = []
        vehiculos: list[Vehicle] = []
        for i, (nom, ape, doc, tel, email, marca, modelo, anio, mat, tipo, color) in enumerate(clientes_data, 1):
            c = Client(organization_id=oid, numero_cliente=f"CL-{i:04d}", nombre=nom, apellido=ape,
                       documento_identidad=doc, telefono=tel, email=email,
                       direccion=f"Calle {100 + i} esq. Avenida {i}", activo=True)
            session.add(c)
            session.flush()
            clientes.append(c)
            v = Vehicle(organization_id=oid, cliente_id=c.id, marca=marca, modelo=modelo,
                        anio=anio, matricula=mat, tipo=tipo, color=color)
            session.add(v)
            session.flush()
            vehiculos.append(v)

        # ── Pólizas ──────────────────────────────────────────────────
        # vence_en_dias controla el estado por-vencer/vigente; estado fija casos especiales.
        # (cliente_idx, aseg_idx, tipo, numero, prima, moneda, cuotas, vence_en_dias, estado)
        polizas_data = [
            (0, 0, InsuranceType.auto, "POL-2026-0001", 48000.0, Currency.UYU, 10, 15,  PolicyStatus.activa),
            (1, 1, InsuranceType.auto, "POL-2026-0002", 36000.0, Currency.UYU, 6,  25,  PolicyStatus.activa),
            (2, 2, InsuranceType.moto, "POL-2026-0003", 12000.0, Currency.UYU, 4,  200, PolicyStatus.activa),
            (3, 0, InsuranceType.auto, "POL-2026-0004", 95000.0, Currency.UYU, 12, 340, PolicyStatus.activa),
            (4, 3, InsuranceType.auto, "POL-2026-0005", 52000.0, Currency.UYU, 10, 90,  PolicyStatus.activa),
            (5, 1, InsuranceType.responsabilidad_civil, "POL-2026-0006", 28000.0, Currency.UYU, 6, -10, PolicyStatus.vencida),
        ]
        polizas: list[Policy] = []
        for cli_idx, aseg_idx, tipo, numero, prima, moneda, cuotas, vence_en, estado in polizas_data:
            cli = clientes[cli_idx]
            veh = vehiculos[cli_idx]
            vigente_hasta = today + timedelta(days=vence_en)
            vigente_desde = vigente_hasta - timedelta(days=365)
            p = Policy(
                organization_id=oid, cliente_id=cli.id, vehiculo_id=veh.id,
                aseguradora_id=aseguradoras[aseg_idx].id, corredor_id=corredor_id,
                numero_poliza=numero, tipo_seguro=tipo, vigente_desde=vigente_desde,
                vigente_hasta=vigente_hasta, prima_total=prima, moneda=moneda,
                total_cuotas=cuotas, estado=estado,
                notas="Póliza de demostración generada por el seed.",
            )
            session.add(p)
            session.flush()
            polizas.append(p)

            # Cuotas: monto = prima/cuotas, vencimiento mensual desde vigente_desde.
            # Marca como pagadas las que vencieron hace tiempo; deja 1-2 vencidas impagas.
            monto = round(prima / cuotas, 2)
            for n in range(1, cuotas + 1):
                fv = vigente_desde + timedelta(days=30 * n)
                vencida = fv < today
                # Dejar impagas las 2 cuotas vencidas más recientes para generar "cuotas vencidas"
                pagada = vencida and fv < (today - timedelta(days=60))
                inst = Installment(
                    organization_id=oid, poliza_id=p.id, numero_cuota=n, monto=monto,
                    fecha_vencimiento=fv,
                    fecha_pago=(fv if pagada else None),
                    pagada=pagada,
                    metodo_pago=("transferencia" if pagada else None),
                )
                session.add(inst)
        session.flush()

        # ── Siniestros ───────────────────────────────────────────────
        # (poliza_idx, tipo_dano, estado, reclamado, liquidado, ocurrencia_hace_dias, desc)
        siniestros_data = [
            (0, DamageType.dano_tercero, ClaimStatus.abierto,   85000.0, None,     12,
             "Colisión en intersección, daños a tercero."),
            (1, DamageType.robo_parcial, ClaimStatus.en_tramite, 40000.0, None,     30,
             "Robo de estéreo y espejos en estacionamiento."),
            (3, DamageType.dano_propio,  ClaimStatus.liquidado,  120000.0, 110000.0, 95,
             "Despiste en ruta, daños en chapa y pintura."),
        ]
        siniestros: list[Claim] = []
        for idx, (pol_idx, tipo_dano, estado, reclamado, liquidado, hace, desc) in enumerate(siniestros_data, 1):
            pol = polizas[pol_idx]
            ocurrencia = today - timedelta(days=hace)
            s = Claim(
                organization_id=oid, poliza_id=pol.id, aseguradora_id=pol.aseguradora_id,
                numero_siniestro=f"SIN-2026-{idx:04d}", fecha_ocurrencia=ocurrencia,
                fecha_denuncia=ocurrencia + timedelta(days=1), tipo_dano=tipo_dano,
                estado=estado, monto_reclamado=reclamado, monto_liquidado=liquidado,
                descripcion=desc,
            )
            session.add(s)
            session.flush()
            siniestros.append(s)

        # ── Tareas ───────────────────────────────────────────────────
        tareas_data = [
            ("Renovar póliza POL-2026-0001", "Contactar al cliente, vence pronto.",
             TaskPriority.alta, TaskStatus.pendiente, 5, clientes[0].id, polizas[0].id, None),
            ("Gestionar siniestro SIN-2026-0001", "Solicitar fotos y presupuesto al taller.",
             TaskPriority.alta, TaskStatus.en_progreso, 3, None, None, siniestros[0].id),
            ("Cobrar cuotas vencidas", "Llamar a clientes con cuotas impagas.",
             TaskPriority.media, TaskStatus.pendiente, 2, None, None, None),
            ("Enviar documentación a BSE", "Adjuntar denuncia del siniestro en trámite.",
             TaskPriority.media, TaskStatus.en_progreso, 7, None, None, siniestros[1].id),
            ("Actualizar datos de cliente", "Verificar teléfono y email de Sofía Martínez.",
             TaskPriority.baja, TaskStatus.completada, -2, clientes[4].id, None, None),
        ]
        for titulo, descr, prioridad, estado, vence_en, cli_id, pol_id, sin_id in tareas_data:
            t = InsuranceTask(
                organization_id=oid, creado_por=corredor_id, asignado_a=corredor_id,
                titulo=titulo, descripcion=descr, prioridad=prioridad, estado=estado,
                fecha_vencimiento=today + timedelta(days=vence_en),
                fecha_completada=(datetime.utcnow() if estado == TaskStatus.completada else None),
                cliente_id=cli_id, poliza_id=pol_id, siniestro_id=sin_id,
            )
            session.add(t)

        # ── Mensajes internos (remitente = destinatario = corredor, demo) ──
        mensajes = [
            Message(organization_id=oid, remitente_id=corredor_id, destinatario_id=corredor_id,
                    asunto="Bienvenido al portal", contenido="Datos de demostración cargados correctamente.",
                    leido=False),
            Message(organization_id=oid, remitente_id=corredor_id, destinatario_id=corredor_id,
                    asunto="Recordatorio", contenido="Revisar pólizas próximas a vencer esta semana.",
                    leido=False, poliza_id=polizas[0].id),
        ]
        session.add_all(mensajes)

        session.commit()

        resumen = {
            "aseguradoras": len(aseguradoras),
            "talleres": len(talleres),
            "clientes": len(clientes),
            "vehiculos": len(vehiculos),
            "polizas": len(polizas),
            "cuotas": session.exec(select(Installment).where(Installment.organization_id == oid)).all().__len__(),
            "siniestros": len(siniestros),
            "tareas": len(tareas_data),
            "mensajes": len(mensajes),
        }
        return resumen


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed de datos de demo para el portal de seguros.")
    parser.add_argument("--org", default="seguros-bk", help="Slug de la organización (default: seguros-bk)")
    parser.add_argument("--force", action="store_true", help="Borra los datos de seguros previos de la org y recarga")
    args = parser.parse_args()

    resumen = seed_seguros_demo(org_slug=args.org, force=args.force)
    print(f"[OK] Datos de demo cargados en la organización '{args.org}':")
    for k, v in resumen.items():
        print(f"  - {k}: {v}")


if __name__ == "__main__":
    main()
