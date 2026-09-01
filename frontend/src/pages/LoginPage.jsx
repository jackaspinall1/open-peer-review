import { useLocation } from 'react-router-dom'
import { useMe } from '../auth'

/**
 * ORCID is the only way in. There is deliberately no alternative: a form that
 * accepted an ORCID iD without verifying it would let anyone comment as any
 * researcher, including as a paper's own author.
 */
export default function LoginPage() {
  const { me } = useMe()
  const location = useLocation()
  const from = location.state?.from || '/'

  if (!me) return <main className="page narrow"><p>Loading…</p></main>

  return (
    <main className="page narrow">
      <h1>Sign in</h1>
      <p className="muted">
        Reviewers sign in with their ORCID iD. Your identity is used only to verify your
        relationship to a paper's authors — your comments appear under a per-paper pseudonym.
      </p>

      {me.orcid_ready ? (
        <a className="primary orcidbtn" href={`/auth/orcid/login?next=${encodeURIComponent(from)}`}>
          Sign in with ORCID
        </a>
      ) : (
        <div className="card">
          <p className="muted">
            ORCID sign-in is not configured on this server. Register a free public API client at{' '}
            <a href="https://orcid.org/developer-tools" target="_blank" rel="noreferrer">
              orcid.org/developer-tools
            </a>{' '}
            and set ORCID_CLIENT_ID and ORCID_CLIENT_SECRET.
          </p>
        </div>
      )}
    </main>
  )
}
