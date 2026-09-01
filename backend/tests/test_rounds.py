"""Review windows: a deadline for reviewers, no deadline for authors.

The window bounds the record, not the page, so late comments are still accepted
and marked. The author's only discretionary lever is to invite more scrutiny:
they can extend, but never close early.
"""
from datetime import timedelta

from app import rounds
from app.db import SessionLocal
from app.models import ReviewRound
from conftest import comment, login, make_document

AUTHOR = "0000-0002-1825-0097"
REVIEWER = "0000-0001-5109-3700"


def _shift_close(doc_id, **delta):
    """Move a round's deadline to simulate the passage of time."""
    db = SessionLocal()
    rnd = db.query(ReviewRound).filter(ReviewRound.document_id == doc_id).one()
    rnd.closes_at = rounds._aware(rnd.closes_at) + timedelta(**delta)
    db.commit()
    db.close()


def test_open_round_sets_a_two_week_window(client):
    login(client, AUTHOR)
    doc = make_document(client)
    r = client.post(f"/api/documents/{doc}/rounds").json()
    assert r["open"] is True
    assert r["days_left"] == rounds.WINDOW_DAYS
    assert r["comment_count"] == 0 and r["reviewer_count"] == 0


def test_only_the_depositing_author_controls_the_round(client):
    login(client, AUTHOR)
    doc = make_document(client)
    login(client, REVIEWER)
    assert client.post(f"/api/documents/{doc}/rounds").status_code == 403
    login(client, AUTHOR)
    client.post(f"/api/documents/{doc}/rounds")
    login(client, REVIEWER)
    assert client.post(f"/api/documents/{doc}/rounds/extend").status_code == 403


def test_cannot_open_two_rounds_at_once(client):
    login(client, AUTHOR)
    doc = make_document(client)
    client.post(f"/api/documents/{doc}/rounds")
    assert client.post(f"/api/documents/{doc}/rounds").status_code == 422


def test_extends_in_weekly_steps_and_stops_at_a_month(client):
    login(client, AUTHOR)
    doc = make_document(client)
    client.post(f"/api/documents/{doc}/rounds")
    first = client.post(f"/api/documents/{doc}/rounds/extend").json()
    assert first["days_left"] == rounds.WINDOW_DAYS + rounds.EXTENSION_DAYS
    second = client.post(f"/api/documents/{doc}/rounds/extend").json()
    assert second["extensions"] == 2
    assert second["days_left"] == rounds.MAX_WINDOW_DAYS
    assert second["extendable"] is False
    assert client.post(f"/api/documents/{doc}/rounds/extend").status_code == 422


def test_comments_are_stamped_with_the_open_round_and_counted(client):
    login(client, AUTHOR)
    doc = make_document(client)
    client.post(f"/api/documents/{doc}/rounds")
    login(client, REVIEWER)
    comment(client, doc, "in-window comment")
    payload = client.get(f"/api/documents/{doc}").json()
    assert payload["round"]["comment_count"] == 1
    assert payload["round"]["reviewer_count"] == 1
    assert payload["comments"][0]["after_window"] is False


def test_late_comments_are_accepted_and_marked(client):
    """A correct criticism must never be lost to a deadline."""
    login(client, AUTHOR)
    doc = make_document(client)
    client.post(f"/api/documents/{doc}/rounds")
    _shift_close(doc, days=-15)                      # window now in the past
    login(client, REVIEWER)
    comment(client, doc, "arrived after the window")  # accepted, not refused

    payload = client.get(f"/api/documents/{doc}").json()
    assert payload["round"]["open"] is False
    assert payload["round"]["comment_count"] == 0     # excluded from the record
    assert payload["comments"][0]["after_window"] is True
    assert payload["comments"][0]["body"] == "arrived after the window"


def test_a_new_round_can_follow_a_closed_one(client):
    login(client, AUTHOR)
    doc = make_document(client)
    client.post(f"/api/documents/{doc}/rounds")
    _shift_close(doc, days=-15)
    r = client.post(f"/api/documents/{doc}/rounds").json()
    assert r["open"] is True and r["extensions"] == 0


def test_documents_without_a_round_report_none(client):
    login(client, AUTHOR)
    doc = make_document(client)
    payload = client.get(f"/api/documents/{doc}").json()
    assert payload["round"] is None
    comment(client, doc, "no round yet")
    assert client.get(f"/api/documents/{doc}").json()["comments"][0]["after_window"] is False


def test_posting_a_comment_does_not_compute_badges_inline(client):
    """Badges must resolve in the background.

    Computed inline they make one OpenAlex request per author with an ORCID,
    which measured five seconds on a fourteen-author paper: the reviewer waits
    while their comment posts. The alias number is assigned immediately because
    the response needs it; the badges start pending.
    """
    login(client, AUTHOR)
    doc = make_document(client)
    body = comment(client, doc, "first comment on this paper")
    posted = body["comments"][0]
    assert posted["alias"] == "Reviewer 1"
    assert posted["coi"]["status"] == "pending"
    assert posted["expertise"]["level"] == "pending"
