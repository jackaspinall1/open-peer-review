"""Seed a document from the command line.

Usage:
    python seed.py paper.pdf "Paper title" --doi 10.1000/xyz \
        --author "Jane Doe:0000-0002-1825-0097" --author "John Smith"
"""
import argparse

from app import config
from app.db import SessionLocal, init_db
from app.models import Document, DocumentAuthor
import shutil
import uuid


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf")
    parser.add_argument("title")
    parser.add_argument("--doi", default=None)
    parser.add_argument("--author", action="append", default=[], help='"Name" or "Name:ORCID"')
    args = parser.parse_args()

    init_db()
    filename = f"{uuid.uuid4().hex}.pdf"
    shutil.copy(args.pdf, config.PDF_DIR / filename)

    db = SessionLocal()
    doc = Document(title=args.title, doi=args.doi, pdf_filename=filename)
    db.add(doc)
    db.flush()
    for i, spec in enumerate(args.author):
        name, _, orcid = spec.partition(":")
        db.add(DocumentAuthor(document_id=doc.id, name=name.strip(), orcid=orcid.strip() or None, position=i))
    db.commit()
    print(f"Created document {doc.id}: {doc.title}")


if __name__ == "__main__":
    main()
