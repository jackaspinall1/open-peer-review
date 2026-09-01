"""Moderation is deliberately minimal and reversible: nothing is ever gated.

Comments publish immediately; reports queue for a human and hide nothing; a
delete removes the text but preserves the thread so replies stay readable.
"""
from conftest import comment, login, logout, make_document

AUTHOR = "0000-0002-1825-0097"
OTHER = "0000-0001-5109-3700"
ADMIN = "0000-0002-0000-0001"


def test_delete_own_comment_preserves_replies(client):
    login(client, AUTHOR)
    doc = make_document(client)
    top = comment(client, doc, "original point")["id"]
    login(client, OTHER)
    comment(client, doc, "a reply", parent_id=top)

    login(client, AUTHOR)
    assert client.delete(f"/api/comments/{top}").status_code == 200

    payload = client.get(f"/api/documents/{doc}").json()["comments"][0]
    assert payload["deleted"] is True
    assert payload["body"] == "[deleted by the commenter]"
    assert "original point" not in str(payload)
    assert payload["replies"][0]["body"] == "a reply"   # thread survives


def test_cannot_delete_someone_elses_comment(client):
    login(client, AUTHOR)
    doc = make_document(client)
    cid = comment(client, doc, "not yours")["id"]
    login(client, OTHER)
    assert client.delete(f"/api/comments/{cid}").status_code == 403
    assert client.get(f"/api/documents/{doc}").json()["comments"][0]["body"] == "not yours"


def test_moderator_can_remove_and_it_is_labelled_as_such(client):
    login(client, AUTHOR)
    doc = make_document(client)
    cid = comment(client, doc, "abusive text")["id"]
    login(client, ADMIN)
    assert client.delete(f"/api/comments/{cid}").status_code == 200
    body = client.get(f"/api/documents/{doc}").json()["comments"][0]["body"]
    assert body == "[removed by a moderator]"


def test_report_hides_nothing_and_queues_for_a_human(client):
    login(client, AUTHOR)
    doc = make_document(client)
    cid = comment(client, doc, "harsh but fair criticism")["id"]
    login(client, OTHER)
    assert client.post(f"/api/comments/{cid}/report", json={"reason": "rude"}).status_code == 200
    # still visible: reports never auto-hide
    assert client.get(f"/api/documents/{doc}").json()["comments"][0]["body"] == "harsh but fair criticism"

    assert client.get("/api/admin/reports").status_code == 403   # not a moderator
    login(client, ADMIN)
    reports = client.get("/api/admin/reports").json()["reports"]
    assert len(reports) == 1
    assert reports[0]["comment_id"] == cid
    assert reports[0]["reason"] == "rude"
    assert "reporter_relationship" in reports[0]


def test_reporting_is_idempotent_and_self_reporting_rejected(client):
    login(client, AUTHOR)
    doc = make_document(client)
    cid = comment(client, doc, "mine")["id"]
    assert client.post(f"/api/comments/{cid}/report", json={}).status_code == 422
    login(client, OTHER)
    client.post(f"/api/comments/{cid}/report", json={})
    client.post(f"/api/comments/{cid}/report", json={})
    login(client, ADMIN)
    assert len(client.get("/api/admin/reports").json()["reports"]) == 1


def test_login_required_to_moderate_or_report(client):
    login(client, AUTHOR)
    doc = make_document(client)
    cid = comment(client, doc, "text")["id"]
    logout(client)
    assert client.delete(f"/api/comments/{cid}").status_code == 401
    assert client.post(f"/api/comments/{cid}/report", json={}).status_code == 401
