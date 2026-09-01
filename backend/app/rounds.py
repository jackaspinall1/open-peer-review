"""Bounded public review windows.

Reviewers need a deadline, because review is solicited work that otherwise
slides; authors need none, because revising is their own work and rushing it is
the journal pathology this project exists to avoid. Hence: a fixed window per
version, extendable when engagement is thin, and unlimited author time
afterwards.

The window bounds the record rather than the page. Late comments are still
accepted and marked, since losing a correct criticism to a deadline would be
exactly the kind of dysfunction that checks are supposed to prevent.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from .models import Comment, Document, ReviewRound, utcnow

WINDOW_DAYS = 14
EXTENSION_DAYS = 7
MAX_WINDOW_DAYS = 28  # about a month: past this, "no engagement" is the honest answer

# Extending is only offered in the closing days of a window. A deadline you can
# postpone on day one is not a deadline, and the question "do I need longer?"
# cannot honestly be answered until the window has nearly run.
EXTEND_FROM_DAYS_LEFT = 3


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; treat them as UTC."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def current_round(db: Session, doc: Document) -> ReviewRound | None:
    return (
        db.query(ReviewRound)
        .filter(ReviewRound.document_id == doc.id)
        .order_by(ReviewRound.opened_at.desc())
        .first()
    )


def open_round_for(db: Session, doc: Document) -> ReviewRound | None:
    """The round accepting comments right now, if any."""
    rnd = current_round(db, doc)
    if rnd and _aware(rnd.closes_at) > utcnow():
        return rnd
    return None


def open_round(db: Session, doc: Document) -> ReviewRound:
    if open_round_for(db, doc) is not None:
        raise ValueError("A review round is already open for this paper")
    now = utcnow()
    rnd = ReviewRound(
        document_id=doc.id,
        version=doc.version,
        opened_at=now,
        closes_at=now + timedelta(days=WINDOW_DAYS),
    )
    db.add(rnd)
    db.commit()
    return rnd


def extend_round(db: Session, doc: Document) -> ReviewRound:
    rnd = open_round_for(db, doc)
    if rnd is None:
        raise ValueError("No review round is open")
    closes = _aware(rnd.closes_at)
    remaining_days = (closes - utcnow()).total_seconds() / 86400
    if remaining_days > EXTEND_FROM_DAYS_LEFT:
        raise ValueError(
            f"A round can only be extended in its last {EXTEND_FROM_DAYS_LEFT} days"
        )
    total = (closes - _aware(rnd.opened_at)).days
    if total + EXTENSION_DAYS > MAX_WINDOW_DAYS:
        raise ValueError(f"A round cannot run longer than {MAX_WINDOW_DAYS} days")
    rnd.closes_at = closes + timedelta(days=EXTENSION_DAYS)
    rnd.extensions += 1
    db.commit()
    return rnd


def summarise(db: Session, doc: Document) -> dict | None:
    """The round record: dates, extensions and participation.

    Participation is reported so a thin round reads as thin. "Reviewed" with a
    short window and nobody looking should not be indistinguishable from a
    round that actually happened.
    """
    rnd = current_round(db, doc)
    if rnd is None:
        return None
    from .serialize import author_user_ids   # imported here to avoid a cycle

    comments = db.query(Comment).filter(Comment.round_id == rnd.id).all()
    # An author replying to criticism is not a reviewer of their own paper, and
    # counting them would inflate how much scrutiny a round actually drew.
    authors = author_user_ids(db, doc)
    closes = _aware(rnd.closes_at)
    now = utcnow()
    is_open = closes > now
    remaining = closes - now
    return {
        "id": rnd.id,
        "version": rnd.version,
        "opened_at": _aware(rnd.opened_at).isoformat(),
        "closes_at": closes.isoformat(),
        "open": is_open,
        "days_left": int(max(0, -(-remaining.total_seconds() // 86400))) if is_open else 0,
        "extensions": rnd.extensions,
        "extendable": (
            is_open
            and remaining.total_seconds() / 86400 <= EXTEND_FROM_DAYS_LEFT
            and (closes - _aware(rnd.opened_at)).days + EXTENSION_DAYS <= MAX_WINDOW_DAYS
        ),
        "comment_count": len(comments),
        "reviewer_count": len({c.user_id for c in comments if c.user_id not in authors}),
    }
