"""Telling a reviewer their comment drew a reply.

In-app only: the ORCID /authenticate scope returns an iD and a name and no email
address, so there is nowhere to send a message. This reaches people when they
next visit, which is a real limitation rather than an oversight.
"""
from conftest import comment, login, make_document

AUTHOR = "0000-0002-1825-0097"
REVIEWER = "0000-0001-5109-3700"
BYSTANDER = "0000-0002-9999-000X"


def test_a_reply_notifies_the_person_replied_to(client):
    login(client, AUTHOR)
    doc = make_document(client, authors=[{"name": "Ada", "orcid": AUTHOR}])
    login(client, REVIEWER)
    cid = comment(client, doc, "the error bars are unexplained")["comments"][0]["id"]
    assert client.get("/api/notifications").json()["unread"] == 0

    login(client, AUTHOR)
    comment(client, doc, "added to the caption", parent_id=cid)
    assert client.get("/api/notifications").json()["unread"] == 0   # not for your own reply

    login(client, REVIEWER)
    payload = client.get("/api/notifications").json()
    assert payload["unread"] == 1
    n = payload["notifications"][0]
    assert n["document_id"] == doc
    assert n["your_comment"] == "the error bars are unexplained"
    assert n["reply"] == "added to the caption"
    assert n["by_author"] is True
    assert n["reply_alias"] == "Author"


def test_replying_to_yourself_notifies_nobody(client):
    login(client, REVIEWER)
    doc = make_document(client)
    cid = comment(client, doc, "a thought")["comments"][0]["id"]
    comment(client, doc, "and another", parent_id=cid)
    assert client.get("/api/notifications").json()["unread"] == 0


def test_bystanders_are_not_notified(client):
    login(client, AUTHOR)
    doc = make_document(client, authors=[{"name": "Ada", "orcid": AUTHOR}])
    login(client, REVIEWER)
    cid = comment(client, doc, "a concern")["comments"][0]["id"]
    login(client, AUTHOR)
    comment(client, doc, "a response", parent_id=cid)
    login(client, BYSTANDER)
    assert client.get("/api/notifications").json()["notifications"] == []


def test_marking_read_clears_the_count_but_keeps_the_list(client):
    login(client, AUTHOR)
    doc = make_document(client, authors=[{"name": "Ada", "orcid": AUTHOR}])
    login(client, REVIEWER)
    cid = comment(client, doc, "a concern")["comments"][0]["id"]
    login(client, AUTHOR)
    comment(client, doc, "a response", parent_id=cid)

    login(client, REVIEWER)
    assert client.post("/api/notifications/read").json()["unread"] == 0
    after = client.get("/api/notifications").json()
    assert after["unread"] == 0 and len(after["notifications"]) == 1
    assert after["notifications"][0]["read"] is True


def test_notifications_never_expose_who_replied(client):
    """Being notified must reveal nothing the page does not already show."""
    import json as _json

    login(client, AUTHOR)
    doc = make_document(client, authors=[{"name": "Ada", "orcid": AUTHOR}])
    login(client, REVIEWER)
    cid = comment(client, doc, "a concern")["comments"][0]["id"]
    login(client, AUTHOR)
    comment(client, doc, "a response", parent_id=cid)
    login(client, REVIEWER)
    blob = _json.dumps(client.get("/api/notifications").json())
    for forbidden in (AUTHOR, AUTHOR.replace("-", ""), "user_id", "orcid"):
        assert forbidden not in blob


def test_notifications_require_login(client):
    client.post("/auth/logout")
    assert client.get("/api/notifications").status_code == 401
    assert client.post("/api/notifications/read").status_code == 401
