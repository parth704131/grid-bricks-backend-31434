from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WindActual(Base):
    __tablename__ = "wind_actuals"
    __table_args__ = (CheckConstraint("generation_mw >= 0", name="ck_wind_actuals_generation_nonnegative"),)

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    generation_mw: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
