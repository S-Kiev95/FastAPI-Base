"""
Service de Dashboard — KPIs y estadísticas del dominio de seguros.
"""
import uuid
from datetime import date, timedelta
from sqlmodel import Session, select, func
from app.models.seguros.client import Client
from app.models.seguros.policy import Policy, PolicyStatus
from app.models.seguros.claim import Claim, ClaimStatus
from app.models.seguros.installment import Installment
from app.models.seguros.insurance_task import InsuranceTask, TaskStatus


class DashboardService:
    """Servicio de KPIs para el dashboard del portal de seguros."""

    def get_stats(self, session: Session, organization_id: uuid.UUID) -> dict:
        """Retorna KPIs principales del dominio de seguros."""

        # Total clientes activos
        total_clientes = session.exec(
            select(func.count()).select_from(Client)
            .where(Client.organization_id == organization_id)
            .where(Client.activo == True)
            .where(Client.deleted_at.is_(None))
        ).one()

        # Pólizas activas
        polizas_activas = session.exec(
            select(func.count()).select_from(Policy)
            .where(Policy.organization_id == organization_id)
            .where(Policy.estado == PolicyStatus.activa)
            .where(Policy.deleted_at.is_(None))
        ).one()

        # Siniestros abiertos
        siniestros_abiertos = session.exec(
            select(func.count()).select_from(Claim)
            .where(Claim.organization_id == organization_id)
            .where(Claim.estado.in_([ClaimStatus.abierto, ClaimStatus.en_tramite]))
            .where(Claim.deleted_at.is_(None))
        ).one()

        # Cuotas vencidas
        today = date.today()
        cuotas_vencidas = session.exec(
            select(func.count()).select_from(Installment)
            .where(Installment.organization_id == organization_id)
            .where(Installment.pagada == False)
            .where(Installment.fecha_vencimiento < today)
        ).one()

        # Pólizas por vencer (próximos 30 días)
        limit_date = today + timedelta(days=30)
        polizas_por_vencer = session.exec(
            select(func.count()).select_from(Policy)
            .where(Policy.organization_id == organization_id)
            .where(Policy.estado == PolicyStatus.activa)
            .where(Policy.vigente_hasta >= today)
            .where(Policy.vigente_hasta <= limit_date)
            .where(Policy.deleted_at.is_(None))
        ).one()

        # Prima total de pólizas activas
        prima_total = session.exec(
            select(func.coalesce(func.sum(Policy.prima_total), 0))
            .where(Policy.organization_id == organization_id)
            .where(Policy.estado == PolicyStatus.activa)
            .where(Policy.deleted_at.is_(None))
        ).one()

        # Tareas pendientes
        tareas_pendientes = session.exec(
            select(func.count()).select_from(InsuranceTask)
            .where(InsuranceTask.organization_id == organization_id)
            .where(InsuranceTask.estado.in_([TaskStatus.pendiente, TaskStatus.en_progreso]))
            .where(InsuranceTask.deleted_at.is_(None))
        ).one()

        return {
            "total_clientes": total_clientes,
            "polizas_activas": polizas_activas,
            "siniestros_abiertos": siniestros_abiertos,
            "cuotas_vencidas": cuotas_vencidas,
            "polizas_por_vencer": polizas_por_vencer,
            "prima_total": float(prima_total),
            "tareas_pendientes": tareas_pendientes,
        }

    def get_upcoming_expirations(
        self, session: Session, organization_id: uuid.UUID, days: int = 30, limit: int = 20
    ) -> list:
        """Próximas pólizas por vencer."""
        today = date.today()
        limit_date = today + timedelta(days=days)
        statement = (
            select(Policy)
            .where(Policy.organization_id == organization_id)
            .where(Policy.estado == PolicyStatus.activa)
            .where(Policy.vigente_hasta >= today)
            .where(Policy.vigente_hasta <= limit_date)
            .where(Policy.deleted_at.is_(None))
            .order_by(Policy.vigente_hasta)
            .limit(limit)
        )
        return list(session.exec(statement).all())


dashboard_service = DashboardService()
