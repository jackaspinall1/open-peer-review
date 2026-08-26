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
| Co-author relationship found | Commenter shares a normal-sized published work with an author (via OpenAlex), with recent/not-recent only |
| Large-collaboration co-author | Appears on 3 or more works with over 15 authors (roadmaps, consortium papers) with an author, which often means a shared programme |
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

Community roadmaps and consortium papers gather contributors from across a whole
field, so they create co-authorship edges that are not collaborations in any
meaningful sense. On a real record, a single 50-author roadmap supplied 46 of
that researcher's 91 co-author edges. Works with more than 15 authors therefore
do not count as co-authorship, and recency is measured from normal-sized works
only.

Count matters as well as size. Sharing one field-wide roadmap says almost
nothing, and labelling an independent reviewer conflicted on that basis
discredits legitimate criticism for no reason, so a single such work is reported
as no relationship (the tooltip still states what was found, so nothing is
hidden). Three or more distinct large works with the same author usually
indicates a shared programme, and that does earn the weaker badge. Distinct
works are counted rather than per-author matches, since one roadmap commonly
contains several of a paper's authors.

The checks run strongest-first: author-list match, then OpenAlex co-authorship
(one request per author; sorting by publication date descending with one result
yields the count and the most recent shared year in a single call), then
institutional overlap from `pub.orcid.org/v3.0/{orcid}/employments` (anonymous
access; organisations matched on disambiguated IDs such as RINGGOLD/ROR with a
normalised-name fallback, and employment date ranges intersected). ORCID
employment lists are optional and visibility-controlled, and many are empty, so
"No relationship found" means exactly that: not found, not disproved.

## One paper, one discussion

A second copy of a paper would split its review in two, so papers are
deduplicated on import and upload. Adding a paper that is already here simply
opens the existing discussion rather than creating a rival one.

Two identity keys are used. The OpenAlex work id is preferred because OpenAlex
merges a preprint with its published version into a single work, so the key
survives that transition. The DOI is the fallback, stored version-stripped,
because preprint servers mint a DOI per version and the raw form would make v1
and v2 look like different papers. Manually uploaded papers with no DOI cannot
be deduplicated reliably and are not.

Control over a paper (opening a review round, extending it, posting a revision)
belongs to **any listed author**, matched by ORCID, not only to whoever added
it. Otherwise a non-author who added a paper first would lock its real authors
out of reviewing their own work.

## Review rounds

Review happens in a bounded window per version, because reviewing is solicited
work: an open-ended invitation slides, a dated one gets answered. The author
opens a round explicitly, which is also the moment to go and ask colleagues to
look, since a direct request from an author is the highest-converting message in
the whole system.

- **Two weeks**, extendable a week at a time up to a month when engagement is
  thin. There is no deadline on the author afterwards: revising is their own
  work, and "revise within 30 days" is a journal pathology this avoids.
- The author's only discretionary lever **increases scrutiny**: they can extend
  but never close early, so no rules are needed about who deserves an extension.
- **The window bounds the record, not the page.** Comments posted after it are
  still accepted, marked "after the window", and excluded from the round's
  counts. Losing a correct criticism to a deadline would be exactly the kind of
  dysfunction that checks are meant to prevent.
- The round is displayed with its dates, extensions and participation, so a thin
  round reads as thin instead of hiding behind the word "reviewed". A countdown
  is public, because urgency nobody can see motivates nobody, and the author is
  nudged to go and ask people when the window is closing quietly.

## Moderation

Deliberately minimal and reversible, because gates are what make review systems
dysfunctional. Nothing is ever held for approval: comments publish immediately,
reports queue for a human and hide nothing by themselves, and removal happens
after the fact.

- **Delete your own comment**: soft delete. The text goes, the thread and any
  replies remain readable, and the card shows "[deleted by the commenter]".
- **Report**: any signed-in reader can flag a comment. Moderators see the queue
  at `GET /api/admin/reports`, which includes the reporter's relationship to the
  paper, since the predictable abuse of reporting is authors flagging criticism
  of their own work.
- **Moderator removal**: ORCID iDs listed in `ADMIN_ORCIDS` can remove any
  comment; it is labelled "[removed by a moderator]" rather than vanishing.
- **The standard is one line**: criticise the work, not the person. It permits
  unlimited harshness toward the science, which is the point. No tone filtering:
  softening blunt criticism would reproduce the failure this project exists to
  fix.

Sanctions beyond removal are intentionally absent for now. Because accounts are
ORCID iDs, which cannot be cheaply abandoned, a ban is already a heavy sanction,
and comments are pseudonymous to readers but not to the operator.

## What this is, and what it will not become

Public-good infrastructure, run non-commercially. That is a commitment about
governance rather than a licence detail, and it has three practical
consequences.

It makes the content position unambiguous. Many preprints carry non-commercial
licences (of one researcher's seven, four are CC BY-NC-ND), which a commercial
service could not host at all. The corollary is that this cannot later become a
paid product without removing those papers or seeking fresh permission.

It sets the sustainability question correctly. Hosting costs a few pounds a
month; the real risk to scholarly tools is not money but abandonment when one
person's attention moves on. The answer is to make the platform disposable:
reviews are intended to be deposited as citable archival artifacts (see
TODO.md), so the record outlives the service that produced it. That is a better
answer to "why invest effort here" than any promise of longevity.

It explains the licence choice. AGPL-3.0 keeps hosted forks equally auditable,
which matters because the anonymity and conflict-of-interest machinery only
deserves trust if it can be inspected.

## Papers, licences, and takedown

Papers are added by their own authors: importing requires the signed-in user's
ORCID to appear on the work, and both the import and upload paths state that the
depositor confirms they have the right to post on behalf of their co-authors.
That is what every repository does, and it matters because copyright in a paper
is usually held jointly by all authors while preprint servers take only
non-exclusive rights, so the authors remain free to license a copy here.

The licence recorded by OpenAlex is stored at import and displayed on the paper
page alongside a link to the original on the preprint server, which satisfies
the attribution that CC licences require and keeps the canonical version
primary. Any listed author can ask for a paper to be removed.

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

Also in `.env`: `OPENALEX_MAILTO=you@example.com` (joins OpenAlex's polite,
faster request pool) and `SECRET_KEY`, which signs session cookies. Anyone who
knows that key can forge a login as any ORCID iD, so there is deliberately no
default: set a long random string, or leave it blank and one will be generated
and stored in `data/secret_key` (mode 600). Generate one with
`python3 -c "import secrets; print(secrets.token_urlsafe(48))"`. Changing it
signs everyone out, which is the intended behaviour if a key is ever exposed.

## Seeding a document from the CLI

```bash
cd backend
.venv/bin/python seed.py paper.pdf "Paper title" --doi 10.1000/xyz \
  --author "Jane Doe:0000-0002-1825-0097" --author "John Smith"
```

## Deployment

The app builds into a single container: FastAPI serves the built frontend
alongside the API, so there is one process, one thing to deploy, and no
cross-origin cookie handling. It cannot be hosted as a static site, because the
comments need shared storage and the ORCID token exchange needs a server-side
client secret.

It needs a persistent disk. `DATA_DIR` holds the SQLite database and the PDFs,
so without a mounted volume every deploy discards the reviews.

```bash
fly auth login
fly launch --no-deploy --name <app-name>          # fly.toml is already written
fly volumes create review_data --size 1 --region lhr
fly secrets set \
  SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')" \
  ORCID_CLIENT_ID=APP-XXXX ORCID_CLIENT_SECRET=xxxx \
  ORCID_REDIRECT_URI=https://<your-domain>/auth/orcid/callback \
  FRONTEND_URL=https://<your-domain> \
  ADMIN_ORCIDS=0000-0000-0000-0000 \
  OPENALEX_MAILTO=you@example.com
fly deploy
fly certs add <your-domain>                        # then add the DNS records it prints
```

Finally add `https://<your-domain>/auth/orcid/callback` as a redirect URI on the
ORCID client, at which point the login flow no longer needs a bounce page.

## Tests

```bash
cd backend && .venv/bin/python -m pytest tests -q
```

`tests/test_anonymity.py` asserts the product's central promise: that public
payloads never carry a name, ORCID, institution or work count, and that aliases
do not link a person across papers. These are the regressions that would be
most damaging and least visible, so they are checked automatically rather than
by hand. Tests stub out OpenAlex and ORCID, so they run offline.

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
