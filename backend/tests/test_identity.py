"""One live discussion per paper, and authors control their own work.

A second copy of a paper would split the review in two, which defeats the point.
Control belongs to any listed author rather than to whoever added it first,
otherwise a non-author could add a paper and lock its authors out.
"""
import json

from app.metadata import normalise_doi
from conftest import PDF, login, make_document

AUTHOR = "0000-0002-1825-0097"
OTHER = "0000-0001-5109-3700"


def _upload(client, title, doi=""):
    return client.post(
        "/api/documents",
        files={"pdf": ("p.pdf", PDF, "application/pdf")},
        data={"title": title, "doi": doi, "authors": json.dumps([])},
    ).json()


def test_version_suffixes_do_not_create_new_papers():
    assert normalise_doi("10.21203/rs.3.rs-6759455/v1") == normalise_doi("10.21203/rs.3.rs-6759455/v2")
    assert normalise_doi("10.1101/2020.01.01.123456v1") == normalise_doi("10.1101/2020.01.01.123456")
    assert normalise_doi("https://doi.org/10.1038/S41467") == "10.1038/s41467"
    # a bare trailing v<digits> is legitimate outside bioRxiv and must survive
    assert normalise_doi("10.1016/j.jpowsour.2019v2") == "10.1016/j.jpowsour.2019v2"


def test_openalex_id_is_an_identity_key(client):
    """The import path dedupes on the OpenAlex id, which survives a preprint
    becoming a published paper. Covered directly because the import route
    itself needs the network and is stubbed out in these tests."""
    from app.db import SessionLocal
    from app.models import Document
    from app.routes.documents import _existing_document

    login(client, AUTHOR)
    doc_id = make_document(client)
    db = SessionLocal()
    db.get(Document, doc_id).openalex_id = "W123456789"
    db.commit()
    assert _existing_document(db, "W123456789", None).id == doc_id
    assert _existing_document(db, "W999999999", None) is None
    db.close()


def test_same_doi_returns_the_existing_paper(client):
    login(client, AUTHOR)
    first = _upload(client, "A paper", "10.1234/abc/v1")
    second = _upload(client, "A paper posted again", "10.1234/abc/v2")
    assert second["id"] == first["id"]
    assert second.get("existing") is True
    # and it did not overwrite the original
    assert client.get(f"/api/documents/{first['id']}").json()["title"] == "A paper"


def test_a_different_person_adding_it_lands_on_the_same_discussion(client):
    login(client, AUTHOR)
    first = _upload(client, "Shared paper", "10.1234/xyz")
    login(client, OTHER)
    assert _upload(client, "Shared paper", "10.1234/xyz")["id"] == first["id"]


def test_papers_without_a_doi_are_not_merged(client):
    login(client, AUTHOR)
    a = _upload(client, "Untitled one")
    b = _upload(client, "Untitled two")
    assert a["id"] != b["id"]


def test_any_listed_author_controls_the_paper_not_just_the_depositor(client):
    """A non-author adding a paper must not lock its authors out."""
    login(client, OTHER)                                    # a third party adds it
    doc = make_document(client, authors=[{"name": "Ada", "orcid": AUTHOR}])
    login(client, AUTHOR)                                   # a listed author arrives
    assert client.get(f"/api/documents/{doc}").json()["can_manage"] is True
    assert client.post(f"/api/documents/{doc}/rounds").status_code == 200


def test_unrelated_users_cannot_manage(client):
    login(client, AUTHOR)
    doc = make_document(client, authors=[{"name": "Ada", "orcid": AUTHOR}])
    login(client, "0000-0002-0000-0009")
    assert client.get(f"/api/documents/{doc}").json()["can_manage"] is False
    assert client.post(f"/api/documents/{doc}/rounds").status_code == 403
