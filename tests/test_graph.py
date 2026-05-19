from __future__ import annotations

import pytest

from app.models.identity import IdentityId, IdType
from app.services import graph


def _id(type_: str, value: str) -> IdentityId:
    return IdentityId(type=IdType(type_), value=value)


def setup_function():
    graph._node_to_uid.clear()
    graph._parent.clear()
    graph._rank.clear()
    graph._profiles.clear()
    graph._merge_log.clear()
    graph._suppressed.clear()


# ── Basic creation ────────────────────────────────────────────────────────────

def test_new_ids_create_profile():
    ids = [_id("cookie", "ck1"), _id("device", "dev1")]
    profile, merged, created = graph.resolve(ids)
    assert created
    assert not merged
    assert len(profile.ids) == 2


def test_same_ids_return_same_uid():
    p1, _, _ = graph.resolve([_id("cookie", "ck2")])
    p2, _, _ = graph.resolve([_id("cookie", "ck2")])
    assert p1.uid == p2.uid


def test_new_id_added_to_existing_profile():
    p1, _, _ = graph.resolve([_id("cookie", "ck3")])
    p2, _, _ = graph.resolve([_id("cookie", "ck3"), _id("email_hash", "em3")])
    assert p1.uid == p2.uid
    assert len(p2.ids) == 2


# ── Cluster merging ───────────────────────────────────────────────────────────

def test_merge_two_separate_clusters():
    p1, _, _ = graph.resolve([_id("cookie", "ck4")])
    p2, _, _ = graph.resolve([_id("email_hash", "em4")])
    assert p1.uid != p2.uid

    merged_profile, merged, created = graph.resolve([
        _id("cookie", "ck4"),
        _id("email_hash", "em4"),
    ])
    assert merged
    assert not created
    types = {i.type for i in merged_profile.ids}
    assert IdType.COOKIE in types
    assert IdType.EMAIL_HASH in types


def test_three_way_merge():
    graph.resolve([_id("cookie", "a")])
    graph.resolve([_id("device", "b")])
    graph.resolve([_id("ppid", "c")])
    merged_profile, merged, _ = graph.resolve([
        _id("cookie", "a"), _id("device", "b"), _id("ppid", "c"),
    ])
    assert merged
    assert len(merged_profile.ids) == 3


def test_merge_logged():
    graph.resolve([_id("cookie", "log1")])
    graph.resolve([_id("device", "log2")])
    graph.resolve([_id("cookie", "log1"), _id("device", "log2")])
    assert len(graph.get_merge_log()) >= 1


# ── Lookup ────────────────────────────────────────────────────────────────────

def test_get_profile_by_uid():
    profile, _, _ = graph.resolve([_id("cookie", "lookup1")])
    fetched = graph.get_profile(profile.uid)
    assert fetched is not None
    assert fetched.uid == profile.uid


def test_get_profile_by_id():
    profile, _, _ = graph.resolve([_id("uid2", "u2_1")])
    fetched = graph.get_profile_by_id(_id("uid2", "u2_1"))
    assert fetched is not None
    assert fetched.uid == profile.uid


def test_unknown_uid_returns_none():
    assert graph.get_profile("uid_does_not_exist") is None


# ── Deletion & suppression ────────────────────────────────────────────────────

def test_delete_removes_profile():
    profile, _, _ = graph.resolve([_id("cookie", "del1")])
    uid, count = graph.delete_identity(profile.uid)
    assert count == 1
    assert graph.get_profile(uid) is None


def test_deleted_ids_are_suppressed():
    profile, _, _ = graph.resolve([_id("cookie", "del2")])
    graph.delete_identity(profile.uid)
    assert graph.is_suppressed(_id("cookie", "del2"))


def test_suppressed_id_raises():
    graph.suppress_id(_id("cookie", "sup1"))
    with pytest.raises(ValueError):
        graph.resolve([_id("cookie", "sup1")])


def test_suppress_check():
    id_ = _id("device", "chk1")
    assert not graph.is_suppressed(id_)
    graph.suppress_id(id_)
    assert graph.is_suppressed(id_)
