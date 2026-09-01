from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
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
    # Identity keys: one live discussion per paper, or the review splits in two.
    # OpenAlex merges a preprint with its published version into one work, so its
    # id survives that transition; the DOI is stored version-stripped for the same
    # reason (preprint servers mint a DOI per version).
    # Short, unguessable share code used in URLs. Not the primary key: sequential
    # ids in a link would let anyone enumerate every paper on the site, which is
    # the directory we deliberately do not have.
    slug: Mapped[Optional[str]] = mapped_column(String(16), unique=True, nullable=True)
    openalex_id: Mapped[Optional[str]] = mapped_column(String(30), unique=True, nullable=True)
    doi: Mapped[Optional[str]] = mapped_column(String(200), unique=True, nullable=True)
    pdf_filename: Mapped[str] = mapped_column(String(200))
    version: Mapped[int] = mapped_column(Integer, default=1)
    topics_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # OpenAlex topics
    source_pdf_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # preprint server
    source_landing_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    license: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # DOI of the deposited review record, once rounds are archived (see TODO).
    review_doi: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    # Page opens, excluding the paper's own authors. Operator and author
    # telemetry only: it answers "is anyone looking at this", which is a
    # question about distribution rather than about quality, and it is never
    # shown publicly because a view count measures promotion, not scrutiny.
    views: Mapped[int] = mapped_column(Integer, default=0)
    pdf_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
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
    # Assigned on the user's first comment, not when the relationship is first
    # computed: a badge can be shown to someone before they have said anything,
    # and handing out numbers to silent viewers would both waste them and let
    # gaps in the sequence hint at how many people looked.
    alias_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # author | coauthor | none | unverifiable | pending
    coi_status: Mapped[str] = mapped_column(String(20), default="pending")
    coi_detail: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    # topic | subfield | field | none | no_record | pending
    expertise_level: Mapped[str] = mapped_column(String(20), default="pending")
    expertise_detail: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    coi_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class ReviewRound(Base):
    """A bounded window of public review over one version of a paper.

    The window supplies the deadline that turns willingness into reviews, and
    its closing supplies the terminal state an author needs to call the paper
    reviewed. It bounds the *record*, not the page: comments are still accepted
    afterwards and marked as arriving late, because a correct criticism should
    never be lost to a deadline.
    """

    __tablename__ = "review_rounds"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer)
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    closes_at: Mapped[datetime] = mapped_column(DateTime)
    extensions: Mapped[int] = mapped_column(Integer, default=0)


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
    # The round open when this was posted; NULL means outside any window.
    round_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("review_rounds.id", ondelete="SET NULL"), nullable=True
    )
    # Soft delete: the thread structure and any replies survive, the text does not.
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_by: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # author | moderator
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    document: Mapped[Document] = relationship(back_populates="comments")
    votes: Mapped[list["Vote"]] = relationship(cascade="all, delete-orphan")


class Report(Base):
    """A reader flagging a comment. Reports never hide anything by themselves."""

    __tablename__ = "reports"
    __table_args__ = (UniqueConstraint("comment_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    comment_id: Mapped[int] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)


class UserProfile(Base):
    """A reviewer's scholarly graph, fetched once and reused for every paper.

    Asking OpenAlex "did X co-author with A? with B? with C?" costs one request
    per author of every paper X comments on. Fetching X's own works once and
    intersecting locally costs two requests for the rest of their life here,
    which matters because the free tier is measured in a thousand calls.
    """

    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    # {co-author ORCID: {"y": latest year of a normal-sized shared work | null,
    #                    "L": [ids of shared works with more than 15 authors]}}
    coauthors_json: Mapped[str] = mapped_column(Text)
    topics_json: Mapped[str] = mapped_column(Text)
    works_count: Mapped[int] = mapped_column(Integer, default=0)
    truncated: Mapped[bool] = mapped_column(Boolean, default=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Notification(Base):
    """Tells a reviewer that someone replied to their comment.

    In-app only. The ORCID /authenticate scope returns an iD and a name and no
    email address, so there is nowhere to send a message; this reaches people
    when they next visit. Email would need an address collected separately.
    """

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    comment_id: Mapped[int] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"))
    parent_comment_id: Mapped[int] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("comment_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    comment_id: Mapped[int] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    value: Mapped[int] = mapped_column(Integer)  # +1 or -1
