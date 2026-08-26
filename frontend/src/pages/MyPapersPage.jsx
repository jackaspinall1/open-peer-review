import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { get } from '../api'
import { useMe } from '../auth'
import RoundStatus from '../components/RoundStatus'

function Metrics({ p }) {
  return (
    <div className="metrics">
      <span><strong>{p.comments}</strong> comment{p.comments === 1 ? '' : 's'}</span>
      {p.awaiting_response > 0 && (
        <span className="awaiting" title="Top-level comments no author has replied to">
          <strong>{p.awaiting_response}</strong> awaiting your response
        </span>
      )}
      {p.superseded > 0 && (
        <span className="muted" title="Written against an earlier version, so a revision may already have dealt with them">
          {p.superseded} on an earlier version
        </span>
      )}
    </div>
  )
}

function PaperRow({ p, past }) {
  return (
    <li className="doccard">
      <Link to={`/doc/${p.id}`} className="doctitle">{p.title}</Link>
      <div className="docmeta">
        <span>v{p.version}</span>
        {p.round ? <RoundStatus round={p.round} /> : <span className="muted">No review window open yet</span>}
        {p.source_url && (
          <a className="sourcelink" href={p.source_url} target="_blank" rel="noreferrer">
            {past ? 'Final version' : 'Original'} on {p.source_name || 'the preprint server'} ↗
          </a>
        )}
        {past && (
          p.review_doi ? (
            <a className="sourcelink" href={`https://doi.org/${p.review_doi}`} target="_blank" rel="noreferrer">
              Review record ↗
            </a>
          ) : (
            <span className="muted" title="Depositing completed rounds as citable records is not built yet">
              Review record not yet deposited
            </span>
          )
        )}
      </div>
      <Metrics p={p} />
    </li>
  )
}

export default function MyPapersPage() {
  const { me } = useMe()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!me?.logged_in) return
    get('/api/documents/mine').then(setData).catch((e) => setError(e.message))
  }, [me?.logged_in])

  if (me && !me.logged_in) {
    return <main className="page"><p className="muted">Sign in to see your papers.</p></main>
  }
  if (error) return <main className="page"><p className="error">{error}</p></main>
  if (!data) return <main className="page"><p>Loading…</p></main>

  return (
    <main className="page">
      <h1>Your papers</h1>
      <p className="muted" title={me?.orcid}>Papers you are listed on, matched by ORCID iD.</p>

      <h2 className="sectionhead">Under review</h2>
      {data.under_review.length === 0 ? (
        <p className="muted">
          Nothing under review. <Link to="/upload">Add one of your preprints</Link> to open a window.
        </p>
      ) : (
        <ul className="doclist">
          {data.under_review.map((p) => <PaperRow key={p.id} p={p} />)}
        </ul>
      )}

      <h2 className="sectionhead">Past reviews</h2>
      {data.past.length === 0 ? (
        <p className="muted">No completed review rounds yet.</p>
      ) : (
        <ul className="doclist">
          {data.past.map((p) => <PaperRow key={p.id} p={p} past />)}
        </ul>
      )}
    </main>
  )
}
