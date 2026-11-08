import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

load_dotenv()
BACKEND_DIR = Path(__file__).resolve().parents[1]
DATABASE_URL = os.environ.get("DATABASE_URL") or f"sqlite:///{BACKEND_DIR / 'complaints.db'}"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Complaint(Base):
    __tablename__ = "complaints"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    clean_text: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(20), default="form")
    customer: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)

    category: Mapped[str] = mapped_column(String(20), index=True)
    category_confidence: Mapped[float] = mapped_column(Float)
    category_scores: Mapped[dict] = mapped_column(JSON)
    sentiment: Mapped[str] = mapped_column(String(20))
    sentiment_confidence: Mapped[float] = mapped_column(Float)
    analysis: Mapped[dict] = mapped_column(JSON)       # sentiment/emotion scores, frustration
    priority: Mapped[str] = mapped_column(String(10), index=True)
    priority_score: Mapped[int] = mapped_column(Integer)
    priority_factors: Mapped[list] = mapped_column(JSON)
    department: Mapped[str] = mapped_column(String(40))
    routing_reason: Mapped[str] = mapped_column(Text)
    entities: Mapped[dict] = mapped_column(JSON)
    product: Mapped[str | None] = mapped_column(String(80), index=True)
    location: Mapped[str | None] = mapped_column(String(80), index=True)

    duplicate_group: Mapped[int | None] = mapped_column(Integer, index=True)
    duplicate_of: Mapped[int | None] = mapped_column(ForeignKey("complaints.id"))
    duplicate_similarity: Mapped[float | None] = mapped_column(Float)
    duplicate_status: Mapped[str | None] = mapped_column(String(12))  # pending / confirmed / rejected

    draft: Mapped[dict | None] = mapped_column(JSON)
    final_response: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(12), default="new", index=True)  # new / approved / rejected
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    embedding: Mapped[bytes] = mapped_column(LargeBinary)


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), index=True)
    field: Mapped[str] = mapped_column(String(20))  # category / priority / department / sentiment / response / duplicate
    predicted: Mapped[str] = mapped_column(String(200))
    corrected: Mapped[str] = mapped_column(String(200))
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


def init_db():
    Base.metadata.create_all(engine)
