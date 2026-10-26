import uuid

from sqlalchemy import Boolean, text
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(nullable=False)
    slug: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    primary_domain: Mapped[str] = mapped_column(CITEXT, nullable=False)
    is_demo: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
