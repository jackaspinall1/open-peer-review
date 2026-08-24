"""The core promise: readers never learn who wrote a comment.

Anonymity is the product's central guarantee, so it is asserted here rather than
left to manual checking. Badge wording is also checked for the quantities that
were measured to identify individuals (see README, "Anonymity and badge
disclosure").
"""
import json

from conftest import comment, login, make_document

REAL_NAME = "Ada Lovelace"
ORCID_A = "0000-0002-1825-0097"
ORCID_B = "0000-0001-5109-3700"


def test_public_payload_never_contains_identity(client):
    login(client, ORCID_A)
    doc = make_document(client, authors=[{"name": "Grace Hopper", "orcid": ORCID_B}])
    comment(client, doc, "A critical observation")
    login(client, ORCID_B)
    comment(client, doc, "A second view")

    client.post("/auth/logout")
    payload = client.get(f"/api/documents/{doc}").json()
    blob = json.dumps(payload["comments"])

    for forbidden in (ORCID_A, ORCID_B, ORCID_A.replace("-", ""), "user_id", "orcid"):
        assert forbidden not in blob, f"{forbidden!r} leaked into the public comment payload"
    assert "Reviewer 1" in blob and "Reviewer 2" in blob


def test_badges_disclose_no_quantities(client):
    """Counts, institutions and seniority proxies identify people; levels do not."""
    login(client, ORCID_A)
    doc = make_document(client)
    comment(client, doc, "hello")
    client.post("/auth/logout")
    blob = json.dumps(client.get(f"/api/documents/{doc}").json()["comments"])
    for forbidden in ("20+", "10+", "5+", "shared works", "publishing 10", "University of"):
        assert forbidden not in blob, f"{forbidden!r} is a fingerprinting disclosure"


def test_aliases_are_per_document(client):
    """Same person, two papers: alias numbering must not link them."""
    login(client, ORCID_A)
    d1 = make_document(client, title="Paper one")
    d2 = make_document(client, title="Paper two")
    login(client, ORCID_B)
    comment(client, d1, "first")          # Reviewer 1 on d1
    login(client, ORCID_A)
    comment(client, d1, "second")         # Reviewer 2 on d1
    comment(client, d2, "third")          # Reviewer 1 on d2
    client.post("/auth/logout")
    a1 = client.get(f"/api/documents/{d1}").json()["comments"]
    a2 = client.get(f"/api/documents/{d2}").json()["comments"]
    assert [c["alias"] for c in a1] == ["Reviewer 1", "Reviewer 2"]
    assert [c["alias"] for c in a2] == ["Reviewer 1"]
