"""Paper metadata from OpenAlex.

Papers are only ever added by their own authors, from their own indexed record.
ORCIDs come solely from a work's own authorships, never from a name search,
because a wrong ORCID would grant someone else's "Author" badge.
"""
import logging
import re
import time

import httpx

from . import config

log = logging.getLogger(__name__)

OPENALEX = "https://api.openalex.org"


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


def _get(client: httpx.Client, url: str, params: dict) -> httpx.Response:
    """GET with one retry on 429.

    OpenAlex rate limits by burst as well as by daily quota, and a transient
    429 should not turn into "could not reach OpenAlex" for a user trying to
    add a paper.
    """
    for attempt in range(2):
        resp = client.get(url, params=params)
        if resp.status_code == 429 and attempt == 0:
            time.sleep(float(resp.headers.get("Retry-After", 2)))
            continue
        resp.raise_for_status()
        return resp
    resp.raise_for_status()
    return resp


def _params(extra: dict) -> dict:
    """Query params with the polite-pool mailto attached when configured."""
    if config.OPENALEX_MAILTO:
        return {**extra, "mailto": config.OPENALEX_MAILTO}
    return extra


PREPRINT_SOURCES = (
    "arxiv", "biorxiv", "medrxiv", "chemrxiv", "research square", "ssrn",
    "preprints.org", "osf", "hal", "zenodo", "techrxiv", "engrxiv", "psyarxiv",
    "earatxiv", "eartharxiv", "socarxiv", "authorea",
)


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
            "landing_url": loc.get("landing_page_url"),
            "source": src.get("display_name"),
            "license": loc.get("license"),
            "is_repository": src.get("type") == "repository",
        })
    cands.sort(key=lambda c: not c["is_repository"])
    return cands


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
        resp = _get(
            client,
            f"{OPENALEX}/works",
            _params({
                "filter": f"author.orcid:{orcid}",
                "per-page": 50,
                "sort": "publication_date:desc",
                "select": "id,title,publication_year,type,doi,locations",
            }),
        )
    out = []
    for w in resp.json().get("results", []):
        cands = [c for c in pdf_candidates(w) if _is_preprint(w, c)]
        if not cands:
            continue
        out.append({
            "openalex_id": w["id"].rsplit("/", 1)[-1],
            "document_id": None,   # filled in by the route: already added or not
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
        resp = _get(
            client,
            f"{OPENALEX}/works/{openalex_id}",
            _params({"select": "id,title,doi,authorships,topics,locations"}),
        )
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


def normalise_doi(doi: str | None) -> str | None:
    """Version-stripped, lowercase DOI, used as an identity key.

    Preprint servers mint a DOI per version (10.21203/rs.3.rs-6759455/v1), so
    the raw DOI would make v1 and v2 look like different papers.
    """
    if not doi:
        return None
    d = doi.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if d.startswith(prefix):
            d = d[len(prefix):]
    d = re.sub(r"/v\d+$", "", d)
    # bioRxiv/medRxiv append the version without a separator; only strip there,
    # since a bare trailing "v<digits>" is legitimate in other DOIs.
    if d.startswith("10.1101/"):
        d = re.sub(r"v\d+$", "", d)
    return d or None
