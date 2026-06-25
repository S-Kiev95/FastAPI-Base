"""
Services del dominio de seguros.
"""
from .client_service import client_service
from .vehicle_service import vehicle_service
from .insurer_service import insurer_service
from .policy_service import policy_service
from .installment_service import installment_service
from .claim_service import claim_service
from .claim_document_service import claim_document_service
from .workshop_service import workshop_service
from .insurer_workshop_service import insurer_workshop_service
from .insurance_task_service import insurance_task_service
from .message_service import message_service
from .dashboard_service import dashboard_service

__all__ = [
    "client_service", "vehicle_service", "insurer_service",
    "policy_service", "installment_service", "claim_service",
    "claim_document_service", "workshop_service", "insurer_workshop_service",
    "insurance_task_service", "message_service", "dashboard_service",
]
