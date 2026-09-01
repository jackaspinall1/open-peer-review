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

OpenAlex is called **twice per reviewer, ever**, not once per author of every
paper. A reviewer's own works are fetched once and cached as a profile: which
ORCIDs they have published with, the most recent normal-sized collaboration with
each, any shared large works, and their own topics. Every paper they then touch
is a local set intersection costing nothing.

This matters because the free tier is metered. The API reports a limit of 1,000
credits at $0.0001 each, and the previous approach asked one question per author
per reviewer per paper: about fifteen requests for each new reviewer on a
fourteen-author preprint, which would exhaust the allowance after roughly
sixty-five reviewer-paper pairs. Two per reviewer is comfortable. Profiles are
rebuilt after thirty days.

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

- **Two weeks**, and there is no deadline on the author afterwards: revising is
  their own work, and "revise within 30 days" is a journal pathology this avoids.
- Extending is possible **only in the last three days** of a window, a week at a
  time, up to a month in total. A deadline you can postpone on day one is not a
  deadline, and whether you actually need longer cannot be answered honestly
  until the window has nearly run. Taking an extension asks for confirmation and
  says that it will appear on the review record, because it does.
- The author's only discretionary lever **increases scrutiny**: they can extend
  but never close early, so no rules are needed about who deserves an extension.
- **The window bounds the record, not the page.** Comments posted after it are
  still accepted, marked "after the window", and excluded from the round's
  counts. Losing a correct criticism to a deadline would be exactly the kind of
  dysfunction that checks are meant to prevent.
- A timeline and countdown sit in the paper's metadata line, next to the link
  to the original, so the deadline is visible to everyone without a banner:
  urgency nobody can see motivates nobody. The tooltip carries the dates,
  extensions and participation, so a thin round reads as thin instead of hiding
  behind the word "reviewed", and the author is nudged in the comment sidebar to
  go and ask people when the window is closing quietly.

## Knowing how you will appear

Above the comments, a signed-in reader sees the labels their own comment would
carry: their pseudonym or "Author", their conflict-of-interest badge and their
expertise badge. People should know how they will be presented before deciding
what to say, and finding out you are flagged as a co-author underneath a comment
you have already posted is a poor way to learn how this works.

The pseudonym itself is assigned on a person's first comment rather than their
first visit. Handing numbers to silent viewers would waste them and, worse, let
gaps in the sequence hint at how many people had opened the paper.

Authorship is settled immediately since it is only a comparison against the
author list; the co-authorship and expertise lookups resolve a moment later,
with the panel showing that it is checking meanwhile.

## Notifications

A reply to your comment raises a notification, shown as a count beside your name
and listed on your own page with the reply and a link back to the thread.

These are **in-app only**, and that is a real limitation rather than an
oversight: the ORCID `/authenticate` scope returns an iD and a name and no email
address, and ORCID addresses are usually private, so there is nowhere to send a
message. A reviewer learns of a response when they next visit. Reaching people
who do not return would mean collecting an email address separately, with the
privacy obligations that brings.

## No directory

The homepage explains how the system works; it does not list papers. Nobody
browses a repository looking for something to review, and a directory would
imply a model that does not work. Each paper has its own URL and travels by an
author asking specific people to look, which is the only invitation that
reliably gets answered.

## The author's page

Clicking your name opens your own papers, matched by ORCID rather than by who
added them. It is the only place a paper is added, and its sections follow the
life of one: **your other preprints**, which you can add for review, then
**under review**, then **past reviews**.
Past entries link to the final version on the preprint server and, once round
deposits exist, to the citable review record.

The counts are limited to what the server can actually know. There is
deliberately no resolved/unresolved verdict anywhere in this system: what
traditional peer review surfaces is a criticism and the author's response, and
readers judge for themselves. Each thread therefore shows whether an author has
answered it, and nothing more is claimed.

The one thing this record does that a journal's cannot is verify the response.
A response-to-reviewers letter says "we have revised the text accordingly" and
no reader can check. Because anchoring already knows whether a quoted passage
still exists in the current version, a thread written against an earlier version
is labelled "passage revised in v2" or "passage unchanged in v2" next to the
author's claim. That costs nothing extra, since the client computes it anyway.

The author's page reports three facts:

| Metric | Meaning |
|---|---|
| comments | how much scrutiny the paper has drawn |
| awaiting your response | top-level comments no author has replied to |
| on an earlier version | comments written before the current revision, so a revision may already have dealt with them |

The last is a hint, not a claim. A real resolved/unresolved state needs the
comment typing and state vector in TODO.md, and the client reporting whether an
anchor still resolves.

## The record a round produces

A closed window leaves an artifact rather than a greyed-out status bar. Any
paper offers its review record at `/api/documents/{id}/record`, as JSON or as
Markdown with `?format=md`, and the closed-round bar and the author's page both
link to it.

The record is self-contained: the paper and the version reviewed, the window and
how much scrutiny it drew, and every thread with its criticism, the author's
answer and what happened to the quoted text. It carries no internal identifiers
and no identities, uses the same words a reader sees rather than status codes,
and states plainly that no resolution verdict is asserted. Withdrawn comments
are absent rather than tombstoned: a live page should show that something was
removed, an archive should not preserve what was withdrawn.

It is public, needing no account, because the record is the point of the
exercise. Depositing it somewhere permanent with a DOI is the next step and is
currently a manual one: download the Markdown, deposit it, and put the DOI in
`documents.review_doi`. Automating that is in TODO.md, deliberately after the
first round rather than before it.

## Page opens

Each paper carries a count of how many times it has been opened, excluding its
own authors, visible only to those authors. It answers "is anyone arriving",
which is a question about distribution rather than about quality: if you send a
link to five colleagues and the page is opened twice, the problem is the ask.

It is deliberately not public and deliberately not a metric. A view count
measures promotion rather than scrutiny, and displayed on a paper it would
become an authoritative-looking number answering a question nobody asked.

It is also not analytics. There is no third-party service, no cookie set for it,
nothing recorded about the visitor and no per-person reading history. A record of
who reads what, tied to a verified ORCID iD, would be more revealing than a
record of what someone chose to say, and would deter exactly the cautious
reviewer this depends on.

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

## Signing in

ORCID is the only way in, and deliberately the only way: a form that accepted an
ORCID iD without verifying it would let anyone comment as any researcher,
including as a paper's own author, so no such path exists even behind a flag.

Reading is public. Signing in is required only to comment, vote or add a paper,
and is prompted at the point of action rather than at the door.

To run your own instance you need a free ORCID public API client:

1. Sign in at orcid.org, click your name, then **Developer tools**
   (https://orcid.org/developer-tools). You may need to verify your email first.
2. Register a **public API client**. The redirect URI must exactly match
   `ORCID_REDIRECT_URI`, e.g. `https://your-domain/auth/orcid/callback`.
3. Put the client ID and secret in `backend/.env` and restart.

`ORCID_ENV=sandbox` targets sandbox.orcid.org, whose accounts require
mailinator.com addresses. Tests never touch any of this: they authenticate by
overriding the current-user dependency, so the application has no test login
path either.

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
so without a mounted volume every deploy discards the reviews. Budget by paper
rather than by user: measured preprints are 2 to 3 MB, and 20 MB is a safe
pessimistic figure for image-heavy work, so a gigabyte holds somewhere between
50 and 500 papers. Comments are negligible by comparison, a few hundred bytes
each. Past a few thousand papers, move the PDFs to object storage (Cloudflare R2
charges no egress, which matters when the files are served on every page view)
and leave SQLite holding only text.

```bash
fly auth login
fly launch --no-deploy --name <app-name>          # fly.toml is already written
fly volumes create review_data --size 3 --region lhr   # PDFs are 2-20 MB each
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

## Privacy

A notice lives at `/privacy` (source in `frontend/src/pages/PrivacyPage.jsx`),
linked from the site footer. It is deliberately specific rather than boilerplate,
because the most important thing it says is the limit of the pseudonymity
promise: comments are pseudonymous to readers, but the operator holds the link
between an ORCID iD and its comments, and could be compelled to disclose it. A
reviewer deciding how candid to be is entitled to know that before they write.

The subject of a comment here is a piece of work, not a person, which is the
whole point of the conduct standard. The reason a professional read is still
worth having is the narrow case where the two blur: an allegation about how
results were produced is about conduct rather than about the paper, and that is
the boundary moderation exists to police.

It also records that no email address is held (ORCID is not asked for one),
that there is no analytics or third-party tracking of any kind, that ORCID and
OpenAlex receive a user's ORCID iD during badge computation, and that a
deposited review record is permanent and cannot later be withdrawn.

## Rate limits

Five comments a minute per person, which is the balance the design is aiming at:
enough to flag several typos while reading a paper, not enough to bury a page.
Adding a paper is capped at ten an hour, since each one fetches a PDF and
queries OpenAlex, and reporting at ten an hour, because nobody legitimately
reports a dozen comments in an hour and report spam is the cheapest way to bury
criticism. Voting is not limited: it is cheap, and reading a long thread means
many votes.

Limits are keyed on the signed-in user rather than the IP address, since every
write requires an ORCID account. They are held in memory, so they reset on
deploy and would not be shared between machines; that is fine for a single
instance and is the first thing to revisit if it ever becomes more than one.

## Backups

Reviews are the only irreplaceable thing here. The papers can be re-fetched from
the preprint servers, but the commentary exists nowhere else.

```bash
./scripts/backup.sh                     # -> backups/review-backup-<timestamp>.tar.gz
./scripts/restore.sh <archive> [target] # refuses to overwrite unless FORCE=1
```

The database is copied with `sqlite3 .backup` rather than `cp`, because it runs
in WAL mode and a plain file copy can capture a database whose committed data is
still in a separate write-ahead log. Every backup is integrity-checked before it
is written, and again before a restore.

On a deployed instance, run the script over SSH and pull the archive down:

```bash
fly ssh console -C "/app/scripts/backup.sh /data/backups"
fly ssh sftp get /data/backups/review-backup-<timestamp>.tar.gz
```

Fly takes daily volume snapshots with five days of retention, restorable with
`fly volumes create --snapshot-id`, but their own documentation is clear that
snapshots alone are not a backup strategy: a host failure loses everything since
the last one. Keep copies off the host.

## Tests

```bash
cd backend && .venv/bin/python -m pytest tests -q
```

`tests/test_lint.py` runs pyflakes over the package and fails on undefined names
and stray unused imports. That is there because editing has three times silently
removed a function other code still called, and the suite did not notice: the
calling paths needed the network and were stubbed out. A name that does not
exist is worth catching without running anything.

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

## Zoom

The PDF column zooms independently of the rest of the page, so figures can be
examined without the header, review bar or comment sidebar moving. Controls sit
top-right of the column, and Ctrl or Cmd with the scroll wheel works as usual.

Zooming re-renders each page at the new scale rather than applying a CSS
transform. A transform would upscale the canvas bitmap and blur exactly the
figures someone is trying to inspect, and it would leave the text layer at the
wrong size. Highlights are recomputed from the re-rendered text layer, so they
track the zoom to within a fraction of a pixel.

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
