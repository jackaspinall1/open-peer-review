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

## Launch path

- [ ] Republish repo (scheduled: evening commit + flip public)
- [ ] Deploy a hosted instance (Fly.io/Render, SQLite on a volume); add the
      deployed callback URI to the ORCID client (fields are editable)
- [ ] OG meta tags so shared paper links unfurl on X/Bluesky/Slack with
      title/authors/comment count — the link is the ad
- [ ] Decide upload policy deliberately: author-initiated only (uploader's
      ORCID must be on the author list) vs. anyone (PubPeer-style critic
      convening) — one `if`, big cultural consequence

## Trust & identity

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
- [ ] COI recency policy: colour active vs. historical co-authorship
      (funder convention: within 48 months; year already captured)
- [x] Upload autofill: client extracts title (largest-font heuristic) + DOI
      (regex) from the PDF; OpenAlex supplies the verified record — canonical
      title, full author list, ORCIDs from the paper's own authorships (never
      name-guessing), affiliations. Editable, with provenance note. Closes the
      "uploader omits an author to hide a COI" hole and kills typing friction

## Review mechanics

- [x] Authors comment under an "Author" label (ORCID-verified via the COI
      check), not "Reviewer N" — the page is the whole venue: critique,
      verified author response, revision, resolution, all on one public URL

- [ ] Moderation basics: delete-own (soft delete preserving threads), report,
      admin remove — the editor's unglamorous jobs come due at any real scale
- [ ] Side-by-side version view: show what a "written on v1, unresolved in v2"
      comment pointed at
- [ ] Editorial summary state per paper: "N expert reviews, M unresolved major
      issues" as the certification-replacement metric
- [ ] HTML document support (second document type alongside PDF)

## Someday

- [ ] Funding-overlap COI signal (ORCID/OpenAlex grants)
- [ ] Fuzzy anchor fallback is deliberately NOT planned: a reworded statement
      surfacing as unresolved is the system working (authors adapted)
