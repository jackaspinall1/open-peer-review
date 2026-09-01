"""The author's own view of their papers.

Counts here are deliberately limited to what the server can actually know.
Whether a criticism was *resolved* is not one of those things: anchoring runs in
the browser, so only the client can tell whether a quoted passage still exists
in the current version. Rather than invent a number, this reports three facts
that are computable and useful on their own:

  comments            how much scrutiny the paper has drawn
  awaiting_response   top-level comments no author has replied to yet
  superseded          comments written against an earlier version

"Superseded" is a hint that a point may have been dealt with by a revision, not
a claim that it was.
"""
from sqlalchemy.orm import Session

from .models import Comment, Document, DocumentAuthor, ReviewRound, User
from .serialize import author_user_ids
from .rounds import summarise


def _counts(db: Session, doc: Document) -> dict:
    comments = (
        db.query(Comment)
        .filter(Comment.document_id == doc.id, Comment.deleted == False)  # noqa: E712
        .all()
    )
    authors = author_user_ids(db, doc)
    replies_by_parent: dict[int, list[Comment]] = {}
    for c in comments:
        if c.parent_id is not None:
            replies_by_parent.setdefault(c.parent_id, []).append(c)

    top_level = [c for c in comments if c.parent_id is None]
    awaiting = sum(
        1
        for c in top_level
        if c.user_id not in authors
        and not any(r.user_id in authors for r in replies_by_parent.get(c.id, []))
    )
    return {
        "comments": len(comments),
        "awaiting_response": awaiting,
        "superseded": sum(1 for c in top_level if c.version < doc.version),
    }


def my_papers(db: Session, user: User) -> dict:
    """Papers this user can manage, split by whether review is still running."""
    orcid = user.orcid.upper()
    matching_ids = {
        a.document_id
        for a in db.query(DocumentAuthor).filter(DocumentAuthor.orcid.isnot(None)).all()
        if a.orcid.upper() == orcid
    }
    docs = [
        d
        for d in db.query(Document).order_by(Document.created_at.desc()).all()
        if d.uploaded_by == user.id or d.id in matching_ids
    ]

    under_review, past = [], []
    for doc in docs:
        rnd = summarise(db, doc)
        entry = {
            "id": doc.id,
            "slug": doc.slug,
            "title": doc.title,
            "version": doc.version,
            "doi": doc.doi,
            "source_url": doc.source_landing_url or doc.source_pdf_url,
            "source_name": doc.source_name,
            "review_doi": doc.review_doi,
            "views": doc.views,
            "round": rnd,
            "rounds_held": db.query(ReviewRound).filter(ReviewRound.document_id == doc.id).count(),
            **_counts(db, doc),
        }
        # A paper with no window open yet belongs with the live ones: it is the
        # one that needs the author to do something.
        (past if rnd and not rnd["open"] else under_review).append(entry)
    return {"under_review": under_review, "past": past}
