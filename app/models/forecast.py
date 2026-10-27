from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Index, Numeric, UniqueConstraint, desc, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WindForecast(Base):
    __tablename__ = "wind_forecasts"
    __table_args__ = (
        UniqueConstraint("start_time", "publish_time", name="uq_wind_forecasts_start_publish"),
        CheckConstraint("generation_mw >= 0", name="ck_wind_forecasts_generation_nonnegative"),
        Index("ix_wind_forecasts_start_publish_desc", "start_time", desc("publish_time")),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    publish_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generation_mw: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
