"""
Service de Cuota — CRUD + vencidas + marcar pagada + generar cuotas.
"""
import uuid
from datetime import date, datetime, timezone
from typing import List
from dateutil.relativedelta import relativedelta
from sqlmodel import Session, select
from app.models.seguros.installment import Installment, InstallmentCreate, InstallmentUpdate, InstallmentRead
from app.models.seguros.policy import Policy
from app.services.base_service import BaseService
from app.services.websocket import installments_channel


class InstallmentService(BaseService[Installment, InstallmentCreate, InstallmentUpdate, InstallmentRead]):

    def __init__(self):
        super().__init__(
            model=Installment,
            channel=installments_channel,
            read_schema=InstallmentRead,
        )

    def get_by_policy(self, session: Session, poliza_id: int) -> List[Installment]:
        """Cuotas de una póliza, ordenadas por número."""
        statement = (
            select(Installment)
            .where(Installment.poliza_id == poliza_id)
            .order_by(Installment.numero_cuota)
        )
        return list(session.exec(statement).all())

    def get_overdue(
        self, session: Session, organization_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[Installment]:
        """Cuotas vencidas (no pagadas con fecha_vencimiento pasada)."""
        today = date.today()
        statement = (
            select(Installment)
            .where(Installment.organization_id == organization_id)
            .where(Installment.pagada == False)  # noqa: E712
            .where(Installment.fecha_vencimiento < today)
            .order_by(Installment.fecha_vencimiento)
            .offset(skip)
            .limit(limit)
        )
        return list(session.exec(statement).all())

    async def mark_paid(
        self, session: Session, installment_id: int, fecha_pago: date, metodo_pago: str = None
    ) -> Installment:
        """Marcar una cuota como pagada."""
        obj = session.get(Installment, installment_id)
        if not obj:
            return None
        obj.pagada = True
        obj.fecha_pago = fecha_pago
        if metodo_pago:
            obj.metodo_pago = metodo_pago
        obj.updated_at = datetime.now(timezone.utc)
        session.add(obj)
        session.commit()
        session.refresh(obj)
        await self.channel.broadcast_updated(
            InstallmentRead.model_validate(obj).model_dump()
        )
        return obj

    async def generate_installments(self, session: Session, policy: Policy) -> List[Installment]:
        """Genera N cuotas a partir de los datos de la póliza."""
        if not policy.prima_total or policy.total_cuotas < 1:
            return []

        monto_cuota = round(policy.prima_total / policy.total_cuotas, 2)
        installments = []

        for i in range(1, policy.total_cuotas + 1):
            fecha = policy.vigente_desde + relativedelta(months=i - 1)
            data = InstallmentCreate(
                organization_id=policy.organization_id,
                poliza_id=policy.id,
                numero_cuota=i,
                monto=monto_cuota,
                fecha_vencimiento=fecha,
            )
            inst = await self.create(session, data, broadcast=False)
            installments.append(inst)

        return installments


installment_service = InstallmentService()
