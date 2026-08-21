import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import require_user
from ..coi import get_or_create_alias
from ..db import get_db
from ..models import Comment, Document, User, Vote
from ..serialize import comment_tree

router = APIRouter(prefix="/api")

MAX_QUOTE = 2000
MAX_BODY = 20000


class CommentIn(BaseModel):
    body: str
    anchor: Optional[dict] = None
    parent_id: Optional[int] = None


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

    get_or_create_alias(db, doc, user)  # assigns pseudonym + COI on first comment
    comment = Comment(
        document_id=doc.id,
        user_id=user.id,
        parent_id=payload.parent_id,
        anchor_json=json.dumps(anchor) if anchor else None,
        body=body,
        version=doc.version,
    )
    db.add(comment)
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
