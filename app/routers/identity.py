from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.models.identity import (
    ResolveRequest, ResolveResponse, IdentityEvent, IdentityProfile, IdentityId, IdType
)
from app.services import graph
from app.services.fingerprint import compute_fingerprint

router = APIRouter(prefix="/identity", tags=["Identity"])


@router.post("/resolve", response_model=ResolveResponse)
def resolve_identity(req: ResolveRequest, request: Request):
    # Auto-append probabilistic fingerprint from HTTP headers
    if not any(i.type == IdType.FINGERPRINT for i in req.ids):
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")
        fp = compute_fingerprint(ip, ua, request.headers.get("accept-language"))
        if fp:
            req.ids = list(req.ids) + [fp]

    try:
        profile, merged, created = graph.resolve(req.ids, req.consent)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if profile.suppressed:
        return ResolveResponse(uid=profile.uid, ids=[], suppressed=True)

    return ResolveResponse(
        uid=profile.uid,
        ids=profile.ids,
        merged=merged,
        created=created,
        match_confidence=profile.match_confidence,
    )


@router.post("/events", status_code=202)
def ingest_event(event: IdentityEvent):
    """Ingest a set of co-observed IDs (fires-and-forgets identity stitching)."""
    if not event.ids:
        raise HTTPException(status_code=400, detail="At least one ID required")
    try:
        graph.resolve(event.ids, event.consent)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "accepted"}


@router.get("", response_model=list[IdentityProfile])
def list_profiles(limit: int = 100):
    return graph.list_profiles(min(limit, 1000))


@router.get("/merges", response_model=list)
def merge_log():
    return graph.get_merge_log()


@router.get("/lookup/{id_type}/{id_value}", response_model=IdentityProfile)
def lookup_by_id(id_type: str, id_value: str):
    try:
        id_ = IdentityId(type=IdType(id_type), value=id_value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown id_type: {id_type}")
    profile = graph.get_profile_by_id(id_)
    if not profile:
        raise HTTPException(status_code=404, detail="Identity not found")
    return profile


@router.get("/{uid}", response_model=IdentityProfile)
def get_profile(uid: str):
    profile = graph.get_profile(uid)
    if not profile:
        raise HTTPException(status_code=404, detail="Identity not found")
    return profile
