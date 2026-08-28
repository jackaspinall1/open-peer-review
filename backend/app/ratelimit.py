"""Per-user rate limits.

Tuned to keep comments considered without getting in the way of someone reading
a paper and flagging several typos as they go: five comments a minute allows a
burst of small corrections, and asks for a pause before a hundred.

Keyed on the user rather than the IP address, since every write requires a
signed-in ORCID account. In-memory and therefore per-process: it resets on
deploy and would not be shared across machines, which is fine while this runs as
a single instance and is the first thing to revisit if it ever does not.
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException

_hits: dict[tuple[str, int], deque] = defaultdict(deque)
_last_prune = 0.0
PRUNE_EVERY = 300


def _prune(now: float) -> None:
    global _last_prune
    if now - _last_prune < PRUNE_EVERY:
        return
    _last_prune = now
    for key in [k for k, dq in _hits.items() if not dq or now - dq[-1] > 3600]:
        del _hits[key]


def check(bucket: str, user_id: int, limit: int, per_seconds: int, what: str) -> None:
    """Raise 429 if this user has exceeded `limit` actions in the window."""
    now = time.monotonic()
    _prune(now)
    hits = _hits[(bucket, user_id)]
    while hits and now - hits[0] >= per_seconds:
        hits.popleft()
    if len(hits) >= limit:
        wait = int(per_seconds - (now - hits[0])) + 1
        raise HTTPException(
            status_code=429,
            detail=f"You are {what} quickly. Try again in {wait} second{'' if wait == 1 else 's'}.",
            headers={"Retry-After": str(wait)},
        )
    hits.append(now)


def reset() -> None:
    """Clear all counters (used by tests)."""
    _hits.clear()
