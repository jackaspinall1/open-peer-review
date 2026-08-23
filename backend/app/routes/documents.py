import json
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

import hashlib
import json as _json

from pydantic import BaseModel

from .. import coi, config, metadata
from ..auth import require_user
from ..db import get_db
from ..models import Comment, Document, DocumentAuthor, User
from ..auth import get_current_user, normalize_orcid
from ..serialize import document_summary, full_document

router = APIRouter(prefix="/api/documents")

MAX_PDF_BYTES = 50 * 1024 * 1024


class ResolveIn(BaseModel):
    title: str | None = None
    doi: str | None = None


@router.post("/resolve-metadata")
def resolve_metadata(payload: ResolveIn, user: User = Depends(require_user)):
    return metadata.resolve(payload.title, payload.doi)


@router.get("/my-works")
def my_works(user: User = Depends(require_user)):
    try:
        return {"works": metadata.list_importable_works(user.orcid)}
    except Exception:
        raise HTTPException(status_code=502, detail="Could not reach OpenAlex")


class ImportIn(BaseModel):
    openalex_id: str


@router.post("/import")
def import_work(payload: ImportIn, user: User = Depends(require_user), db: Session = Depends(get_db)):
    try:
        work = metadata.fetch_work(payload.openalex_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid work id")
    except Exception:
        raise HTTPException(status_code=502, detail="Could not fetch the work from OpenAlex")

    shaped = metadata._shape(work, "import")
    # author-initiated by construction: you can only import papers you are on
    my = user.orcid
    if not any(a["orcid"] == my for a in shaped["authors"]):
        raise HTTPException(status_code=403, detail="You can only import papers you are an author of (by ORCID)")

    candidates = metadata.pdf_candidates(work)
    if not candidates:
        raise HTTPException(status_code=422, detail="No open-access PDF available for this work")
    content, used_url = None, None
    for cand in candidates:
        try:
            content = metadata.download_pdf(cand["url"], MAX_PDF_BYTES)
            used_url = cand["url"]
            break
        except Exception:
            continue
    if content is None:
        raise HTTPException(
            status_code=502,
            detail="Could not fetch the PDF automatically (the publisher blocks downloads). "
            "Please upload the PDF below instead.",
        )

    filename = f"{uuid.uuid4().hex}.pdf"
    (config.PDF_DIR / filename).write_bytes(content)
    doc = Document(title=shaped["title"], doi=shaped["doi"], pdf_filename=filename, uploaded_by=user.id,
                   source_pdf_url=used_url, pdf_sha256=hashlib.sha256(content).hexdigest())
    from ..coi import _topic_ref
    topics = [_topic_ref(t) for t in (work.get("topics") or [])[:3]]
    if topics:
        doc.topics_json = _json.dumps(topics)
    db.add(doc)
    db.flush()
    for i, a in enumerate(shaped["authors"]):
        if not a["name"]:
            continue
        db.add(DocumentAuthor(document_id=doc.id, name=a["name"], orcid=a["orcid"],
                              affiliation=a["affiliation"], position=i))
    db.commit()
    return {"id": doc.id}


@router.get("")
def list_documents(db: Session = Depends(get_db)):
    counts = dict(
        db.query(Comment.document_id, func.count(Comment.id)).group_by(Comment.document_id).all()
    )
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return [document_summary(d, counts.get(d.id, 0)) for d in docs]


@router.post("")
async def upload_document(
    pdf: UploadFile = File(...),
    title: str = Form(...),
    doi: str = Form(""),
    authors: str = Form("[]"),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if not title.strip():
        raise HTTPException(status_code=422, detail="Title required")
    try:
        author_list = json.loads(authors)
        assert isinstance(author_list, list)
    except (json.JSONDecodeError, AssertionError):
        raise HTTPException(status_code=422, detail="authors must be a JSON list")

    content = await pdf.read()
    if len(content) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF too large (50 MB limit)")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="File is not a PDF")

    filename = f"{uuid.uuid4().hex}.pdf"
    (config.PDF_DIR / filename).write_bytes(content)

    doc = Document(title=title.strip(), doi=doi.strip() or None, pdf_filename=filename, uploaded_by=user.id)
    db.add(doc)
    db.flush()
    for i, a in enumerate(author_list):
        name = str(a.get("name", "")).strip()
        if not name:
            continue
        orcid_raw = str(a.get("orcid") or "").strip()
        orcid = normalize_orcid(orcid_raw) if orcid_raw else None
        if orcid_raw and orcid is None:
            raise HTTPException(status_code=422, detail=f"Invalid ORCID for author '{name}'")
        affiliation = (str(a.get("affiliation") or "").strip() or None)
        db.add(DocumentAuthor(document_id=doc.id, name=name, orcid=orcid,
                              affiliation=affiliation, position=i))
    topics = coi.classify_document(doc)  # best-effort; retried lazily if it fails
    if topics is not None:
        doc.topics_json = _json.dumps(topics)
    db.commit()
    return {"id": doc.id}


@router.post("/{doc_id}/revision")
async def upload_revision(
    doc_id: int,
    pdf: UploadFile = File(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.uploaded_by != user.id:
        raise HTTPException(status_code=403, detail="Only the original uploader can post a revision")
    content = await pdf.read()
    if len(content) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF too large (50 MB limit)")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="File is not a PDF")
    filename = f"{uuid.uuid4().hex}.pdf"
    (config.PDF_DIR / filename).write_bytes(content)
    # previous file is left on disk (future: version history route)
    doc.pdf_filename = filename
    doc.pdf_sha256 = hashlib.sha256(content).hexdigest()
    doc.version += 1
    db.commit()
    return {"id": doc.id, "version": doc.version}


@router.post("/{doc_id}/check-source")
def check_source(doc_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    """Re-fetch the preprint from its server; bump the version if it changed.

    Preprint servers serve the latest version at a stable URL, so this is how a
    revision posted to arXiv/bioRxiv propagates into the review record.
    """
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.uploaded_by != user.id:
        raise HTTPException(status_code=403, detail="Only the uploader can refresh this paper")
    if not doc.source_pdf_url:
        raise HTTPException(status_code=422, detail="This paper was uploaded manually, not imported")
    try:
        content = metadata.download_pdf(doc.source_pdf_url, MAX_PDF_BYTES)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch from the preprint server: {exc}")

    digest = hashlib.sha256(content).hexdigest()
    if digest == doc.pdf_sha256:
        return {"id": doc.id, "version": doc.version, "updated": False}
    filename = f"{uuid.uuid4().hex}.pdf"
    (config.PDF_DIR / filename).write_bytes(content)
    doc.pdf_filename = filename
    doc.pdf_sha256 = digest
    doc.version += 1
    db.commit()
    return {"id": doc.id, "version": doc.version, "updated": True}


@router.get("/{doc_id}")
def get_document(doc_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    coi.refresh_pending(db, doc)
    return full_document(db, doc, user)


@router.get("/{doc_id}/pdf")
def get_pdf(doc_id: int, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    path = config.PDF_DIR / doc.pdf_filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF file missing")
    return FileResponse(path, media_type="application/pdf")
