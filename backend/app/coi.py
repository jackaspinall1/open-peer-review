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
import json
import logging
from datetime import datetime, timedelta

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


def _shared_works(client: httpx.Client, orcid_a: str, orcid_b: str) -> tuple[int, int | None, set[str]]:
    """(normal co-authored works, year of the most recent one, large-work ids).

    "Normal" means at or below LARGE_WORK_AUTHORS authors: an actual
    collaboration rather than a shared appearance on a community roadmap.
    """
    params = {
        "filter": f"author.orcid:https://orcid.org/{orcid_a},author.orcid:https://orcid.org/{orcid_b}",
        "per-page": 50,
        "sort": "publication_date:desc",
        "select": "id,publication_year,authorships",
    }
    if config.OPENALEX_MAILTO:
        params["mailto"] = config.OPENALEX_MAILTO
    resp = client.get(f"{OPENALEX}/works", params=params)
    resp.raise_for_status()
    normal, latest, large = 0, None, set()
    for w in resp.json().get("results", []):
        if len(w.get("authorships") or []) > LARGE_WORK_AUTHORS:
            large.add(w["id"])  # ids, not a count: one roadmap can contain several authors
            continue
        normal += 1
        year = w.get("publication_year")
        if year and (latest is None or year > latest):
            latest = year
    return normal, latest, large


# Disclosure policy (see README "Anonymity and badge disclosure").
#
# Badges must support judgement without identifying the reviewer. Magnitudes are
# the leak: measured against OpenAlex, "20+ shared works with an author" has an
# anonymity set of ONE for typical researchers (their single closest
# collaborator), and anyone can confirm it with one API query. Institution names
# narrow a topic's author population by roughly three orders of magnitude.
#
# So the public strings carry the RELATIONSHIP and nothing quantitative: no
# counts, no institution names, no author names, no seniority proxies. Recency
# is kept at one bit because it is genuinely decision-relevant (funders commonly
# treat collaboration within 48 months as disqualifying).
RECENT_YEARS = 4

# Roadmaps, consortium reports and community reviews gather contributors from
# across a whole field, so they create co-authorship edges that are not
# collaborations in any meaningful sense. Measured on a real record: one
# 50-author roadmap supplied 46 of that researcher's 91 co-author edges. Works
# above this many authors therefore signal a weaker relationship, reported
# separately rather than as co-authorship.
LARGE_WORK_AUTHORS = 15

# One shared roadmap says almost nothing: those papers gather a whole field, and
# labelling an independent reviewer "conflicted" on that basis discredits
# legitimate criticism for no reason. Repeatedly appearing on the same
# consortium outputs is different, since it usually means a shared programme.
# Below this many DISTINCT large works, the relationship is reported as none
# (the tooltip still says what was found, so nothing is hidden).
LARGE_COLLAB_MIN = 3


def _topic_ref(t: dict) -> dict:
    return {
        "id": t["id"].rsplit("/", 1)[-1],
        "name": t["display_name"],
        "subfield_id": t["subfield"]["id"].rsplit("/", 1)[-1],
        "subfield_name": t["subfield"]["display_name"],
        "field_id": t["field"]["id"].rsplit("/", 1)[-1],
        "field_name": t["field"]["display_name"],
    }


def classify_document(doc) -> list[dict] | None:
    """Topics for a paper: by DOI when OpenAlex has it, else title classification."""
    params = {}
    if config.OPENALEX_MAILTO:
        params["mailto"] = config.OPENALEX_MAILTO
    try:
        with httpx.Client(timeout=8) as client:
            topics = []
            if doc.doi:
                resp = client.get(f"{OPENALEX}/works/doi:{doc.doi}", params={**params, "select": "topics"})
                if resp.status_code == 200:
                    topics = resp.json().get("topics") or []
            if not topics:
                resp = client.get(f"{OPENALEX}/text/topics", params={**params, "title": doc.title})
                resp.raise_for_status()
                topics = resp.json().get("topics") or []
            return [_topic_ref(t) for t in topics[:3]]
    except Exception as exc:
        log.warning("Topic classification failed for doc %s: %s", doc.id, exc)
        return None


def compute_expertise(user: User, doc_topics: list[dict] | None) -> tuple[str, str]:
    """Reviewer's topical publication record vs this paper. Bucketed, no titles,
    no institutions — career hierarchy is deliberately not displayed."""
    if not doc_topics:
        return "pending", "Paper not yet classified"
    params = {"filter": f"orcid:{user.orcid}", "select": "topics,works_count"}
    if config.OPENALEX_MAILTO:
        params["mailto"] = config.OPENALEX_MAILTO
    with httpx.Client(timeout=8) as client:
        resp = client.get(f"{OPENALEX}/authors", params=params)
        resp.raise_for_status()
        results = resp.json().get("results") or []
        if not results or not results[0].get("works_count"):
            return "no_record", "No publications found for this ORCID iD"
        mine = [dict(_topic_ref(t), count=t.get("count", 0)) for t in results[0].get("topics") or []]

    # Level only. Work counts and years-active are withheld: both are seniority
    # proxies that shrink the anonymity set, and neither changes the judgement a
    # reader makes (does this person work in this area, yes or no).
    for id_field, level, phrase in (
        ("id", "topic", "Publishes on this paper's topic"),
        ("subfield_id", "subfield", "Publishes in this paper's subfield"),
        ("field_id", "field", "Publishes in this paper's broader field"),
    ):
        doc_ids = {t[id_field] for t in doc_topics}
        if any(t[id_field] in doc_ids for t in mine):
            return level, phrase
    return "none", "No publication record in this paper's area"


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
            hits, large_ids = [], set()
            for a in with_orcid:
                n, latest, large = _shared_works(client, my_orcid, _norm(a.orcid))
                if n > 0:
                    hits.append((n, latest))
                large_ids |= large
            if hits:
                hits.sort(key=lambda h: (h[1] or 0, h[0]), reverse=True)
                latest = hits[0][1]
                recent = latest is not None and (datetime.now().year - int(latest)) <= RECENT_YEARS
                return "coauthor", (
                    "Has co-authored with an author of this paper in the last "
                    f"{RECENT_YEARS} years" if recent
                    else "Has co-authored with an author of this paper, but not recently"
                )
            if len(large_ids) >= LARGE_COLLAB_MIN:
                return "large_collab", (
                    f"Appears on {LARGE_COLLAB_MIN} or more large multi-author works "
                    "with an author of this paper (roadmaps or consortium papers), which "
                    "often means a shared programme"
                )
            if large_ids:
                return "none", (
                    "No substantive co-authorship found; shares only an occasional "
                    "large multi-author paper, such as a field-wide roadmap"
                )
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
                        # institution name withheld: it narrows a topic's author
                        # population by ~3 orders of magnitude
                        return "colleague", "Shares an institution with an author of this paper"
    except Exception as exc:
        log.warning("ORCID employment check failed for %s: %s", user.orcid, exc)
        # co-authorship already came back clean; degrade to 'none' rather than pending

    if without:
        return "none", f"{without} of {len(document.authors)} author(s) could not be checked (no ORCID)"
    return "none", "No co-authorship found"


def compute_alias_badges(document_id: int, user_id: int) -> None:
    """Fill in a reviewer's badges. Runs off the request path.

    The checks make one OpenAlex request per author with an ORCID, so on a
    fourteen-author paper this took five seconds inline: a reviewer clicked
    "Post comment" and waited. The comment now posts immediately and the badges
    resolve a moment later, which is also what the lazy retry path expects.
    """
    from .db import SessionLocal

    db = SessionLocal()
    try:
        alias = (
            db.query(ReviewerAlias)
            .filter(ReviewerAlias.document_id == document_id, ReviewerAlias.user_id == user_id)
            .one_or_none()
        )
        if alias is None:
            return
        document, user = db.get(Document, document_id), db.get(User, user_id)
        if document is None or user is None:
            return
        if alias.coi_status == "pending":
            alias.coi_status, alias.coi_detail = compute_coi(user, document)
        if alias.expertise_level == "pending":
            if document.topics_json is None:
                topics = classify_document(document)
                if topics is not None:
                    document.topics_json = json.dumps(topics)
            try:
                alias.expertise_level, alias.expertise_detail = compute_expertise(
                    user, json.loads(document.topics_json) if document.topics_json else None)
            except Exception as exc:
                log.warning("Expertise check failed for %s: %s", user.orcid, exc)
        alias.coi_checked_at = utcnow()
        db.commit()
    except Exception as exc:
        log.warning("Badge computation failed for user %s on doc %s: %s", user_id, document_id, exc)
    finally:
        db.close()


def get_or_create_relationship(db: Session, document: Document, user: User) -> ReviewerAlias:
    """This user's standing on this paper, with no alias number yet.

    Exists so a badge can be shown to someone before they comment: the
    relationship is a property of (person, paper), while the pseudonym is only
    needed once they speak.
    """
    alias = (
        db.query(ReviewerAlias)
        .filter(ReviewerAlias.document_id == document.id, ReviewerAlias.user_id == user.id)
        .one_or_none()
    )
    if alias is None:
        # Authorship is a list comparison with no network cost, so settle it now
        # rather than showing an author "checking..." and then "Author".
        is_author = _norm(user.orcid) in {_norm(a.orcid) for a in document.authors if a.orcid}
        alias = ReviewerAlias(
            document_id=document.id,
            user_id=user.id,
            coi_status="author" if is_author else "pending",
            coi_detail="Commenter is a listed author" if is_author else None,
            expertise_level="pending",
        )
        db.add(alias)
        db.commit()
    return alias


def get_or_create_alias(db: Session, document: Document, user: User) -> ReviewerAlias:
    """As above, but also assigns the pseudonym, for someone about to comment."""
    alias = get_or_create_relationship(db, document, user)
    if alias.alias_number is None:
        alias.alias_number = (
            db.query(func.coalesce(func.max(ReviewerAlias.alias_number), 0))
            .filter(ReviewerAlias.document_id == document.id)
            .scalar()
        ) + 1
        db.commit()
    return alias


def refresh_pending(db: Session, document: Document) -> None:
    """Lazily retry failed COI checks when the document is fetched (rate-limited)."""
    pending = (
        db.query(ReviewerAlias)
        .filter(
            ReviewerAlias.document_id == document.id,
            (ReviewerAlias.coi_status == "pending") | (ReviewerAlias.expertise_level == "pending"),
        )
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
        if alias.coi_status == "pending":
            alias.coi_status, alias.coi_detail = compute_coi(user, document)
        if alias.expertise_level == "pending":
            if document.topics_json is None:
                topics = classify_document(document)
                if topics is not None:
                    document.topics_json = json.dumps(topics)
            try:
                alias.expertise_level, alias.expertise_detail = compute_expertise(
                    user, json.loads(document.topics_json) if document.topics_json else None)
            except Exception as exc:
                log.warning("Expertise retry failed for %s: %s", user.orcid, exc)
        alias.coi_checked_at = now
        changed = True
    if changed:
        db.commit()


def refresh_pending_detached(document_id: int) -> None:
    """Background wrapper for refresh_pending, with its own session."""
    from .db import SessionLocal

    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is not None:
            refresh_pending(db, document)
    except Exception as exc:
        log.warning("Badge retry failed for doc %s: %s", document_id, exc)
    finally:
        db.close()
