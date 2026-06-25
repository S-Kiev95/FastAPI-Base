"""
Service de Vehículo — CRUD + consulta por cliente.
"""
import uuid
from typing import List
from sqlmodel import Session, select
from app.models.seguros.vehicle import Vehicle, VehicleCreate, VehicleUpdate, VehicleRead
from app.services.base_service import BaseService
from app.services.websocket import vehicles_channel


class VehicleService(BaseService[Vehicle, VehicleCreate, VehicleUpdate, VehicleRead]):

    def __init__(self):
        super().__init__(
            model=Vehicle,
            channel=vehicles_channel,
            read_schema=VehicleRead,
        )

    def get_by_client(self, session: Session, cliente_id: int) -> List[Vehicle]:
        """Obtener todos los vehículos de un cliente."""
        statement = select(Vehicle).where(Vehicle.cliente_id == cliente_id)
        statement = self._apply_soft_delete_filter(statement)
        return list(session.exec(statement).all())


vehicle_service = VehicleService()
