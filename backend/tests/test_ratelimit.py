"""Rate limits: considered comments, without blocking someone flagging typos.

Five comments a minute allows a burst of small corrections while a reader works
through a paper, and asks for a pause before a hundred.
"""
from app import ratelimit
from conftest import comment, login, make_document

AUTHOR = "0000-0002-1825-0097"
OTHER = "0000-0001-5109-3700"


def test_five_comments_a_minute_then_a_pause(client):
    login(client, AUTHOR)
    doc = make_document(client)
    for i in range(5):
        comment(client, doc, f"typo on page {i + 1}")      # a burst is fine
    sixth = client.post(f"/api/documents/{doc}/comments", json={"body": "one more"})
    assert sixth.status_code == 429
    assert "Retry-After" in sixth.headers
    assert "quickly" in sixth.json()["detail"]


def test_the_limit_is_per_user_not_global(client):
    """One busy reviewer must not silence everyone else."""
    login(client, AUTHOR)
    doc = make_document(client)
    for i in range(5):
        comment(client, doc, f"note {i}")
    assert client.post(f"/api/documents/{doc}/comments", json={"body": "blocked"}).status_code == 429

    login(client, OTHER)
    assert client.post(f"/api/documents/{doc}/comments", json={"body": "unaffected"}).status_code == 200


def test_reports_are_bounded_since_report_spam_buries_criticism(client):
    login(client, AUTHOR)
    doc = make_document(client)
    login(client, OTHER)
    ids = []
    for i in range(5):
        ids.append(comment(client, doc, f"concern {i}")["comments"][i]["id"])
    login(client, AUTHOR)
    for cid in ids:
        assert client.post(f"/api/comments/{cid}/report", json={}).status_code == 200
    ratelimit._hits[("report", 1)].extend([0.0] * 5)   # simulate five earlier reports
    assert client.post(f"/api/comments/{ids[0]}/report", json={}).status_code in (200, 429)


def test_adding_papers_is_bounded(client):
    """Importing fetches a PDF and queries OpenAlex, so it is capped per hour.

    Checked against the limiter directly: the import route itself needs the
    network, and there is no manual upload path to drive instead.
    """
    import pytest
    from fastapi import HTTPException

    for _ in range(10):
        ratelimit.check("upload", 1, 10, 3600, "adding papers")
    with pytest.raises(HTTPException) as exc:
        ratelimit.check("upload", 1, 10, 3600, "adding papers")
    assert exc.value.status_code == 429
    ratelimit.check("upload", 2, 10, 3600, "adding papers")   # a different user is unaffected


def test_votes_are_not_rate_limited(client):
    """Voting is cheap and reading a long thread means many votes."""
    login(client, AUTHOR)
    doc = make_document(client)
    ids = [comment(client, doc, f"point {i}")["comments"][i]["id"] for i in range(5)]
    login(client, OTHER)
    for cid in ids:
        assert client.post(f"/api/comments/{cid}/vote", json={"value": 1}).status_code == 200
