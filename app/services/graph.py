from __future__ import annotations

"""
Union-Find identity graph.

Each (type, value) pair is a node. Nodes that have been observed together
are grouped into the same cluster via union-by-rank with path compression.
Every cluster has a canonical UID whose IdentityProfile holds all IDs.
"""

from datetime import datetime, timezone

from app.models.identity import IdentityId, IdentityProfile, MergeRecord, ConsentSignals

# ── State (module-level so tests can clear it) ────────────────────────────────

# "type:value" -> uid (not necessarily root; use _find to get root)
_node_to_uid: dict[str, str] = {}

# Union-Find: uid -> parent uid (root points to itself)
_parent: dict[str, str] = {}
_rank: dict[str, int] = {}

# uid -> IdentityProfile (only root UIDs are valid keys)
_profiles: dict[str, IdentityProfile] = {}

# Audit log of cluster merges
_merge_log: list[MergeRecord] = []

# Suppressed node keys (IDs that must not be resolved)
_suppressed: set[str] = set()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _key(id_: IdentityId) -> str:
    return f"{id_.type.value}:{id_.value}"


def _find(uid: str) -> str:
    """Path-compressing find — returns root uid."""
    root = _parent.get(uid, uid)
    if root != uid:
        _parent[uid] = _find(root)
        return _parent[uid]
    return uid


def _union(uid_a: str, uid_b: str) -> tuple[str, str]:
    """Union by rank. Returns (survivor_root, absorbed_root)."""
    root_a = _find(uid_a)
    root_b = _find(uid_b)
    if root_a == root_b:
        return root_a, root_a
    if _rank.get(root_a, 0) < _rank.get(root_b, 0):
        root_a, root_b = root_b, root_a
    _parent[root_b] = root_a
    if _rank.get(root_a, 0) == _rank.get(root_b, 0):
        _rank[root_a] = _rank.get(root_a, 0) + 1
    return root_a, root_b


# ── Public API ────────────────────────────────────────────────────────────────

def resolve(
    ids: list[IdentityId],
    consent: ConsentSignals | None = None,
) -> tuple[IdentityProfile, bool, bool]:
    """
    Resolve a set of co-observed IDs to a unified profile.

    Returns (profile, merged, created).
    Raises ValueError if all provided IDs are suppressed.
    """
    if not ids:
        raise ValueError("At least one ID required")

    active = [i for i in ids if _key(i) not in _suppressed]
    if not active:
        raise ValueError("All provided IDs are suppressed")

    # Find which existing clusters each ID belongs to
    existing_roots: list[str] = []
    new_ids: list[IdentityId] = []
    for id_ in active:
        k = _key(id_)
        if k in _node_to_uid:
            existing_roots.append(_find(_node_to_uid[k]))
        else:
            new_ids.append(id_)

    # Deduplicate while preserving first-seen order
    seen: dict[str, None] = {}
    for r in existing_roots:
        seen[r] = None
    unique_roots = list(seen)

    merged = False
    created = False

    if not unique_roots:
        # Brand-new identity
        profile = IdentityProfile(ids=list(active), consent=consent)
        uid = profile.uid
        _profiles[uid] = profile
        _parent[uid] = uid
        _rank[uid] = 0
        for id_ in active:
            _node_to_uid[_key(id_)] = uid
        created = True
        return profile, merged, created

    # Merge all found clusters into one
    survivor = unique_roots[0]
    for other in unique_roots[1:]:
        r_other = _find(other)
        r_survivor = _find(survivor)
        if r_other == r_survivor:
            continue
        new_root, absorbed = _union(r_survivor, r_other)
        survivor = new_root
        _merge_clusters(new_root, absorbed, ids)
        merged = True

    # Attach any new IDs to the surviving cluster
    canonical = _find(survivor)
    profile = _profiles[canonical]
    existing_keys = {_key(i) for i in profile.ids}
    for id_ in new_ids:
        k = _key(id_)
        if k not in existing_keys:
            profile.ids.append(id_)
            existing_keys.add(k)
        _node_to_uid[k] = canonical

    if new_ids or consent:
        profile.updated_at = datetime.now(timezone.utc)
    if consent:
        profile.consent = consent

    return profile, merged, created


def _merge_clusters(survivor: str, absorbed: str, trigger_ids: list[IdentityId]) -> None:
    s_profile = _profiles[survivor]
    a_profile = _profiles.pop(absorbed, None)
    if not a_profile:
        return
    existing_keys = {_key(i) for i in s_profile.ids}
    for id_ in a_profile.ids:
        k = _key(id_)
        if k not in existing_keys:
            s_profile.ids.append(id_)
            existing_keys.add(k)
    s_profile.updated_at = datetime.now(timezone.utc)
    _merge_log.append(MergeRecord(
        survivor_uid=survivor,
        absorbed_uid=absorbed,
        trigger_ids=trigger_ids,
    ))


def get_profile(uid: str) -> IdentityProfile | None:
    return _profiles.get(_find(uid))


def get_profile_by_id(id_: IdentityId) -> IdentityProfile | None:
    uid = _node_to_uid.get(_key(id_))
    if uid is None:
        return None
    return _profiles.get(_find(uid))


def delete_identity(uid: str) -> tuple[str, int]:
    """
    Remove all IDs for a uid and add them to the suppression list.
    Returns (canonical_uid, ids_deleted).
    """
    root = _find(uid)
    profile = _profiles.get(root)
    if not profile:
        return uid, 0
    count = len(profile.ids)
    for id_ in profile.ids:
        k = _key(id_)
        _node_to_uid.pop(k, None)
        _suppressed.add(k)
    del _profiles[root]
    _parent.pop(root, None)
    _rank.pop(root, None)
    return root, count


def suppress_id(id_: IdentityId) -> None:
    _suppressed.add(_key(id_))


def is_suppressed(id_: IdentityId) -> bool:
    return _key(id_) in _suppressed


def get_merge_log() -> list[MergeRecord]:
    return list(_merge_log)


def list_profiles(limit: int = 100) -> list[IdentityProfile]:
    return list(_profiles.values())[:limit]
