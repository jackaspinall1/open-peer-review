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

- [ ] Expertise badge: same OpenAlex lookup → "publishes in this field" for
      pseudonymous reviewers (topic overlap between reviewer's works and paper)
- [ ] Weight/flag by publication record (fresh zero-work ORCIDs are cheap to
      create; a "no publication record" badge is the honest Sybil defence)
- [ ] COI recency policy: colour active vs. historical co-authorship
      (funder convention: within 48 months; year already captured)
- [ ] DOI → Crossref/OpenAlex metadata autofill on upload (closes the
      "uploader omits an author to hide a COI" hole; kills typing friction)

## Review mechanics

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
