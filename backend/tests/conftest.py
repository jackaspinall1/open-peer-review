import os
import tempfile
from pathlib import Path

import pytest

TMP = tempfile.mkdtemp(prefix="pr-tests-")
os.environ["DATA_DIR"] = TMP
os.environ["AUTH_MODE"] = "mock"
os.environ["SECRET_KEY"] = "test-key-not-used-in-production"
os.environ["ADMIN_ORCIDS"] = "0000-0002-0000-0001"

from fastapi.testclient import TestClient  # noqa: E402

from app import coi, config, ratelimit  # noqa: E402
from app.db import Base, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402

PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Tests must not depend on OpenAlex/ORCID being reachable."""
    def fake_coi(user, doc, profile=None):
        # Faithful to the real rule for the one case that has no network cost:
        # an ORCID on the author list is an author. Everything else reads as no
        # relationship, since the graph lookups are what we are avoiding here.
        if user.orcid in {a.orcid for a in doc.authors if a.orcid}:
            return ("author", "Commenter is a listed author")
        return ("none", "No co-authorship found")

    monkeypatch.setattr(coi, "compute_coi", fake_coi)
    # The profile builder is the only remaining network path in badge
    # computation; without stubbing it the suite would call OpenAlex.
    monkeypatch.setattr(coi, "get_profile", lambda db, user: {
        "coauthors": {}, "topics": [], "works": 0, "truncated": False})
    monkeypatch.setattr(coi, "classify_document", lambda doc: [])
    monkeypatch.setattr(coi, "compute_expertise", lambda user, topics, profile=None: ("none", "No record"))
    monkeypatch.setattr(coi, "refresh_pending", lambda db, doc: None)


@pytest.fixture()
def client():
    init_db()
    ratelimit.reset()   # counters are process-global; do not leak between tests
    # Each test gets an empty database: otherwise rows leak between tests and
    # assertions about counts pass alone but fail in a full run.
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


def login(client, orcid):
    r = client.post("/auth/mock/login", json={"orcid": orcid})
    assert r.status_code == 200, r.text
    return r


def make_document(client, title="Test paper", authors=None, doi=None, uploader_orcid=None):
    """Create a paper directly.

    There is no manual upload endpoint: papers are only ever imported by one of
    their own authors from their indexed record, which needs the network. Tests
    therefore build the row rather than driving a user-facing path that does not
    exist.
    """
    from app.db import SessionLocal
    from app.models import Document, DocumentAuthor, User

    db = SessionLocal()
    try:
        # Attribute the paper to whoever is signed in, matching what importing
        # does, so the creator can manage it.
        orcid = uploader_orcid
        if orcid is None:
            me = client.get("/api/me").json()
            orcid = me.get("orcid")
        uploader = (
            db.query(User).filter(User.orcid == orcid).one_or_none() if orcid else None
        )
        doc = Document(
            title=title, doi=doi, pdf_filename="test.pdf",
            uploaded_by=uploader.id if uploader else None,
        )
        db.add(doc)
        db.flush()
        for i, a in enumerate(authors or []):
            db.add(DocumentAuthor(
                document_id=doc.id, name=a["name"], orcid=a.get("orcid"), position=i))
        db.commit()
        (config.PDF_DIR / "test.pdf").write_bytes(PDF)
        return doc.id
    finally:
        db.close()


def comment(client, doc_id, body, **kw):
    r = client.post(f"/api/documents/{doc_id}/comments", json={"body": body, **kw})
    assert r.status_code == 200, r.text
    return r.json()
