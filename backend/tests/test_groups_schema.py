"""M3 schema guards: org scoping, uniqueness and cascade behaviour."""

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models import Group, GroupMember, Organization, Target


def test_groups_targets_membership_tables_exist(db_session):
    tables = set(
        db_session.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            )
        ).scalars()
    )
    assert {"groups", "targets", "group_members"}.issubset(tables)


def test_target_email_unique_per_org(db_session, organization):
    db_session.add(Target(org_id=organization.id, email="same@example.test"))
    db_session.add(Target(org_id=organization.id, email="same@example.test"))
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_same_target_email_allowed_in_different_orgs(db_session, organization):
    other = Organization(
        name="Other", slug="cascade-other", primary_domain="other.example.test"
    )
    db_session.add(other)
    db_session.flush()
    db_session.add(Target(org_id=organization.id, email="shared@example.test"))
    db_session.add(Target(org_id=other.id, email="shared@example.test"))
    db_session.flush()
    shared = db_session.execute(
        select(Target).where(Target.email == "shared@example.test")
    ).scalars().all()
    assert len(shared) == 2


def test_deleting_group_cascades_memberships_only(db_session, organization):
    group = Group(org_id=organization.id, name="Cascade")
    target = Target(org_id=organization.id, email="cascade@example.test")
    db_session.add_all([group, target])
    db_session.flush()
    db_session.add(GroupMember(group_id=group.id, target_id=target.id))
    db_session.flush()

    db_session.delete(group)
    db_session.flush()
    assert (
        db_session.execute(
            select(GroupMember).where(GroupMember.target_id == target.id)
        ).scalars().all()
        == []
    )
    remaining = db_session.execute(
        select(Target).where(Target.id == target.id)
    ).scalar_one_or_none()
    assert remaining is not None
