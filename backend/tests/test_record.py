"""The artifact a review round leaves behind.

It has to stand on its own: readable without this service existing, free of
internal identifiers, and honest about what it does and does not assert.
"""
import json

from conftest import comment, login, make_document

AUTHOR = "0000-0002-1825-0097"
REVIEWER = "0000-0001-5109-3700"


def _record(client, doc, fmt="json"):
    r = client.get(f"/api/documents/{doc}/record", params={"format": fmt})
    assert r.status_code == 200, r.text
    return r.json() if fmt == "json" else r.text


def test_the_record_is_public(client):
    """The record is the point of the exercise; no account needed to take one."""
    login(client, AUTHOR)
    doc = make_document(client, authors=[{"name": "Ada", "orcid": AUTHOR}])
    from conftest import logout

    logout(client)
    assert client.get(f"/api/documents/{doc}/record").status_code == 200


def test_it_carries_the_paper_the_window_and_the_threads(client):
    login(client, AUTHOR)
    doc = make_document(client, title="A paper", authors=[{"name": "Ada", "orcid": AUTHOR}])
    client.post(f"/api/documents/{doc}/rounds")
    login(client, REVIEWER)
    cid = comment(client, doc, "the error bars are unexplained")["comments"][0]["id"]
    login(client, AUTHOR)
    comment(client, doc, "added to the caption", parent_id=cid)

    rec = _record(client, doc)
    assert rec["paper"]["title"] == "A paper"
    assert rec["paper"]["authors"][0]["orcid"] == AUTHOR
    assert rec["round"]["reviewers"] == 1
    thread = rec["threads"][0]
    assert thread["comment"] == "the error bars are unexplained"
    assert thread["answered_by_an_author"] is True
    assert thread["replies"][0]["from"]["as"] == "Author"
    assert thread["raised_by"]["as"] == "Reviewer 1"


def test_it_never_carries_identities(client):
    login(client, AUTHOR)
    doc = make_document(client, authors=[{"name": "Ada", "orcid": AUTHOR}])
    login(client, REVIEWER)
    comment(client, doc, "a concern")
    blob = json.dumps(_record(client, doc))
    for forbidden in (REVIEWER, REVIEWER.replace("-", ""), "user_id"):
        assert forbidden not in blob


def test_withdrawn_comments_are_absent_not_tombstoned(client):
    """A live page shows something was removed; an archive should not keep it."""
    login(client, AUTHOR)
    doc = make_document(client, authors=[{"name": "Ada", "orcid": AUTHOR}])
    login(client, REVIEWER)
    cid = comment(client, doc, "withdrawn later")["comments"][0]["id"]
    client.delete(f"/api/comments/{cid}")
    rec = _record(client, doc)
    assert rec["threads"] == []
    assert "withdrawn later" not in json.dumps(rec)
    assert "[deleted" not in json.dumps(rec)


def test_markdown_reads_on_its_own(client):
    login(client, AUTHOR)
    doc = make_document(client, title="A paper", authors=[{"name": "Ada", "orcid": AUTHOR}])
    login(client, REVIEWER)
    comment(client, doc, "the error bars are unexplained")
    md = _record(client, doc, "md")
    assert md.startswith("# Review record: A paper")
    assert "the error bars are unexplained" in md
    assert "No resolution verdict is asserted" in md
    assert "_No author response._" in md


def test_an_empty_round_still_produces_a_record(client):
    login(client, AUTHOR)
    doc = make_document(client, authors=[{"name": "Ada", "orcid": AUTHOR}])
    client.post(f"/api/documents/{doc}/rounds")
    assert "No comments were made" in _record(client, doc, "md")
