"""The artifact a review round produces.

A round that closes should leave something citable behind, not just a greyed-out
status bar. This renders the whole record: the paper and the version reviewed,
the window and how much scrutiny it drew, and every thread with its criticism,
the author's answer, and what happened to the quoted text afterwards.

It is deliberately self-contained and free of platform-internal identifiers, so
it can be deposited somewhere permanent and read without this service existing.
Deleted comments are absent rather than tombstoned: a live page shows that
something was removed, an archive should not preserve what was withdrawn.
"""
import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .models import Comment, Document
from .rounds import summarise
from .serialize import author_user_ids


# The record has to read on its own, so internal status codes are given the same
# words a reader sees on the page. A check that never completed says nothing and
# is left out rather than archived as "pending".
CONFLICT_LABELS = {
    "author": "Author",
    "coauthor": "Co-author relationship found",
    "large_collab": "Large-collaboration co-author",
    "colleague": "Same institution",
    "none": "No relationship found",
    "unverifiable": "Unverifiable: no author has an ORCID iD",
}
EXPERTISE_LABELS = {
    "topic": "Publishes on this paper's topic",
    "subfield": "Publishes in this paper's subfield",
    "field": "Publishes in this paper's broader field",
    "none": "No publication record in this area",
    "no_record": "No publication record found",
}


def _labelled(status: str | None, labels: dict) -> dict | None:
    if status is None or status not in labels:
        return None
    return {"status": status, "label": labels[status]}


def _fmt(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).isoformat()


def build(db: Session, doc: Document, base_url: str) -> dict:
    rnd = summarise(db, doc)
    authors = author_user_ids(db, doc)
    comments = (
        db.query(Comment)
        .filter(Comment.document_id == doc.id, Comment.deleted == False)  # noqa: E712
        .order_by(Comment.created_at)
        .all()
    )
    from .models import ReviewerAlias

    aliases = {
        a.user_id: a
        for a in db.query(ReviewerAlias).filter(ReviewerAlias.document_id == doc.id).all()
    }

    def who(user_id: int) -> dict:
        alias = aliases.get(user_id)
        if alias and alias.coi_status == "author":
            return {"as": "Author"}
        return {
            "as": f"Reviewer {alias.alias_number}" if alias and alias.alias_number else "Reviewer",
            "conflict_of_interest": _labelled(alias.coi_status if alias else None, CONFLICT_LABELS),
            "expertise": _labelled(alias.expertise_level if alias else None, EXPERTISE_LABELS),
        }

    replies = {}
    for c in comments:
        if c.parent_id is not None:
            replies.setdefault(c.parent_id, []).append(c)

    threads = []
    for c in comments:
        if c.parent_id is not None:
            continue
        anchor = json.loads(c.anchor_json) if c.anchor_json else None
        threads.append({
            "raised_by": who(c.user_id),
            "raised_at": _fmt(c.created_at),
            "on_version": c.version,
            "quoting": (
                {"page": anchor["page"], "text": anchor["quote"]} if anchor else None
            ),
            "comment": c.body,
            "answered_by_an_author": any(r.user_id in authors for r in replies.get(c.id, [])),
            "replies": [
                {
                    "from": who(r.user_id),
                    "at": _fmt(r.created_at),
                    "on_version": r.version,
                    "comment": r.body,
                }
                for r in replies.get(c.id, [])
            ],
        })

    return {
        "record": {
            "produced_by": "Open Peer Review",
            "produced_at": _fmt(datetime.now(timezone.utc)),
            "page": f"{base_url}/doc/{doc.id}",
            "note": (
                "A public review record. Reviewers are pseudonymous within this paper; "
                "the conflict-of-interest and expertise labels are computed from public "
                "scholarly records. No resolution verdict is asserted: what is recorded "
                "is a criticism, any answer to it, and whether the quoted text changed."
            ),
        },
        "paper": {
            "title": doc.title,
            "doi": doc.doi,
            "version_reviewed": doc.version,
            "authors": [
                {"name": a.name, "orcid": a.orcid, "affiliation": a.affiliation}
                for a in doc.authors
            ],
            "source": doc.source_landing_url or doc.source_pdf_url,
            "source_name": doc.source_name,
            "licence": doc.license,
        },
        "round": None if rnd is None else {
            "opened": rnd["opened_at"],
            "closed": rnd["closes_at"],
            "open_now": rnd["open"],
            "extensions": rnd["extensions"],
            "reviewers": rnd["reviewer_count"],
            "comments_in_window": rnd["comment_count"],
        },
        "threads": threads,
    }


def to_markdown(record: dict) -> str:
    """A readable rendering of the same record, for people rather than machines."""
    p, r, out = record["paper"], record["round"], []
    out.append(f"# Review record: {p['title']}\n")
    authors = ", ".join(a["name"] for a in p["authors"])
    out.append(f"**Authors** {authors}  ")
    if p["doi"]:
        out.append(f"**DOI** {p['doi']}  ")
    if p["source"]:
        out.append(f"**Preprint** {p['source']}  ")
    out.append(f"**Version reviewed** v{p['version_reviewed']}\n")
    if r:
        window = f"{r['opened'][:10]} to {r['closed'][:10]}"
        extended = f", extended {r['extensions']}×" if r["extensions"] else ""
        out.append(
            f"Review window {window}{extended}. "
            f"{r['reviewers']} reviewer(s), {r['comments_in_window']} comment(s).\n"
        )
    out.append(f"_{record['record']['note']}_\n")
    out.append("---\n")

    if not record["threads"]:
        out.append("No comments were made during this review.\n")
    for i, t in enumerate(record["threads"], 1):
        who = t["raised_by"]["as"]
        labels = [
            v["label"] for k, v in t["raised_by"].items() if k != "as" and isinstance(v, dict)
        ]
        suffix = f" — {'; '.join(labels)}" if labels else ""
        out.append(f"## {i}. {who}{suffix}\n")
        if t["quoting"]:
            out.append(f"> p. {t['quoting']['page']}: {t['quoting']['text']}\n")
        out.append(f"{t['comment']}\n")
        out.append(
            "_Answered by an author._\n" if t["answered_by_an_author"]
            else "_No author response._\n"
        )
        for rep in t["replies"]:
            out.append(f"**{rep['from']['as']}:** {rep['comment']}\n")
        out.append("")
    return "\n".join(out)
