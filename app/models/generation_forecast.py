from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    desc,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GenerationForecast(Base):
    __tablename__ = "generation_forecasts"
    __table_args__ = (
        UniqueConstraint(
            "start_time",
            "publish_time",
            "fuel_type",
            name="uq_generation_forecasts_start_publish_fuel",
        ),
        CheckConstraint(
            "generation_mw >= 0", name="ck_generation_forecasts_generation_nonnegative"
        ),
        Index(
            "ix_generation_forecasts_fuel_start_publish_desc",
            "fuel_type",
            "start_time",
            desc("publish_time"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    publish_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fuel_type: Mapped[str] = mapped_column(String(32), nullable=False)
    generation_mw: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
