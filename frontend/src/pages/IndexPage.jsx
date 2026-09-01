import { Link } from 'react-router-dom'
import { useMe } from '../auth'

/**
 * The homepage explains the system rather than listing papers.
 *
 * There is deliberately no directory: nobody browses a repository looking for
 * something to review, and a list of every paper would imply a model that does
 * not work. Papers have their own URL and travel by an author asking specific
 * people to look, which is the only invitation that reliably gets answered.
 */
export default function IndexPage() {
  const { me } = useMe()

  return (
    <main className="page narrow prose">
      <h1>Open peer review of preprints</h1>
      <p className="lede">
        An author posts a preprint, opens it for review here, and asks colleagues to look.
        Reviewers highlight a sentence and say what is wrong with it. The exchange is public and
        permanent, and it produces a record anyone can cite.
      </p>

      <h2>How it works</h2>
      <ol>
        <li>
          You add one of your own preprints, matched to your ORCID iD. The PDF and the author list
          come from the preprint server, so there is nothing to type.
        </li>
        <li>
          You open a two-week review window and send the paper's link to people whose opinion you
          want. A direct request from an author is the only invitation that reliably gets answered.
        </li>
        <li>
          Reviewers select a sentence and comment on it. Comments are threaded, can be voted on,
          and stay attached to the text they refer to.
        </li>
        <li>
          You answer them, revise the preprint, and pull the new version through. Comments
          re-anchor: criticism whose passage you rewrote is marked as such, so the record shows
          what actually changed rather than only what you said you changed.
        </li>
        <li>
          When the window closes, the round produces a review record: the criticism, your answers,
          and what happened to the text.
        </li>
      </ol>

      <h2>Reviewers are pseudonymous, and not anonymous to us</h2>
      <p>
        Comments appear as “Reviewer 2”, or “Author” for someone on the paper. Your pseudonym on
        one paper cannot be linked to your pseudonym on another, so a postdoc can be blunt about a
        professor's work. But we hold the link between your ORCID iD and your comments, and could
        be compelled to disclose it. If that is not enough protection for what you want to say,
        do not say it here. The <Link to="/privacy">privacy notice</Link> is specific about this.
      </p>

      <h2>Every comment shows its author's relationship to the paper</h2>
      <p>
        Alongside each comment sits what we can work out from public records: whether the commenter
        has co-authored with one of the paper's authors, shares an institution with them, and
        whether they publish on the topic. That is what lets an author recruit their own reviewers
        without it being a conflict of interest hidden from readers, which is normally the problem
        with author-chosen review.
      </p>

      <h2>No verdicts</h2>
      <p>
        Nothing here decides whether a paper is good. There is no score, no accept or reject, and
        no resolution flag. What the record shows is a criticism, whether an author answered it,
        and whether the text changed. Readers judge, as they do with any review.
      </p>

      <p className="muted">
        Non-commercial and open source under AGPL-3.0. Papers stay on their preprint server; this
        holds the discussion of them.
      </p>

      {me?.logged_in ? (
        <p><Link className="primary" to="/me">Add one of your preprints</Link></p>
      ) : (
        <p><Link className="primary" to="/login">Sign in with ORCID</Link></p>
      )}
    </main>
  )
}
