"""
Rutas del dominio de seguros.
Router padre: /api/orgs/{org_slug}/seguros
"""
from fastapi import APIRouter

from .clients import router as clients_router
from .vehicles import router as vehicles_router
from .insurers import router as insurers_router
from .policies import router as policies_router
from .installments import router as installments_router
from .claims import router as claims_router
from .workshops import router as workshops_router
from .insurance_tasks import router as insurance_tasks_router
from .messages import router as messages_router
from .dashboard import router as dashboard_router

router = APIRouter(
    prefix="/api/orgs/{org_slug}/seguros",
    tags=["seguros"],
)

router.include_router(clients_router)
router.include_router(vehicles_router)
router.include_router(insurers_router)
router.include_router(policies_router)
router.include_router(installments_router)
router.include_router(claims_router)
router.include_router(workshops_router)
router.include_router(insurance_tasks_router)
router.include_router(messages_router)
router.include_router(dashboard_router)
