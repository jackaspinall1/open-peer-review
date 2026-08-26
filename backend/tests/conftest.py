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

from app import coi, metadata  # noqa: E402
from app.db import Base, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402

PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Tests must not depend on OpenAlex/ORCID being reachable."""
    def fake_coi(user, doc):
        # Faithful to the real rule for the one case that has no network cost:
        # an ORCID on the author list is an author. Everything else reads as no
        # relationship, since the graph lookups are what we are avoiding here.
        if user.orcid in {a.orcid for a in doc.authors if a.orcid}:
            return ("author", "Commenter is a listed author")
        return ("none", "No co-authorship found")

    monkeypatch.setattr(coi, "compute_coi", fake_coi)
    monkeypatch.setattr(coi, "classify_document", lambda doc: [])
    monkeypatch.setattr(coi, "compute_expertise", lambda user, topics: ("none", "No record"))
    monkeypatch.setattr(coi, "refresh_pending", lambda db, doc: None)
    monkeypatch.setattr(metadata, "resolve", lambda title, doi: {"found": False, "authors": []})


@pytest.fixture()
def client():
    init_db()
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


def make_document(client, title="Test paper", authors=None):
    r = client.post(
        "/api/documents",
        files={"pdf": ("p.pdf", PDF, "application/pdf")},
        data={"title": title, "doi": "", "authors": __import__("json").dumps(authors or [])},
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def comment(client, doc_id, body, **kw):
    r = client.post(f"/api/documents/{doc_id}/comments", json={"body": body, **kw})
    assert r.status_code == 200, r.text
    return r.json()
