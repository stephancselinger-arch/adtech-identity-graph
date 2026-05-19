from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.identity import IdentityId, IdType
from app.models.privacy import DeletionRequest, DeletionResult, ConsentUpdate, SuppressCheck
from app.services import graph
from app.services import privacy as privacy_svc

router = APIRouter(prefix="/privacy", tags=["Privacy & Consent"])


@router.post("/delete", response_model=DeletionResult)
def delete_identity(req: DeletionRequest):
    """GDPR right-to-be-forgotten: removes all IDs and adds them to suppression list."""
    if req.uid:
        uid, count = privacy_svc.delete_by_uid(req.uid)
    elif req.id_type and req.id_value:
        uid, count = privacy_svc.delete_by_id(req.id_type, req.id_value)
        if uid is None:
            raise HTTPException(status_code=404, detail="Identity not found")
    else:
        raise HTTPException(status_code=400, detail="Provide uid or id_type+id_value")
    return DeletionResult(uid=uid, ids_deleted=count, success=True)


@router.post("/consent")
def update_consent(req: ConsentUpdate):
    """Update GDPR / CCPA consent signals for an identity."""
    data = req.model_dump(exclude={"uid"}, exclude_none=True)
    profile = privacy_svc.update_consent(req.uid, data)
    if not profile:
        raise HTTPException(status_code=404, detail="Identity not found")
    return {"uid": req.uid, "consent": profile.consent}


@router.post("/suppress")
def suppress_id(id_type: str, id_value: str):
    """Add a specific ID to the suppression list without full deletion."""
    try:
        id_ = IdentityId(type=IdType(id_type), value=id_value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown id_type: {id_type}")
    graph.suppress_id(id_)
    return {"suppressed": True, "id_type": id_type, "id_value": id_value}


@router.get("/suppressed/{id_type}/{id_value}", response_model=SuppressCheck)
def check_suppressed(id_type: str, id_value: str):
    try:
        id_ = IdentityId(type=IdType(id_type), value=id_value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown id_type: {id_type}")
    return SuppressCheck(
        id_type=id_type,
        id_value=id_value,
        suppressed=graph.is_suppressed(id_),
    )
