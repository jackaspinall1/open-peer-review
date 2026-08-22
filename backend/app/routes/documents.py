import json
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

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
    doc.version += 1
    db.commit()
    return {"id": doc.id, "version": doc.version}


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
