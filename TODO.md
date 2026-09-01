# TODO / roadmap

Working principle: launch and iterate — these are discovered priorities, not a-priori design.

## Reviews as archival artifacts (Zenodo)

The durable output of a review round is a citable artifact, not rows in this
app's database. When a review round stabilises (or on demand), export the
review record — paper metadata + version history, all threads with quotes and
anchors, pseudonyms, COI badges, vote tallies, resolution states
(addressed / unresolved in v2) — as PDF+JSON and deposit it on Zenodo:

- DataCite relation `Reviews` → the paper's DOI, so indexers (incl. OpenAlex)
  can surface "this preprint has a public review record" automatically
- Zenodo concept DOI + version DOIs map onto our document versions
  ("review of v1" and "review of v2" are distinct citable objects)
- Pseudonyms preserved in the artifact; reviewer credit flows through ORCID's
  native peer-review section ("performed review for …", Publons-style, no link
  to specific comments); optional signing at deposit time
- Makes the platform a thin, replaceable process layer: arXiv holds the paper,
  this tool runs the process, Zenodo archives the outcome — reviews outlive
  the site
- Build notes: Zenodo REST API (free token), sandbox.zenodo.org to develop
  against, a community collection as the umbrella; store the returned DOI on
  the document

## Preprint workflow (the core loop)

Post preprint to arXiv/bioRxiv/ChemRxiv → open review here → post the revised
version back to the preprint server → "Check for new version" pulls it through,
bumps the document version, and re-anchors older comments (moved text
re-attaches; revised text surfaces as unresolved).

- [x] Import from ORCID: signed-in authors pick from their own indexed
      preprints; PDF + author record + ORCIDs + affiliations + topics fetched
      automatically. Author-initiated by construction (you can only import
      papers your ORCID is on)
- [x] Preprint servers only (arXiv, bioRxiv, medRxiv, ChemRxiv, Research
      Square, OSF, SSRN…); publisher copies are excluded — they 403 automated
      fetches anyway
- [x] Version tracking: stored PDF hash vs the preprint server's current file
- [ ] Poll for new versions automatically rather than on demand (arXiv serves
      the latest at a stable URL, so this is a cron over documents with a
      source URL)
- [ ] Push the review record back the other way: DOI/link to the review page in
      the preprint's comments field where the server supports it

## Legal entity and jurisdiction

Needs a decision before any public launch. A memo is planned; this is the raw
material for it.

**The problem.** Reviewers are pseudonymous, so a claimant cannot identify them
and the complaint lands on whoever hosts the statement. That is the PubPeer
pattern: the litigation went to the platform, not to the commenters. Today the
host is one person, with no entity in between.

**Why the answer cannot be to avoid the category.** The critique with the most
value is the most exposed: duplicated panels, impossible statistics, data that
could not have come from the described experiment. A review system that cannot
host that is reduced to typo-spotting, which is worth something and is not the
thing that changes the literature.

**What reduces the exposure**

- An entity rather than a person. A letter to an organisation is a process; a
  letter to an individual is their evening.
- US domicile, for three specific mechanisms: Section 230 immunity for
  user-posted content, with no UK or EU equivalent; state anti-SLAPP statutes
  allowing early dismissal with costs, which addresses the real risk here of
  nuisance and expense rather than losing; and the SPEECH Act, which makes
  foreign defamation judgments largely unenforceable in the US. Caveat:
  jurisdiction is not purely elective. UK courts can take a case over material
  read in the UK, and a UK-resident operator stays reachable wherever the entity
  sits, so this protects the organisation rather than the individual.
- Media liability insurance, which exists and is inexpensive at this scale.
- A disclosure policy decided and published in advance. This is a trust feature
  as much as a shield: reviewers will not write the valuable thing if they
  suspect a name gets handed over at the first angry email.
- A conduct norm of observation over conclusion. "Panels 2a and 2c appear
  identical" is a checkable claim about a document; "the authors fabricated
  this" is a claim about people. The defensible form and the rigorous form are
  the same sentence, which is why PubPeer's culture converged on it. One line
  to add to the existing standard.

**Constraints that interact**

- Non-commercial is already committed, and many preprints are CC BY-NC-ND (four
  of seven in one real sample), which a commercial operator cannot host. The
  entity should be a nonprofit or equivalent.
- AGPL means any hosted fork must publish its source. Fine, but the operator
  should accept it knowingly rather than discover it.
- Data currently sits in London. A US host means UK and EU personal data
  transfers: workable, more paperwork.

**Options**, ascending in effort: fiscal sponsorship by an existing US nonprofit,
which gives a legal entity without incorporating anything; handing it to a US
organisation whose mission already covers this; incorporating a US nonprofit;
or a UK entity accepting the greater exposure.

**Not urgent for the pilot.** Five invited colleagues on your own preprint is not
the scenario that produces letters.

## Launch path

- [x] Rate limits: 5 comments/minute per user, 10 papers/hour, 10 reports/hour
- [ ] Schedule the backup script (a script nobody runs is not a backup)
- [x] Privacy notice at /privacy, linked from a site footer
- [ ] Fill in the contact address (CONTACT@EXAMPLE.COM placeholder in
      frontend/src/pages/PrivacyPage.jsx)
- [ ] Have the privacy notice read by someone legally qualified before a public
      launch. It is honest and specific but written by the builders. The subject
      of a comment is the work, not the person; the case worth a professional
      opinion is the narrow one where those blur, i.e. an allegation about how
      results were produced
- [ ] Terms of use (separate from privacy): what conduct is expected, what
      happens to your content, no warranty
- [ ] Monitoring: nobody currently finds out if it falls over or if the
      background badge checks start failing

- [x] Backup and restore scripts, integrity-checked, WAL-safe
- [x] Works on a phone: the paper fits the screen and comments stack beneath
      (previously the fixed 400px sidebar left the PDF about 30px wide)

- [x] Republish repo publicly (AGPL)
- [x] Real SECRET_KEY; no hardcoded default (a known key in a public repo lets
      anyone forge a session for any ORCID iD)
- [x] Production packaging: single container, FastAPI serves the built
      frontend, Dockerfile + fly.toml written and the single-process mode
      verified locally
- [ ] Actually deploy it (needs a Fly account, a GoDaddy DNS record, and the
      new callback URI on the ORCID client)
- [ ] OG meta tags so shared paper links unfurl on X/Bluesky/Slack with
      title/authors/comment count — the link is the ad
- [ ] Decide upload policy deliberately: author-initiated only (uploader's
      ORCID must be on the author list) vs. anyone (PubPeer-style critic
      convening) — one `if`, big cultural consequence

## Before a public deployment

- [x] Moderation basics: soft-delete own comment, report (queues for a human,
      hides nothing), moderator removal via ADMIN_ORCIDS, one-line conduct
      standard. No pre-publication gate and no tone filtering, by design
- [x] Automated anonymity tests (backend/tests); 9 tests, offline
- [x] Record and display the preprint's licence + link to the original; add a
      depositor warranty at import. Author-initiated import means the depositor
      is a rights holder, so no licence restriction is needed — but NC licences
      do rule out a commercial pivot later
- [ ] One-page privacy note (ORCID iDs and names of EU researchers are stored)

## Trust & identity

- [x] Cache each reviewer's scholarly profile (co-authors, shared large works,
      topics) so conflict and expertise checks are local intersections. Two
      OpenAlex requests per reviewer ever, rather than ~15 per reviewer per
      paper; the free tier is 1,000 metered credits, so the old pattern would
      have run out during a pilot
- [ ] Consider self-hosting the OpenAlex snapshot if volume ever justifies it;
      paid credits are $0.0001/call, so 100k calls is $10

- [x] Show a reader the badges their comment would carry, before they write it.
      Alias numbers are now assigned on first comment rather than first view,
      so silent viewers neither consume numbers nor reveal their presence
      through gaps in the sequence

- [x] One live discussion per paper: dedupe on OpenAlex work id, then
      version-stripped DOI. Paper control belongs to any listed author by
      ORCID, not just the depositor (otherwise a non-author can squat a paper)
- [ ] Soft duplicate warning for manual uploads with no DOI (title match);
      warn rather than block, since it cannot be decided reliably

- [x] Expertise badge: topic/subfield/field-tiered match between reviewer's
      OpenAlex topic profile and the paper's topics (DOI lookup or /text/topics
      title classification); bucketed counts + years-active only — career
      titles and institutions deliberately NOT displayed (reimports hierarchy,
      shrinks the anonymity set)
- [x] De-fingerprint every badge: no counts, no institution names, no author
      names, no seniority proxies. Driven by measurement, not taste — a
      "20+ shared works" badge has an anonymity set of ONE against OpenAlex.
      Relationship + one bit of recency only
- [ ] Revisit if/when a badge needs more granularity: check the anonymity set
      against OpenAlex first (see README), never add magnitudes by default
- [x] "No publication record" badge for zero-work ORCIDs (the honest Sybil
      defence); algorithmic vote-weighting by expertise deliberately deferred —
      display, don't weight, until real behaviour is observed
- [x] COI recency: one bit, recent (4y) vs not, per funder convention
- [x] Discount hyperauthorship: works with >15 authors (roadmaps, consortium
      papers) are not co-authorship — one 50-author roadmap was supplying half
      a researcher's co-author graph. Count-sensitive too: one shared roadmap
      reads as no relationship, 3+ distinct ones earn the weak badge
- [ ] Revisit the 15-author threshold if a field routinely publishes larger
      genuine collaborations (particle physics, large clinical trials)
- [x] Upload autofill: client extracts title (largest-font heuristic) + DOI
      (regex) from the PDF; OpenAlex supplies the verified record — canonical
      title, full author list, ORCIDs from the paper's own authorships (never
      name-guessing), affiliations. Editable, with provenance note. Closes the
      "uploader omits an author to hide a COI" hole and kills typing friction

## Review mechanics

- [x] Author page lists the preprints not yet added, with an Add button, so
      papers can be added from the one place that already shows your work

- [x] Notify a reviewer in-app when their comment is replied to (count beside
      the name, list on their own page)
- [ ] Email notification would reach reviewers who do not return, but needs an
      optional address collected at sign-in: ORCID gives us none

- [x] Author page (/me): papers matched by ORCID, under review vs past, window
      timeline, comment counts and how many await an author reply
- [x] Thread state: "Awaiting author response" / "Answered by an author", plus
      "passage revised/unchanged in vN" from the anchoring once a revision
      exists. Deliberately NO resolved/unresolved verdict: that is all
      traditional review surfaces, and it removes the satisfaction step, the
      notification email it depended on (ORCID gives us no address), and the
      need for comment typing
- [x] A round produces a downloadable record (JSON and Markdown), linked from
      the closed-round bar and the author page
- [ ] Deposit that record to Zenodo automatically and store the DOI in
      documents.review_doi. Deliberately manual for the first rounds: doing it
      by hand will show what the artifact should actually contain

- [x] Zoom inside the PDF column only (re-render, not CSS transform, so figures
      stay sharp); fixed a latent bug where text-layer spans never scaled,
      which made selection rectangles ~29% too wide even at 100%

- [x] Review rounds: 2-week window per version, extendable weekly to a month,
      author-opened, public countdown, late comments accepted but marked and
      excluded from the record, participation shown so thin rounds look thin
- [ ] Version bump should not silently start a new round (currently a source
      refresh bumps the version; opening a round stays a separate, explicit act
      — confirm that reads correctly once a real revision happens)
- [ ] Notify topic-matched reviewers when a round opens (the solicitation step;
      needs the personalised queue below)

- [x] Authors comment under an "Author" label (ORCID-verified via the COI
      check), not "Reviewer N" — the page is the whole venue: critique,
      verified author response, revision, resolution, all on one public URL

- [ ] Side-by-side version view: show what a "written on v1, unresolved in v2"
      comment pointed at
- [ ] Editorial summary state per paper: "N expert reviews, M unresolved major
      issues" as the certification-replacement metric
- [ ] HTML document support (second document type alongside PDF)

## Someday

- [ ] Funding-overlap COI signal (ORCID/OpenAlex grants)
- [ ] Fuzzy anchor fallback is deliberately NOT planned: a reworded statement
      surfacing as unresolved is the system working (authors adapted)
