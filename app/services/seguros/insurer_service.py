"""
Service de Aseguradora — CRUD estándar.
"""
from app.models.seguros.insurer import Insurer, InsurerCreate, InsurerUpdate, InsurerRead
from app.services.base_service import BaseService
from app.services.websocket import insurers_channel


class InsurerService(BaseService[Insurer, InsurerCreate, InsurerUpdate, InsurerRead]):

    def __init__(self):
        super().__init__(
            model=Insurer,
            channel=insurers_channel,
            read_schema=InsurerRead,
        )


insurer_service = InsurerService()
