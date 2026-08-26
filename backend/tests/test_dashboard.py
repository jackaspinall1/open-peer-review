"""The author's own view: papers they are listed on, and what needs their attention.

Counts are restricted to what the server can genuinely know. Whether a
criticism was resolved is not among them, because anchoring runs in the browser,
so the page reports comments, comments awaiting an author reply, and comments
written against an earlier version.
"""
from datetime import timedelta

from app import rounds
from app.db import SessionLocal
from app.models import ReviewRound
from conftest import comment, login, make_document

AUTHOR = "0000-0002-1825-0097"
COAUTHOR = "0000-0001-5109-3700"
REVIEWER = "0000-0002-9999-000X"


def test_lists_papers_matched_by_orcid_not_just_uploads(client):
    """A listed author sees the paper even if someone else added it."""
    login(client, REVIEWER)
    make_document(client, title="Their paper", authors=[{"name": "Ada", "orcid": AUTHOR}])
    login(client, AUTHOR)
    mine = client.get("/api/documents/mine").json()
    assert [p["title"] for p in mine["under_review"]] == ["Their paper"]


def test_awaiting_response_counts_only_unanswered_reviewer_comments(client):
    login(client, AUTHOR)
    doc = make_document(client, authors=[{"name": "Ada", "orcid": AUTHOR}])
    login(client, REVIEWER)
    first = comment(client, doc, "a concern")["comments"][0]["id"]
    comment(client, doc, "a second concern")

    login(client, AUTHOR)
    assert client.get("/api/documents/mine").json()["under_review"][0]["awaiting_response"] == 2
    comment(client, doc, "we address this in section 4", parent_id=first)
    paper = client.get("/api/documents/mine").json()["under_review"][0]
    assert paper["awaiting_response"] == 1      # the answered one drops out
    assert paper["comments"] == 3               # the reply still counts as a comment


def test_an_authors_own_comment_never_awaits_their_response(client):
    login(client, AUTHOR)
    doc = make_document(client, authors=[{"name": "Ada", "orcid": AUTHOR}])
    comment(client, doc, "a note to myself")
    assert client.get("/api/documents/mine").json()["under_review"][0]["awaiting_response"] == 0


def test_closed_rounds_move_to_past_reviews(client):
    login(client, AUTHOR)
    doc = make_document(client, authors=[{"name": "Ada", "orcid": AUTHOR}])
    client.post(f"/api/documents/{doc}/rounds")
    assert len(client.get("/api/documents/mine").json()["under_review"]) == 1

    db = SessionLocal()
    rnd = db.query(ReviewRound).filter(ReviewRound.document_id == doc).one()
    rnd.closes_at = rounds._aware(rnd.closes_at) - timedelta(days=30)
    db.commit()
    db.close()

    mine = client.get("/api/documents/mine").json()
    assert mine["under_review"] == []
    assert len(mine["past"]) == 1
    assert mine["past"][0]["review_doi"] is None      # deposits are not built yet


def test_papers_you_are_not_on_do_not_appear(client):
    login(client, AUTHOR)
    make_document(client, title="Someone else's", authors=[{"name": "Bob", "orcid": COAUTHOR}])
    login(client, REVIEWER)
    mine = client.get("/api/documents/mine").json()
    assert mine["under_review"] == [] and mine["past"] == []


def test_dashboard_requires_login(client):
    client.post("/auth/logout")
    assert client.get("/api/documents/mine").status_code == 401


def test_threads_report_whether_an_author_answered(client):
    """What the record shows: a criticism and whether an author replied.

    No resolution verdict is asserted, which is all traditional peer review
    surfaces either.
    """
    login(client, AUTHOR)
    doc = make_document(client, authors=[{"name": "Ada", "orcid": AUTHOR}])
    login(client, REVIEWER)
    cid = comment(client, doc, "a concern")["comments"][0]["id"]
    assert client.get(f"/api/documents/{doc}").json()["comments"][0]["answered"] is False

    login(client, AUTHOR)
    comment(client, doc, "addressed in section 4", parent_id=cid)
    thread = client.get(f"/api/documents/{doc}").json()["comments"][0]
    assert thread["answered"] is True
    assert thread["by_author"] is False
    assert thread["replies"][0]["by_author"] is True


def test_an_authors_own_thread_is_not_marked_awaiting(client):
    login(client, AUTHOR)
    doc = make_document(client, authors=[{"name": "Ada", "orcid": AUTHOR}])
    comment(client, doc, "a note from the author")
    thread = client.get(f"/api/documents/{doc}").json()["comments"][0]
    assert thread["by_author"] is True and thread["answered"] is False
