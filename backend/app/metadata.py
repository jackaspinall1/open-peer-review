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
