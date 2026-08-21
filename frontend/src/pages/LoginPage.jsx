import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { postJSON } from '../api'
import { useMe } from '../auth'

export default function LoginPage() {
  const { me, refresh } = useMe()
  const navigate = useNavigate()
  const location = useLocation()
  const [orcid, setOrcid] = useState('')
  const [error, setError] = useState(null)
  const from = location.state?.from || '/'

  const mockLogin = async (e) => {
    e.preventDefault()
    setError(null)
    try {
      await postJSON('/auth/mock/login', { orcid })
      await refresh()
      navigate(from)
    } catch (err) {
      setError(err.message)
    }
  }

  if (!me) return <main className="page narrow"><p>Loading…</p></main>

  return (
    <main className="page narrow">
      <h1>Sign in</h1>
      <p className="muted">
        Reviewers sign in with their ORCID iD. Your identity is used only to verify your
        relationship to a paper's authors — your comments appear under a per-paper pseudonym.
      </p>

      {me.orcid_enabled && (
        me.orcid_ready ? (
          <a className="primary orcidbtn" href={`/auth/orcid/login?next=${encodeURIComponent(from)}`}>
            Sign in with ORCID
          </a>
        ) : (
          <div className="card">
            <p className="muted">
              ORCID sign-in is enabled but not configured yet: register a free public API client
              at <a href="https://orcid.org/developer-tools" target="_blank" rel="noreferrer">orcid.org/developer-tools</a> and
              put the client ID and secret in <code>backend/.env</code>.
            </p>
          </div>
        )
      )}

      {me.mock_enabled && (
        <form onSubmit={mockLogin} className="card form" style={me.orcid_enabled ? { marginTop: 16 } : undefined}>
          <div className="formnote">Development mode: enter any well-formed ORCID iD.</div>
          <label>ORCID iD
            <input value={orcid} onChange={(e) => setOrcid(e.target.value)} placeholder="0000-0002-1825-0097" required />
          </label>
          {error && <p className="error">{error}</p>}
          <button type="submit" className="primary">Sign in (dev)</button>
        </form>
      )}
    </main>
  )
}
