"""Public-facing serialization. Nothing here may ever expose user_id, name, or ORCID."""
import json
from collections import defaultdict
from typing import Optional

from sqlalchemy.orm import Session

from .models import Comment, Document, ReviewerAlias, ReviewRound, User, Vote


def author_user_ids(db: Session, doc: Document) -> set[int]:
    """Users who count as authors here: the depositor plus ORCID matches."""
    ids = {doc.uploaded_by} if doc.uploaded_by else set()
    orcids = {a.orcid for a in doc.authors if a.orcid}
    if orcids:
        ids |= {u.id for u in db.query(User).filter(User.orcid.in_(orcids)).all()}
    return ids


def document_summary(doc: Document, comment_count: int) -> dict:
    return {
        "id": doc.id,
        "title": doc.title,
        "doi": doc.doi,
        "authors": [{"name": a.name, "orcid": a.orcid, "affiliation": a.affiliation} for a in doc.authors],
        "comment_count": comment_count,
        "version": doc.version,
        "license": doc.license,
        "source_name": doc.source_name,
        "source_url": doc.source_landing_url or doc.source_pdf_url,
        "created_at": doc.created_at.isoformat(),
    }


def comment_tree(db: Session, doc: Document, me: Optional[User]) -> list[dict]:
    comments = (
        db.query(Comment).filter(Comment.document_id == doc.id).order_by(Comment.created_at).all()
    )
    has_rounds = db.query(ReviewRound).filter(ReviewRound.document_id == doc.id).count() > 0
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

    DELETED_TEXT = {
        "author": "[deleted by the commenter]",
        "moderator": "[removed by a moderator]",
    }

    def shape(c: Comment) -> dict:
        alias = aliases.get(c.user_id)
        return {
            "id": c.id,
            "anchor": json.loads(c.anchor_json) if c.anchor_json else None,
            "body": DELETED_TEXT.get(c.deleted_by, "[deleted]") if c.deleted else c.body,
            "deleted": bool(c.deleted),
            "alias": (
                "Author"
                if alias and alias.coi_status == "author"
                else f"Reviewer {alias.alias_number}" if alias and alias.alias_number else "Reviewer ?"
            ),
            "coi": {
                "status": alias.coi_status if alias else "pending",
                "detail": alias.coi_detail if alias else None,
            },
            "expertise": {
                "level": alias.expertise_level if alias else "pending",
                "detail": alias.expertise_detail if alias else None,
            },
            "votes": {"up": ups[c.id], "down": downs[c.id], "mine": mine.get(c.id, 0)},
            "is_mine": me is not None and c.user_id == me.id,
            "by_author": c.user_id in authors,
            # What traditional review surfaces too: a criticism and whether an
            # author answered it. No resolution verdict is claimed.
            "answered": c.parent_id is None
            and c.user_id not in authors
            and any(r.user_id in authors for r in replies_by_parent.get(c.id, [])),
            "version": c.version,
            # Late comments are kept and marked rather than refused.
            "after_window": has_rounds and c.round_id is None,
            "created_at": c.created_at.isoformat(),
            "replies": [],
        }

    authors = author_user_ids(db, doc)
    replies_by_parent: dict[int, list[Comment]] = {}
    for c in comments:
        if c.parent_id is not None:
            replies_by_parent.setdefault(c.parent_id, []).append(c)

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
    from .routes.documents import can_manage

    out["can_manage"] = can_manage(me, doc) if me is not None else False
    # Only the paper's own authors see how many times it was opened. It is a
    # distribution signal for them, not a public score.
    if out["can_manage"]:
        out["views"] = doc.views
    out["has_source"] = bool(doc.source_pdf_url)
    from . import rounds as _rounds

    out["round"] = _rounds.summarise(db, doc)
    out["comments"] = comments
    return out
