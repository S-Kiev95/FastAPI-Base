"""
Helpers para enriquecer respuestas de seguros con nombres legibles
(cliente, aseguradora, número de póliza) sin caer en N+1: cada helper hace
como máximo una query batcheada por conjunto de IDs.
"""
from typing import Dict, Iterable, Optional

from sqlmodel import Session, select

from app.models.seguros.client import Client
from app.models.seguros.insurer import Insurer
from app.models.seguros.policy import Policy
from app.models.user import User


def _ids(values: Iterable) -> set:
    return {v for v in values if v is not None}


def client_names(session: Session, ids: Iterable[int]) -> Dict[int, str]:
    """{cliente_id: 'Nombre Apellido'}"""
    ids = _ids(ids)
    if not ids:
        return {}
    rows = session.exec(select(Client).where(Client.id.in_(ids))).all()
    return {c.id: f"{c.nombre} {c.apellido}".strip() for c in rows}


def insurer_names(session: Session, ids: Iterable[int]) -> Dict[int, str]:
    """{aseguradora_id: 'Nombre'}"""
    ids = _ids(ids)
    if not ids:
        return {}
    rows = session.exec(select(Insurer).where(Insurer.id.in_(ids))).all()
    return {i.id: i.nombre for i in rows}


def user_names(session: Session, ids: Iterable[int]) -> Dict[int, str]:
    """{user_id: 'Nombre' o email si no tiene nombre}"""
    ids = _ids(ids)
    if not ids:
        return {}
    rows = session.exec(select(User).where(User.id.in_(ids))).all()
    return {u.id: (u.name or u.email) for u in rows}


def policy_map(session: Session, ids: Iterable[int]) -> Dict[int, Policy]:
    """{poliza_id: Policy} — para obtener numero_poliza y cliente_id."""
    ids = _ids(ids)
    if not ids:
        return {}
    rows = session.exec(select(Policy).where(Policy.id.in_(ids))).all()
    return {p.id: p for p in rows}


def enrich_policies(session: Session, policies: list) -> list:
    """Serializa pólizas agregando cliente_nombre y aseguradora_nombre."""
    from app.models.seguros.policy import PolicyRead
    cnames = client_names(session, (p.cliente_id for p in policies))
    inames = insurer_names(session, (p.aseguradora_id for p in policies))
    out = []
    for p in policies:
        d = PolicyRead.model_validate(p).model_dump()
        d["cliente_nombre"] = cnames.get(p.cliente_id)
        d["aseguradora_nombre"] = inames.get(p.aseguradora_id)
        out.append(d)
    return out


def enrich_claims(session: Session, claims: list) -> list:
    """Serializa siniestros agregando poliza_numero, cliente_nombre y aseguradora_nombre."""
    from app.models.seguros.claim import ClaimRead
    pmap = policy_map(session, (c.poliza_id for c in claims))
    cnames = client_names(session, (p.cliente_id for p in pmap.values()))
    inames = insurer_names(session, (c.aseguradora_id for c in claims))
    out = []
    for c in claims:
        d = ClaimRead.model_validate(c).model_dump()
        pol = pmap.get(c.poliza_id)
        d["poliza_numero"] = pol.numero_poliza if pol else None
        d["cliente_nombre"] = cnames.get(pol.cliente_id) if pol else None
        d["aseguradora_nombre"] = inames.get(c.aseguradora_id)
        out.append(d)
    return out


def enrich_messages(session: Session, messages: list) -> list:
    """Serializa mensajes agregando remitente_nombre y destinatario_nombre."""
    from app.models.seguros.message import MessageRead
    unames = user_names(
        session,
        [m.remitente_id for m in messages] + [m.destinatario_id for m in messages],
    )
    out = []
    for m in messages:
        d = MessageRead.model_validate(m).model_dump()
        d["remitente_nombre"] = unames.get(m.remitente_id)
        d["destinatario_nombre"] = unames.get(m.destinatario_id)
        out.append(d)
    return out


def enrich_installments(session: Session, installments: list) -> list:
    """Serializa cuotas agregando poliza_numero y cliente_nombre."""
    from app.models.seguros.installment import InstallmentRead
    pmap = policy_map(session, (i.poliza_id for i in installments))
    cnames = client_names(session, (p.cliente_id for p in pmap.values()))
    out = []
    for inst in installments:
        d = InstallmentRead.model_validate(inst).model_dump()
        pol = pmap.get(inst.poliza_id)
        d["poliza_numero"] = pol.numero_poliza if pol else None
        d["cliente_nombre"] = cnames.get(pol.cliente_id) if pol else None
        out.append(d)
    return out
