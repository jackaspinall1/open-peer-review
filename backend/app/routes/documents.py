import json
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

import hashlib
import json as _json
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel

from .. import coi, config, metadata, ratelimit, record, rounds
from ..auth import require_user
from ..db import get_db
from ..models import Comment, Document, DocumentAuthor, User
from ..auth import get_current_user
from ..serialize import document_summary, full_document

router = APIRouter(prefix="/api/documents")

MAX_PDF_BYTES = 50 * 1024 * 1024


SOURCE_CHECK_EVERY = timedelta(hours=6)


def _due_for_source_check(doc: Document) -> bool:
    """Each check downloads the PDF, so not on every page view."""
    if doc.source_checked_at is None:
        return True
    checked = doc.source_checked_at
    if checked.tzinfo is None:
        checked = checked.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - checked > SOURCE_CHECK_EVERY


def can_manage(user: User, doc: Document) -> bool:
    """Who controls a paper: the person who added it, or any listed author.

    Tying control to the depositor alone would let a non-author who added a
    paper first lock its real authors out of opening review on their own work.
    """
    if user is None:
        return False
    if doc.uploaded_by == user.id:
        return True
    return user.orcid.upper() in {a.orcid.upper() for a in doc.authors if a.orcid}


def resolve(db: Session, ident: str) -> Document:
    """Find a paper by its share code, or by numeric id for older links."""
    doc = db.query(Document).filter(Document.slug == ident).one_or_none()
    if doc is None and ident.isdigit():
        doc = db.get(Document, int(ident))
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


def _existing_document(db: Session, openalex_id: str | None, doi: str | None) -> Document | None:
    """One live discussion per paper: a second copy would split the review."""
    if openalex_id:
        hit = db.query(Document).filter(Document.openalex_id == openalex_id).one_or_none()
        if hit:
            return hit
    if doi:
        return db.query(Document).filter(Document.doi == doi).one_or_none()
    return None


@router.get("/mine")
def my_papers(user: User = Depends(require_user), db: Session = Depends(get_db)):
    from ..dashboard import my_papers as _my_papers

    return _my_papers(db, user)


@router.get("/my-works")
def my_works(user: User = Depends(require_user), db: Session = Depends(get_db)):
    def _mark_added(works: list[dict]) -> list[dict]:
        """Flag the ones already here, so the caller can offer the right action."""
        ids = {w["openalex_id"] for w in works}
        if ids:
            existing = {
                d.openalex_id: d.id
                for d in db.query(Document).filter(Document.openalex_id.in_(ids)).all()
            }
            for w in works:
                w["document_id"] = existing.get(w["openalex_id"])
        return works

    try:
        return {"works": _mark_added(metadata.list_importable_works(user.orcid))}
    except Exception as exc:
        busy = "429" in str(exc)
        raise HTTPException(
            status_code=503 if busy else 502,
            detail=(
                "OpenAlex is rate limiting us at the moment. Wait a minute and reload."
                if busy
                else "Could not reach OpenAlex to look up your preprints."
            ),
        )


class ImportIn(BaseModel):
    openalex_id: str


@router.post("/import")
def import_work(payload: ImportIn, user: User = Depends(require_user), db: Session = Depends(get_db)):
    ratelimit.check("upload", user.id, 10, 3600, "adding papers")
    try:
        work = metadata.fetch_work(payload.openalex_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid work id")
    except Exception:
        raise HTTPException(status_code=502, detail="Could not fetch the work from OpenAlex")

    openalex_id = work["id"].rsplit("/", 1)[-1]
    shaped = metadata._shape(work, "import")
    existing = _existing_document(db, openalex_id, metadata.normalise_doi(shaped["doi"]))
    if existing is not None:
        return {"id": existing.id, "existing": True}

    # author-initiated by construction: you can only import papers you are on
    my = user.orcid
    if not any(a["orcid"] == my for a in shaped["authors"]):
        raise HTTPException(status_code=403, detail="You can only import papers you are an author of (by ORCID)")

    candidates = metadata.pdf_candidates(work)
    if not candidates:
        raise HTTPException(status_code=422, detail="No open-access PDF available for this work")
    content, used = None, None
    for cand in candidates:
        try:
            content = metadata.download_pdf(cand["url"], MAX_PDF_BYTES)
            used = cand
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
    doc = Document(
        slug=metadata.new_slug(
            lambda c: db.query(Document).filter(Document.slug == c).first() is not None
        ),
        title=shaped["title"], doi=metadata.normalise_doi(shaped["doi"]),
        openalex_id=openalex_id, pdf_filename=filename, uploaded_by=user.id,
        source_pdf_url=used["url"], source_landing_url=used.get("landing_url"),
        source_name=used.get("source"), license=used.get("license"),
        pdf_sha256=hashlib.sha256(content).hexdigest(),
    )
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




def refresh_from_source(document_id: int) -> None:
    """Re-fetch a paper from its preprint server and bump the version if it moved.

    Runs in the background rather than behind a button: a revision belongs on the
    preprint server, and an author should not have to come here and press
    something for it to arrive. Throttled, since each check downloads the PDF.
    """
    import hashlib

    from ..db import SessionLocal
    from ..models import utcnow

    db = SessionLocal()
    try:
        doc = db.get(Document, document_id)
        if doc is None or not doc.source_pdf_url:
            return
        try:
            content = metadata.download_pdf(doc.source_pdf_url, MAX_PDF_BYTES)
        except Exception:
            doc.source_checked_at = utcnow()   # do not hammer a failing source
            db.commit()
            return
        digest = hashlib.sha256(content).hexdigest()
        doc.source_checked_at = utcnow()
        if digest != doc.pdf_sha256:
            filename = f"{uuid.uuid4().hex}.pdf"
            (config.PDF_DIR / filename).write_bytes(content)
            doc.pdf_filename = filename
            doc.pdf_sha256 = digest
            doc.version += 1
        db.commit()
    finally:
        db.close()


@router.post("/{ident}/rounds")
def open_review_round(ident: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    """Open a review window. Explicit, because it is also the moment to ask people."""
    doc = resolve(db, ident)
    if not can_manage(user, doc):
        raise HTTPException(status_code=403, detail="Only an author of this paper can open review")
    try:
        rounds.open_round(db, doc)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return rounds.summarise(db, doc)


@router.post("/{ident}/rounds/extend")
def extend_review_round(ident: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    doc = resolve(db, ident)
    if not can_manage(user, doc):
        raise HTTPException(status_code=403, detail="Only an author of this paper can extend review")
    try:
        rounds.extend_round(db, doc)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return rounds.summarise(db, doc)


@router.get("/{ident}")
def get_document(
    ident: str,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    doc = resolve(db, ident)
    # Count the open, unless it is one of the paper's own authors looking at
    # their own work. No cookie is set and nothing about the visitor is stored:
    # this is a counter, not analytics.
    if not can_manage(user, doc):
        doc.views += 1
        db.commit()
    # Retrying failed badge checks must not block the read either.
    background.add_task(coi.refresh_pending_detached, doc.id)
    if doc.source_pdf_url and _due_for_source_check(doc):
        background.add_task(refresh_from_source, doc.id)
    return full_document(db, doc, user)


@router.get("/{ident}/my-relationship")
def my_relationship(
    ident: str,
    background: BackgroundTasks,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """The badges this user's comment would carry, shown before they write one.

    People should know how they will be labelled before deciding what to say,
    and an author seeing "co-author relationship found" for the first time
    underneath their own posted comment is a bad way to learn how this works.
    """
    doc = resolve(db, ident)
    rel = coi.get_or_create_relationship(db, doc, user)
    if rel.coi_status == "pending" or rel.expertise_level == "pending":
        background.add_task(coi.compute_alias_badges, doc.id, user.id)
    return {
        "coi": {"status": rel.coi_status, "detail": rel.coi_detail},
        "expertise": {"level": rel.expertise_level, "detail": rel.expertise_detail},
        # The number itself is only fixed at the moment of commenting.
        "alias": "Author" if rel.coi_status == "author" else (
            f"Reviewer {rel.alias_number}" if rel.alias_number else "a numbered reviewer"
        ),
        "has_commented": rel.alias_number is not None,
    }


@router.get("/{ident}/record")
def review_record(ident: str, format: str = "json", db: Session = Depends(get_db)):
    """The artifact a review round leaves behind, in JSON or Markdown.

    Public: the record is the point of the exercise, and anyone should be able
    to take a copy without an account.
    """
    doc = resolve(db, ident)
    built = record.build(db, doc, config.FRONTEND_URL.rstrip("/"))
    stem = f"review-record-{doc.id}-v{doc.version}"
    if format == "md":
        return Response(
            content=record.to_markdown(built),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{stem}.md"'},
        )
    return Response(
        content=_json.dumps(built, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{stem}.json"'},
    )


@router.get("/{ident}/pdf")
def get_pdf(ident: str, db: Session = Depends(get_db)):
    doc = resolve(db, ident)
    path = config.PDF_DIR / doc.pdf_filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF file missing")
    return FileResponse(path, media_type="application/pdf")
