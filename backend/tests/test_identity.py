"""One live discussion per paper, and authors control their own work.

A second copy of a paper would split the review in two, which defeats the point.
Control belongs to any listed author rather than to whoever added it first,
otherwise a non-author could add a paper and lock its authors out.
"""

from app.metadata import normalise_doi
from conftest import login, make_document

AUTHOR = "0000-0002-1825-0097"
OTHER = "0000-0001-5109-3700"


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


def test_a_versioned_doi_finds_the_existing_paper(client):
    """Import dedupes on the version-stripped DOI, so v2 finds the v1 paper."""
    from app.db import SessionLocal
    from app.metadata import normalise_doi
    from app.routes.documents import _existing_document

    login(client, AUTHOR)
    doc_id = make_document(client, title="A paper", doi=normalise_doi("10.1234/abc/v1"))
    db = SessionLocal()
    assert _existing_document(db, None, normalise_doi("10.1234/abc/v2")).id == doc_id
    assert _existing_document(db, None, normalise_doi("10.1234/abc")).id == doc_id
    db.close()


def test_papers_without_a_doi_are_not_merged(client):
    """A missing DOI is not an identity: two untitled papers stay separate."""
    from app.db import SessionLocal
    from app.routes.documents import _existing_document

    login(client, AUTHOR)
    a = make_document(client, title="Untitled one")
    b = make_document(client, title="Untitled two")
    assert a != b
    db = SessionLocal()
    assert _existing_document(db, None, None) is None
    db.close()


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
