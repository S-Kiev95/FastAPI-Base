"""
Modelos del dominio de seguros.
"""
from .client import Client, ClientCreate, ClientRead, ClientUpdate
from .vehicle import Vehicle, VehicleCreate, VehicleRead, VehicleUpdate, VehicleType
from .insurer import Insurer, InsurerCreate, InsurerRead, InsurerUpdate
from .policy import Policy, PolicyCreate, PolicyRead, PolicyUpdate, InsuranceType, PolicyStatus, Currency
from .installment import Installment, InstallmentCreate, InstallmentRead, InstallmentUpdate
from .claim import Claim, ClaimCreate, ClaimRead, ClaimUpdate, DamageType, ClaimStatus
from .claim_document import ClaimDocument, ClaimDocumentCreate, ClaimDocumentRead, ClaimDocumentUpdate
from .workshop import Workshop, WorkshopCreate, WorkshopRead, WorkshopUpdate, WorkshopSpecialty
from .insurer_workshop import InsurerWorkshop, InsurerWorkshopCreate, InsurerWorkshopRead, InsurerWorkshopUpdate
from .insurance_task import InsuranceTask, InsuranceTaskCreate, InsuranceTaskRead, InsuranceTaskUpdate, TaskPriority, TaskStatus
from .message import Message, MessageCreate, MessageRead, MessageUpdate

__all__ = [
    "Client", "ClientCreate", "ClientRead", "ClientUpdate",
    "Vehicle", "VehicleCreate", "VehicleRead", "VehicleUpdate", "VehicleType",
    "Insurer", "InsurerCreate", "InsurerRead", "InsurerUpdate",
    "Policy", "PolicyCreate", "PolicyRead", "PolicyUpdate", "InsuranceType", "PolicyStatus", "Currency",
    "Installment", "InstallmentCreate", "InstallmentRead", "InstallmentUpdate",
    "Claim", "ClaimCreate", "ClaimRead", "ClaimUpdate", "DamageType", "ClaimStatus",
    "ClaimDocument", "ClaimDocumentCreate", "ClaimDocumentRead", "ClaimDocumentUpdate",
    "Workshop", "WorkshopCreate", "WorkshopRead", "WorkshopUpdate", "WorkshopSpecialty",
    "InsurerWorkshop", "InsurerWorkshopCreate", "InsurerWorkshopRead", "InsurerWorkshopUpdate",
    "InsuranceTask", "InsuranceTaskCreate", "InsuranceTaskRead", "InsuranceTaskUpdate", "TaskPriority", "TaskStatus",
    "Message", "MessageCreate", "MessageRead", "MessageUpdate",
]
