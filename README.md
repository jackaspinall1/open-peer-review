# Open Peer Review

A web tool for open, public peer review of papers. A PDF is uploaded and becomes
publicly readable; reviewers sign in with their ORCID iD, highlight a passage, and
attach a comment. Comments are public, threaded, and up/down-votable.

Reviewers are **anonymous to readers** (per-paper pseudonyms: "Reviewer 1",
"Reviewer 2", …) but **known to the server**, which uses the ORCID to display a
conflict-of-interest badge on every comment:

| Badge | Meaning |
|---|---|
| Author | Commenter's ORCID matches a listed author |
| Co-author relationship found | Commenter shares published work with an author (via OpenAlex), with recent/not-recent only |
| Same institution | Overlapping employment with an author (via ORCID's public employment records), institution not named |
| No relationship found | No co-authorship or affiliation overlap detected |
| Unverifiable | No listed author has an ORCID |
| Verification pending | OpenAlex check failed; retried automatically |

### Anonymity and badge disclosure

Badges must carry enough for a reader to judge a comment and too little to
identify who wrote it. Magnitudes turned out to be the leak, and the anonymity
sets are measurable against OpenAlex:

- "20+ shared works with an author" has an anonymity set of **one** for a
  typical researcher (it names their single closest collaborator), and anyone
  can confirm it with a single API query.
- Naming an institution narrows a topic's author population by roughly three
  orders of magnitude (284,000 authors on a battery-materials topic; 339 of
  them at one named university).
- Topic membership alone is safe: OpenAlex topics carry authors in the tens of
  thousands.

So the public strings state the relationship and nothing quantitative: no
counts, no institution names, no author names, and no seniority proxies such as
work totals or years-active (which would also reimport the career hierarchy
that pseudonymity exists to remove). Recency of co-authorship is kept at one
bit, because funders commonly treat collaboration within 48 months as
disqualifying and that genuinely changes a reader's judgement.

The server still computes the full picture; it just does not publish it.

The checks run strongest-first: author-list match, then OpenAlex co-authorship
(one request per author; sorting by publication date descending with one result
yields the count and the most recent shared year in a single call), then
institutional overlap from `pub.orcid.org/v3.0/{orcid}/employments` (anonymous
access; organisations matched on disambiguated IDs such as RINGGOLD/ROR with a
normalised-name fallback, and employment date ranges intersected). ORCID
employment lists are optional and visibility-controlled, and many are empty, so
"No relationship found" means exactly that: not found, not disproved.

## The workflow

1. An author posts a preprint to arXiv / bioRxiv / ChemRxiv / Research Square.
2. They sign in here with ORCID and pick that preprint from their own list —
   the PDF, author list, ORCIDs, affiliations and topics are fetched
   automatically from OpenAlex. Nothing is typed, and you can only add papers
   your own ORCID is on.
3. Reviewers highlight sentences and comment under per-paper pseudonyms, with
   conflict-of-interest and topical-expertise badges computed from ORCID and
   OpenAlex.
4. The author posts a revised version to the preprint server and clicks "Check
   for new version": the paper advances to v2 and comments re-anchor — text
   that moved re-attaches, text that was rewritten surfaces as unresolved,
   which is the review loop working.

Manual PDF upload is still available for papers that are not indexed yet.

## Running it

Backend (terminal 1):

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # first time only
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Frontend (terminal 2):

```bash
cd frontend
npm install        # first time only
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api` and `/auth` to the
backend, so everything is same-origin.

## Auth modes

Configuration lives in `backend/.env` (copy `backend/.env.example`; gitignored).
`AUTH_MODE` is one of:

- `mock` — dev login form only: any well-formed ORCID iD, no external account
- `orcid` — real ORCID sign-in only
- `both` (the `.env.example` default) — ORCID button plus the dev form, handy for
  testing multi-user scenarios locally when you only own one real ORCID

To enable real ORCID sign-in:

1. Sign in at orcid.org → click your name → **Developer tools**
   (https://orcid.org/developer-tools). You may need to verify your email first.
2. Register a **public API client** (free). Name/description/URL can be anything;
   the **redirect URI must be exactly** `http://localhost:5173/auth/orcid/callback`.
   (If ORCID refuses a plain-http URI, use `ORCID_ENV=sandbox` with a client
   registered at sandbox.orcid.org — sandbox accounts need mailinator.com emails —
   or keep using mock mode until deployment gives you an https URL.)
3. Copy the client ID and secret into `backend/.env`
   (`ORCID_CLIENT_ID=APP-…`, `ORCID_CLIENT_SECRET=…`) and restart the backend.

Also in `.env`: `SECRET_KEY` (set a long random string for anything non-local) and
`OPENALEX_MAILTO=you@example.com` (joins OpenAlex's polite, faster request pool).

## Seeding a document from the CLI

```bash
cd backend
.venv/bin/python seed.py paper.pdf "Paper title" --doi 10.1000/xyz \
  --author "Jane Doe:0000-0002-1825-0097" --author "John Smith"
```

## End-to-end test

With both servers running and a document with id 1 present:

```bash
cd frontend
npx playwright install chromium   # first time only
SP=/tmp node e2e.mjs              # SP = where screenshots are written
```

It exercises: PDF rendering, mock login, text selection → anchored comment,
highlight re-anchoring after reload, and highlight↔sidebar focus.

## How anchoring works

Comments store a W3C-style text quote selector: `{page, quote, prefix, suffix,
start, end}` where offsets index into a canonical per-page string built from the
PDF.js text layer (`item.str` + `'\n'` for `hasEOL`). On load, the quote is
searched (exactly) in its page's text — prefix/suffix disambiguate repeats and
stored offsets are only a hint — then mapped back to DOM ranges and drawn as
absolutely-positioned highlight divs.

Documents carry a version, bumped when the original uploader posts a revision
("Upload revision" in the viewer). Comments are stamped with the version they
were written on. On an unchanged version, a quote missing from its page simply
pins ("approx.") — never re-attaches elsewhere. Once a newer version exists,
older comments may re-attach: the search expands outward from the stored page
across the whole document, scoring candidates by surrounding context; short
quotes (a single word) re-attach only when the stored context corroborates the
match, else they pin. Matching stays exact by design — a reworded passage means
the authors revised it, and should surface as unresolved rather than fuzzy-match
onto the new wording. A comment is never dropped. `pdfjs-dist` is pinned (~6.2.108) because
the text-layer DOM and text normalisation can shift between majors.

## Layout

```
backend/app/       FastAPI: models.py (schema), auth.py (mock + ORCID OAuth),
                   coi.py (OpenAlex check), serialize.py (identity-masking),
                   routes/documents.py, routes/comments.py
frontend/src/pdf/  pdfSetup.js (worker), anchors.js (pure anchor maths),
                   PdfPage.jsx (canvas + text layer + highlights), PdfViewer.jsx
frontend/src/      pages/, components/ (sidebar, threads, votes, badges)
data/              SQLite DB + uploaded PDFs (gitignored — delete to reset)
```

Anonymity note: the public API never returns names, ORCIDs, or user ids — only
aliases and COI badges (enforced in `backend/app/serialize.py`). Aliases are
per-document, so activity is not linkable across papers.

## License

AGPL-3.0. The pseudonymity and conflict-of-interest machinery only deserves
trust if it can be audited, and network copyleft keeps hosted forks equally
auditable.
