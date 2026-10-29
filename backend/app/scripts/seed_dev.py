import os
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Organization, User, UserRole


def _pwd(name: str) -> str:
    value = os.getenv(name)
    if value is None or value == "":
        print(f"ERROR: {name} is required to seed demo admins")
        sys.exit(1)
    if len(value) < 12:
        print(f"ERROR: {name} must be at least 12 characters long")
        sys.exit(1)
    return value


DEMO_ORG = {
    "name": "Demo Organization",
    "slug": "demo-org",
    "primary_domain": "example.test",
    "is_demo": True,
}

DEMO_ADMINS = [
    {"email": "demo-admin-1@example.test", "display_name": "Demo Admin 1", "pwd_var": "DEMO_ADMIN_1_PASSWORD"},
    {"email": "demo-admin-2@example.test", "display_name": "Demo Admin 2", "pwd_var": "DEMO_ADMIN_2_PASSWORD"},
]


def seed_dev(db: Session):
    app_env = os.getenv("APP_ENV", "development")
    env = os.getenv("ENV", "development")
    if app_env == "production" or env == "production":
        print("ERROR: Cannot run seed in production")
        sys.exit(1)

    pwd1 = _pwd("DEMO_ADMIN_1_PASSWORD")
    pwd2 = _pwd("DEMO_ADMIN_2_PASSWORD")

    org = db.execute(select(Organization).where(Organization.slug == DEMO_ORG["slug"])).scalar_one_or_none()
    if org is None:
        org = Organization(**DEMO_ORG)
        db.add(org)
        db.flush()
        db.commit()
        print("Created demo organization: Demo Organization (slug=demo-org, is_demo=true)")
    else:
        print("Demo organization already exists, skipping setup")

    passwords = {"DEMO_ADMIN_1_PASSWORD": pwd1, "DEMO_ADMIN_2_PASSWORD": pwd2}
    for admin in DEMO_ADMINS:
        pwd = passwords[admin["pwd_var"]]
        existing = db.execute(
            select(User).where(User.org_id == org.id, User.email == admin["email"])
        ).scalar_one_or_none()
        if existing is not None:
            print(f"User {admin['email']} already exists, not overwriting password or reactivating")
            continue
        user = User(
            org_id=org.id,
            email=admin["email"],
            password_hash=hash_password(pwd),
            display_name=admin["display_name"],
            role=UserRole.ADMIN,
            is_active=True,
            is_demo=True,
        )
        db.add(user)
        db.flush()
        print(f"Created demo admin: {admin['email']} (is_demo=true)")
    db.commit()
    print("Seed completed - clearly labelled demo data created")


if __name__ == "__main__":
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        seed_dev(db)
    finally:
        db.close()
