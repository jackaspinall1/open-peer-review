"""Conflict-of-interest assessment, cached per (user, document).

Signals, strongest first:
  author    - commenter's ORCID is on the author list
  coauthor  - shared works via OpenAlex (comma-joined author.orcid filters AND
              together; sort=publication_date:desc&per-page=1 also yields the most
              recent shared year in the same request)
  colleague - overlapping employment via ORCID's public API (pub.orcid.org,
              anonymous). Employment records are optional and visibility-controlled
              (often empty), so this is best-effort: absence proves nothing.
  none / unverifiable / pending
"""
import logging
from datetime import timedelta

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import config
from .models import Document, ReviewerAlias, User, utcnow

log = logging.getLogger(__name__)

OPENALEX = "https://api.openalex.org"
RETRY_AFTER = timedelta(minutes=5)


def _norm(orcid: str) -> str:
    return orcid.strip().upper().replace("HTTPS://ORCID.ORG/", "")


def _shared_works(client: httpx.Client, orcid_a: str, orcid_b: str) -> tuple[int, int | None]:
    """(number of co-authored works, year of the most recent one)."""
    params = {
        "filter": f"author.orcid:https://orcid.org/{orcid_a},author.orcid:https://orcid.org/{orcid_b}",
        "per-page": 1,
        "sort": "publication_date:desc",
        "select": "publication_year",
    }
    if config.OPENALEX_MAILTO:
        params["mailto"] = config.OPENALEX_MAILTO
    resp = client.get(f"{OPENALEX}/works", params=params)
    resp.raise_for_status()
    data = resp.json()
    count = data.get("meta", {}).get("count", 0)
    results = data.get("results", [])
    latest = results[0].get("publication_year") if results else None
    return count, latest


def _norm_org_name(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum() or ch == " ").strip()


def _fetch_employments(client: httpx.Client, orcid: str) -> list[dict]:
    """Public employment entries: org match keys + comparable date range.

    Soft signal only: many records are empty (unlisted or private).
    """
    resp = client.get(
        f"https://pub.orcid.org/v3.0/{orcid}/employments",
        headers={"Accept": "application/json"},
    )
    resp.raise_for_status()
    out = []
    for group in resp.json().get("affiliation-group", []):
        for summary in group.get("summaries", []):
            e = summary.get("employment-summary") or {}
            org = e.get("organization") or {}
            if not org.get("name"):
                continue
            keys = {_norm_org_name(org["name"])}
            dis = org.get("disambiguated-organization") or {}
            if dis.get("disambiguated-organization-identifier"):
                keys.add(f"{dis.get('disambiguation-source')}:{dis['disambiguated-organization-identifier']}")

            def bound(d, default):
                if not d or not d.get("year"):
                    return default
                y = int(d["year"]["value"])
                m = int(d["month"]["value"]) if d.get("month") else default[1]
                day = int(d["day"]["value"]) if d.get("day") else default[2]
                return (y, m, day)

            out.append({
                "name": org["name"],
                "keys": keys,
                "start": bound(e.get("start-date"), (0, 1, 1)),
                "end": bound(e.get("end-date"), (9999, 12, 31)),
            })
    return out


def _overlapping_org(mine: list[dict], theirs: list[dict]) -> str | None:
    """Name of an organisation where the two employment periods intersect."""
    for a in mine:
        for b in theirs:
            if a["keys"] & b["keys"] and a["start"] <= b["end"] and b["start"] <= a["end"]:
                return b["name"]
    return None


def compute_coi(user: User, document: Document) -> tuple[str, str]:
    """Return (status, detail). Status: author|coauthor|none|unverifiable|pending."""
    my_orcid = _norm(user.orcid)
    with_orcid = [a for a in document.authors if a.orcid]
    without = len(document.authors) - len(with_orcid)

    for a in with_orcid:
        if _norm(a.orcid) == my_orcid:
            return "author", "Commenter is a listed author"
    if not with_orcid:
        return "unverifiable", "No authors have ORCID iDs"

    try:
        with httpx.Client(timeout=5) as client:
            hits = []
            for a in with_orcid:
                n, latest = _shared_works(client, my_orcid, _norm(a.orcid))
                if n > 0:
                    hits.append((n, latest, a.name))
            if hits:
                hits.sort(key=lambda h: (h[1] or 0, h[0]), reverse=True)
                n, latest, name = hits[0]
                recency = f", most recent {latest}" if latest else ""
                more = f" (and {len(hits) - 1} other author(s))" if len(hits) > 1 else ""
                return "coauthor", f"{n} shared work(s) with {name}{recency}{more}"
    except Exception as exc:  # network/API failure: report pending, retry later
        log.warning("OpenAlex COI check failed for %s: %s", user.orcid, exc)
        return "pending", "Check not yet completed"

    # Institutional overlap — best-effort: ORCID employment lists are often empty
    try:
        with httpx.Client(timeout=5) as client:
            mine = _fetch_employments(client, my_orcid)
            if mine:
                for a in with_orcid:
                    org = _overlapping_org(mine, _fetch_employments(client, _norm(a.orcid)))
                    if org:
                        return "colleague", f"Commenter and {a.name} both affiliated with {org}"
    except Exception as exc:
        log.warning("ORCID employment check failed for %s: %s", user.orcid, exc)
        # co-authorship already came back clean; degrade to 'none' rather than pending

    if without:
        return "none", f"{without} of {len(document.authors)} author(s) could not be checked (no ORCID)"
    return "none", "No co-authorship found"


def get_or_create_alias(db: Session, document: Document, user: User) -> ReviewerAlias:
    alias = (
        db.query(ReviewerAlias)
        .filter(ReviewerAlias.document_id == document.id, ReviewerAlias.user_id == user.id)
        .one_or_none()
    )
    if alias is not None:
        return alias
    next_number = (
        db.query(func.coalesce(func.max(ReviewerAlias.alias_number), 0))
        .filter(ReviewerAlias.document_id == document.id)
        .scalar()
    ) + 1
    status, detail = compute_coi(user, document)
    alias = ReviewerAlias(
        document_id=document.id,
        user_id=user.id,
        alias_number=next_number,
        coi_status=status,
        coi_detail=detail,
        coi_checked_at=utcnow(),
    )
    db.add(alias)
    db.commit()
    return alias


def refresh_pending(db: Session, document: Document) -> None:
    """Lazily retry failed COI checks when the document is fetched (rate-limited)."""
    pending = (
        db.query(ReviewerAlias)
        .filter(ReviewerAlias.document_id == document.id, ReviewerAlias.coi_status == "pending")
        .all()
    )
    now = utcnow()
    changed = False
    for alias in pending:
        checked = alias.coi_checked_at
        if checked is not None and checked.tzinfo is None:
            checked = checked.replace(tzinfo=now.tzinfo)
        if checked is not None and now - checked < RETRY_AFTER:
            continue
        user = db.get(User, alias.user_id)
        alias.coi_status, alias.coi_detail = compute_coi(user, document)
        alias.coi_checked_at = now
        changed = True
    if changed:
        db.commit()
