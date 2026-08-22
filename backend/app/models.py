from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    orcid: Mapped[str] = mapped_column(String(19), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    doi: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    pdf_filename: Mapped[str] = mapped_column(String(200))
    version: Mapped[int] = mapped_column(Integer, default=1)
    topics_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # OpenAlex topics
    uploaded_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    authors: Mapped[list["DocumentAuthor"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="DocumentAuthor.position"
    )
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentAuthor(Base):
    __tablename__ = "document_authors"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200))
    orcid: Mapped[Optional[str]] = mapped_column(String(19), nullable=True)
    affiliation: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    document: Mapped[Document] = relationship(back_populates="authors")


class ReviewerAlias(Base):
    """Per-document pseudonym + cached conflict-of-interest status for a commenter."""

    __tablename__ = "reviewer_aliases"
    __table_args__ = (
        UniqueConstraint("document_id", "user_id"),
        UniqueConstraint("document_id", "alias_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    alias_number: Mapped[int] = mapped_column(Integer)
    # author | coauthor | none | unverifiable | pending
    coi_status: Mapped[str] = mapped_column(String(20), default="pending")
    coi_detail: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    # topic | subfield | field | none | no_record | pending
    expertise_level: Mapped[str] = mapped_column(String(20), default="pending")
    expertise_detail: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    coi_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), nullable=True
    )
    anchor_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)  # doc version when written
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    document: Mapped[Document] = relationship(back_populates="comments")
    votes: Mapped[list["Vote"]] = relationship(cascade="all, delete-orphan")


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("comment_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    comment_id: Mapped[int] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    value: Mapped[int] = mapped_column(Integer)  # +1 or -1
