import json
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_user
from ..coi import compute_alias_badges, get_or_create_alias
from ..rounds import open_round_for
from ..db import get_db
from .. import config
from ..models import Comment, Document, Notification, Report, User, Vote
from ..serialize import comment_tree

router = APIRouter(prefix="/api")

MAX_QUOTE = 2000
MAX_BODY = 20000


class CommentIn(BaseModel):
    body: str
    anchor: Optional[dict] = None
    parent_id: Optional[int] = None


class ReportIn(BaseModel):
    reason: Optional[str] = None


class VoteIn(BaseModel):
    value: int  # 1, -1, or 0 to clear


def _validate_anchor(anchor: dict) -> dict:
    try:
        page = int(anchor["page"])
        start = int(anchor["start"])
        end = int(anchor["end"])
        quote = str(anchor["quote"])
        prefix = str(anchor.get("prefix", ""))
        suffix = str(anchor.get("suffix", ""))
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Malformed anchor")
    if page < 1 or start < 0 or end <= start or not quote or len(quote) > MAX_QUOTE:
        raise HTTPException(status_code=422, detail="Malformed anchor")
    return {"page": page, "start": start, "end": end, "quote": quote,
            "prefix": prefix[-64:], "suffix": suffix[:64]}


@router.post("/documents/{doc_id}/comments")
def create_comment(
    doc_id: int,
    payload: CommentIn,
    background: BackgroundTasks,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=422, detail="Comment body required")
    if len(body) > MAX_BODY:
        raise HTTPException(status_code=422, detail="Comment too long")

    anchor = None
    if payload.parent_id is not None:
        parent = db.get(Comment, payload.parent_id)
        if parent is None or parent.document_id != doc.id:
            raise HTTPException(status_code=422, detail="Parent comment not on this document")
    elif payload.anchor is not None:
        anchor = _validate_anchor(payload.anchor)

    alias = get_or_create_alias(db, doc, user)  # assigns the pseudonym immediately
    if alias.coi_status == "pending" or alias.expertise_level == "pending":
        background.add_task(compute_alias_badges, doc.id, user.id)
    comment = Comment(
        document_id=doc.id,
        user_id=user.id,
        parent_id=payload.parent_id,
        anchor_json=json.dumps(anchor) if anchor else None,
        body=body,
        version=doc.version,
        round_id=(lambda r: r.id if r else None)(open_round_for(db, doc)),
    )
    db.add(comment)
    db.flush()
    if payload.parent_id is not None:
        parent = db.get(Comment, payload.parent_id)
        if parent is not None and parent.user_id != user.id:
            db.add(Notification(
                user_id=parent.user_id,
                document_id=doc.id,
                comment_id=comment.id,
                parent_comment_id=parent.id,
            ))
    db.commit()
    return {"id": comment.id, "comments": comment_tree(db, doc, user)}


@router.post("/comments/{comment_id}/vote")
def vote(
    comment_id: int,
    payload: VoteIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if payload.value not in (-1, 0, 1):
        raise HTTPException(status_code=422, detail="value must be -1, 0 or 1")
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id == user.id:
        raise HTTPException(status_code=403, detail="You cannot vote on your own comment")

    existing = (
        db.query(Vote).filter(Vote.comment_id == comment_id, Vote.user_id == user.id).one_or_none()
    )
    if payload.value == 0:
        if existing is not None:
            db.delete(existing)
    elif existing is None:
        db.add(Vote(comment_id=comment_id, user_id=user.id, value=payload.value))
    else:
        existing.value = payload.value
    db.commit()

    votes = db.query(Vote).filter(Vote.comment_id == comment_id).all()
    return {
        "up": sum(1 for v in votes if v.value > 0),
        "down": sum(1 for v in votes if v.value < 0),
        "mine": next((v.value for v in votes if v.user_id == user.id), 0),
    }


def _is_admin(user: User) -> bool:
    return user.orcid.upper() in config.ADMIN_ORCIDS


@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Soft delete. Replies and thread structure survive; the text does not."""
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    admin = _is_admin(user)
    if comment.user_id != user.id and not admin:
        raise HTTPException(status_code=403, detail="You can only delete your own comments")
    comment.deleted = True
    comment.deleted_by = "moderator" if (admin and comment.user_id != user.id) else "author"
    db.commit()
    return {"id": comment.id, "deleted": True}


@router.post("/comments/{comment_id}/report")
def report_comment(
    comment_id: int,
    payload: ReportIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Flag a comment for human review. Reports never hide anything by themselves."""
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id == user.id:
        raise HTTPException(status_code=422, detail="You cannot report your own comment")
    existing = (
        db.query(Report)
        .filter(Report.comment_id == comment_id, Report.user_id == user.id)
        .one_or_none()
    )
    if existing is None:
        db.add(Report(comment_id=comment_id, user_id=user.id,
                      reason=(payload.reason or "").strip()[:500] or None))
        db.commit()
    return {"reported": True}


@router.get("/admin/reports")
def list_reports(user: User = Depends(require_user), db: Session = Depends(get_db)):
    """Open reports for a human to judge.

    Includes the reporter's relationship to the paper, because a report from an
    author of the paper is a much weaker signal than one from an uninvolved
    reader: the predictable abuse of reporting is authors flagging criticism.
    """
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Not a moderator")
    from ..models import ReviewerAlias

    out = []
    for r in db.query(Report).filter(Report.resolved == False).order_by(Report.created_at).all():  # noqa: E712
        comment = db.get(Comment, r.comment_id)
        if comment is None:
            continue
        alias = (
            db.query(ReviewerAlias)
            .filter(ReviewerAlias.document_id == comment.document_id,
                    ReviewerAlias.user_id == r.user_id)
            .one_or_none()
        )
        out.append({
            "report_id": r.id,
            "comment_id": comment.id,
            "document_id": comment.document_id,
            "body": comment.body,
            "already_deleted": comment.deleted,
            "reason": r.reason,
            "reporter_relationship": alias.coi_status if alias else "unknown",
            "reported_at": r.created_at.isoformat(),
        })
    return {"reports": out}


@router.get("/notifications")
def list_notifications(user: User = Depends(require_user), db: Session = Depends(get_db)):
    """Replies to this user's comments, newest first.

    Shows the reply under its per-document alias like everywhere else, so being
    notified reveals nothing that the page does not already show.
    """
    from ..models import Document as Doc
    from ..serialize import comment_tree

    rows = (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    aliases = {}
    out = []
    for n in rows:
        reply, mine, doc = db.get(Comment, n.comment_id), db.get(Comment, n.parent_comment_id), db.get(Doc, n.document_id)
        if reply is None or mine is None or doc is None:
            continue
        if doc.id not in aliases:
            aliases[doc.id] = {c["id"]: c for c in _flatten(comment_tree(db, doc, user))}
        shaped = aliases[doc.id].get(reply.id, {})
        out.append({
            "id": n.id,
            "document_id": doc.id,
            "document_title": doc.title,
            "comment_id": reply.id,
            "your_comment": mine.body[:140],
            "reply": reply.body[:280] if not reply.deleted else "[deleted]",
            "reply_alias": shaped.get("alias", "Reviewer ?"),
            "by_author": shaped.get("by_author", False),
            "read": n.read_at is not None,
            "created_at": n.created_at.isoformat(),
        })
    return {"notifications": out, "unread": sum(1 for n in out if not n["read"])}


def _flatten(tree: list[dict]) -> list[dict]:
    out = []
    for c in tree:
        out.append(c)
        out.extend(c.get("replies", []))
    return out


@router.post("/notifications/read")
def mark_notifications_read(user: User = Depends(require_user), db: Session = Depends(get_db)):
    from ..models import utcnow

    db.query(Notification).filter(
        Notification.user_id == user.id, Notification.read_at.is_(None)
    ).update({Notification.read_at: utcnow()}, synchronize_session=False)
    db.commit()
    return {"unread": 0}
