"""Resolve paper metadata (title, authors, ORCIDs, affiliations) from OpenAlex.

The client extracts a title candidate and/or DOI string from the PDF; we look
the work up and return its verified authorship record. ORCIDs come only from
the work's own authorships — never from name search — because a wrong ORCID
would grant someone else's "Author" badge.
"""
import logging
import re

import httpx

from . import config

log = logging.getLogger(__name__)

OPENALEX = "https://api.openalex.org"


def _norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def _shape(work: dict, source: str) -> dict:
    authors = []
    for auth in work.get("authorships", []):
        a = auth.get("author") or {}
        insts = auth.get("institutions") or []
        raw = auth.get("raw_affiliation_strings") or []
        affiliation = (insts[0].get("display_name") if insts else None) or (raw[0] if raw else None)
        authors.append({
            "name": a.get("display_name") or "",
            "orcid": (a.get("orcid") or "").replace("https://orcid.org/", "") or None,
            "affiliation": affiliation,
        })
    doi = (work.get("doi") or "").replace("https://doi.org/", "") or None
    return {"found": True, "source": source, "title": work.get("title"), "doi": doi, "authors": authors}


def resolve(title: str | None, doi: str | None) -> dict:
    params = {"select": "title,doi,authorships"}
    if config.OPENALEX_MAILTO:
        params["mailto"] = config.OPENALEX_MAILTO
    try:
        with httpx.Client(timeout=8) as client:
            if doi:
                resp = client.get(f"{OPENALEX}/works/doi:{doi}", params=params)
                if resp.status_code == 200:
                    return _shape(resp.json(), "doi")
            if title and len(title.strip()) >= 10:
                resp = client.get(
                    f"{OPENALEX}/works",
                    params={**params, "filter": f"title.search:{title}", "per-page": 1},
                )
                resp.raise_for_status()
                results = resp.json().get("results") or []
                if results:
                    hit = results[0]
                    a, b = _norm_title(title), _norm_title(hit.get("title") or "")
                    # only trust a close title match: wrong-paper autofill would
                    # poison the COI/Author machinery
                    if a and b and (a == b or a in b or b in a):
                        return _shape(hit, "title")
    except Exception as exc:
        log.warning("Metadata resolution failed: %s", exc)
    return {"found": False, "source": None, "title": title, "doi": doi, "authors": []}


def _params(extra: dict) -> dict:
    if config.OPENALEX_MAILTO:
        return {**extra, "mailto": config.OPENALEX_MAILTO}
    return extra


def pdf_candidates(work: dict) -> list[dict]:
    """Fetchable PDF locations, repositories first.

    Publisher sites (RSC, Elsevier, Wiley) routinely 403 automated requests even
    for open-access articles; arXiv/Research Square/PMC copies do not.
    """
    cands = []
    for loc in work.get("locations") or []:
        if not loc.get("pdf_url"):
            continue
        src = loc.get("source") or {}
        cands.append({
            "url": loc["pdf_url"],
            "source": src.get("display_name"),
            "is_repository": src.get("type") == "repository",
        })
    cands.sort(key=lambda c: not c["is_repository"])
    return cands


PREPRINT_SOURCES = (
    "arxiv", "biorxiv", "medrxiv", "chemrxiv", "research square", "ssrn",
    "preprints.org", "osf", "hal", "zenodo", "techrxiv", "engrxiv", "psyarxiv",
    "earatxiv", "eartharxiv", "socarxiv", "authorea",
)


def _is_preprint(work: dict, cand: dict) -> bool:
    if work.get("type") == "preprint":
        return True
    src = (cand.get("source") or "").lower()
    return any(p in src for p in PREPRINT_SOURCES)


def list_importable_works(orcid: str) -> list[dict]:
    """The author's preprints that have a directly fetchable PDF.

    Preprints only: the workflow is post to arXiv/bioRxiv, review here, then
    post the revised version back to the preprint server.
    """
    with httpx.Client(timeout=8) as client:
        resp = client.get(
            f"{OPENALEX}/works",
            params=_params({
                "filter": f"author.orcid:{orcid}",
                "per-page": 50,
                "sort": "publication_date:desc",
                "select": "id,title,publication_year,type,doi,locations",
            }),
        )
        resp.raise_for_status()
    out = []
    for w in resp.json().get("results", []):
        cands = [c for c in pdf_candidates(w) if _is_preprint(w, c)]
        if not cands:
            continue
        out.append({
            "openalex_id": w["id"].rsplit("/", 1)[-1],
            "title": w.get("title"),
            "year": w.get("publication_year"),
            "type": w.get("type"),
            "doi": (w.get("doi") or "").replace("https://doi.org/", "") or None,
            "source": cands[0]["source"],
            "likely_fetchable": cands[0]["is_repository"],
        })
    return out


def fetch_work(openalex_id: str) -> dict:
    """Full work record for import: metadata, authorships, topics, PDF location."""
    if not re.fullmatch(r"W\d+", openalex_id):
        raise ValueError("Invalid OpenAlex work id")
    with httpx.Client(timeout=8) as client:
        resp = client.get(
            f"{OPENALEX}/works/{openalex_id}",
            params=_params({"select": "id,title,doi,authorships,topics,locations"}),
        )
        resp.raise_for_status()
        return resp.json()


def download_pdf(url: str, max_bytes: int) -> bytes:
    headers = {"User-Agent": f"OpenPeerReview/0.1 (mailto:{config.OPENALEX_MAILTO or 'unset'})"}
    with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
        resp = client.get(url)
        resp.raise_for_status()
        content = resp.content
    if len(content) > max_bytes:
        raise ValueError("PDF too large")
    if not content.startswith(b"%PDF-"):
        raise ValueError("URL did not return a PDF")
    return content
