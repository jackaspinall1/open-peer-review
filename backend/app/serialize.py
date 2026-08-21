"""Public-facing serialization. Nothing here may ever expose user_id, name, or ORCID."""
import json
from collections import defaultdict
from typing import Optional

from sqlalchemy.orm import Session

from .models import Comment, Document, ReviewerAlias, User, Vote


def document_summary(doc: Document, comment_count: int) -> dict:
    return {
        "id": doc.id,
        "title": doc.title,
        "doi": doc.doi,
        "authors": [{"name": a.name, "orcid": a.orcid} for a in doc.authors],
        "comment_count": comment_count,
        "version": doc.version,
        "created_at": doc.created_at.isoformat(),
    }


def comment_tree(db: Session, doc: Document, me: Optional[User]) -> list[dict]:
    comments = (
        db.query(Comment).filter(Comment.document_id == doc.id).order_by(Comment.created_at).all()
    )
    aliases = {
        a.user_id: a
        for a in db.query(ReviewerAlias).filter(ReviewerAlias.document_id == doc.id).all()
    }
    ups: dict[int, int] = defaultdict(int)
    downs: dict[int, int] = defaultdict(int)
    mine: dict[int, int] = {}
    comment_ids = [c.id for c in comments]
    if comment_ids:
        for v in db.query(Vote).filter(Vote.comment_id.in_(comment_ids)).all():
            if v.value > 0:
                ups[v.comment_id] += 1
            else:
                downs[v.comment_id] += 1
            if me is not None and v.user_id == me.id:
                mine[v.comment_id] = v.value

    def shape(c: Comment) -> dict:
        alias = aliases.get(c.user_id)
        return {
            "id": c.id,
            "anchor": json.loads(c.anchor_json) if c.anchor_json else None,
            "body": c.body,
            "alias": (
                "Author"
                if alias and alias.coi_status == "author"
                else f"Reviewer {alias.alias_number}" if alias else "Reviewer ?"
            ),
            "coi": {
                "status": alias.coi_status if alias else "pending",
                "detail": alias.coi_detail if alias else None,
            },
            "votes": {"up": ups[c.id], "down": downs[c.id], "mine": mine.get(c.id, 0)},
            "is_mine": me is not None and c.user_id == me.id,
            "version": c.version,
            "created_at": c.created_at.isoformat(),
            "replies": [],
        }

    by_id = {c.id: c for c in comments}
    shaped = {c.id: shape(c) for c in comments}
    roots: list[dict] = []
    for c in comments:
        if c.parent_id is None:
            roots.append(shaped[c.id])
        else:
            # flatten reply chains onto the top-level ancestor
            root = c
            while root.parent_id is not None and root.parent_id in by_id:
                root = by_id[root.parent_id]
            shaped[root.id]["replies"].append(shaped[c.id])

    def sort_key(node: dict):
        a = node["anchor"]
        if a is None:  # general comments after anchored ones
            return (1, 0, 0, node["created_at"])
        return (0, a.get("page", 0), a.get("start", 0), node["created_at"])

    roots.sort(key=sort_key)
    return roots


def full_document(db: Session, doc: Document, me: Optional[User]) -> dict:
    comments = comment_tree(db, doc, me)
    n = sum(1 + len(c["replies"]) for c in comments)
    out = document_summary(doc, n)
    out["is_uploader"] = me is not None and doc.uploaded_by == me.id
    out["comments"] = comments
    return out
