import { Link } from 'react-router-dom'
import { useMe } from '../auth'

/**
 * The homepage states what this is and how a round runs, in five steps.
 *
 * There is deliberately no list of papers: nobody browses a repository looking
 * for something to review. Each paper has its own URL and travels by an author
 * asking specific people to look.
 */
export default function IndexPage() {
  const { me } = useMe()

  return (
    <main className="page narrow prose">
      <h1 className="mission">Open, fast, permanent peer review.</h1>

      <ol className="steps">
        <li>Log in with ORCID.</li>
        <li>Add any preprint for review, from the preprint servers, and share it.</li>
        <li>
          Reviewers comment, either on specific highlighted text or on the paper as a whole. Their
          relationship to the authors and their expertise are calculated from their ORCID. All
          reviews are pseudonymous.
        </li>
        <li>Review concludes after 14 days, with the option for authors to extend.</li>
        <li>
          The review is deposited on Zenodo.{' '}
          <span className="pending-feature">[This feature is currently disabled during development.]</span>
        </li>
      </ol>

      {me?.logged_in ? (
        <p><Link className="primary" to="/me">Add one of your preprints</Link></p>
      ) : (
        <p><Link className="primary" to="/login">Sign in with ORCID</Link></p>
      )}
    </main>
  )
}
