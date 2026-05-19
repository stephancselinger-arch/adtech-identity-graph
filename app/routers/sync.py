from __future__ import annotations

"""
ID sync endpoints — used by DSPs and data partners to sync their user IDs
into the identity graph via pixel fires or server-side calls.
"""

from fastapi import APIRouter, HTTPException, Response

from app.models.identity import IdentityId, IdType
from app.services import graph

router = APIRouter(prefix="/sync", tags=["ID Sync"])

# 1×1 transparent GIF (standard tracking pixel response)
_PIXEL_GIF = bytes([
    0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0x01, 0x00, 0x01, 0x00,
    0x80, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x21,
    0xF9, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x2C, 0x00, 0x00,
    0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0x02, 0x02, 0x44,
    0x01, 0x00, 0x3B,
])


@router.get("/pixel")
def sync_pixel(
    response: Response,
    uid: str,
    id_type: str,
    redirect: str = "",
):
    """
    ID sync pixel.  Partner fires:
      GET /v1/sync/pixel?uid=<partner_uid>&id_type=<type>
    The server stitches the ID into the graph and optionally redirects
    back to the partner with our uid appended.
    """
    try:
        id_ = IdentityId(type=IdType(id_type), value=uid)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown id_type: {id_type}")

    try:
        graph.resolve([id_])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if redirect:
        response.status_code = 302
        response.headers["Location"] = redirect
        return

    return Response(content=_PIXEL_GIF, media_type="image/gif")


@router.get("/merge")
def merge_ids(
    id_type_a: str,
    id_value_a: str,
    id_type_b: str,
    id_value_b: str,
):
    """Explicitly merge two IDs into the same identity cluster."""
    try:
        id_a = IdentityId(type=IdType(id_type_a), value=id_value_a)
        id_b = IdentityId(type=IdType(id_type_b), value=id_value_b)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    profile, merged, created = graph.resolve([id_a, id_b])
    return {"uid": profile.uid, "merged": merged, "created": created, "id_count": len(profile.ids)}
