import os
import sys

from sqlalchemy import select

from app.core import rate_limit
from app.core.audit import write_audit
from app.core.redis import get_redis
from app.models import User


def unlock_user(db, email: str | None = None):
    if email is None:
        email = os.getenv("UNLOCK_EMAIL")
    if not email or not email.strip():
        print("ERROR: UNLOCK_EMAIL is required (usage: make unlock-user EMAIL=<email>)")
        sys.exit(1)

    email = email.strip()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        print("ERROR: User not found")
        sys.exit(1)

    r = get_redis()
    rate_limit.clear_user_lockout(r, user.email)
    write_audit(
        db,
        org_id=user.org_id,
        actor_user_id=None,
        action="user.unlock",
        entity_type="user",
        entity_id=str(user.id),
        after={"is_active": user.is_active},
    )
    db.commit()
    print("User unlocked successfully")


if __name__ == "__main__":
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        unlock_user(db)
    finally:
        db.close()
