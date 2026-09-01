import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { get, postJSON } from '../api'
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
        {p.round ? <RoundStatus round={p.round} documentId={p.id} /> : <span className="muted">No review window open yet</span>}
        {p.source_url && (
          <a className="sourcelink" href={p.source_url} target="_blank" rel="noreferrer">
            {past ? 'Final version' : 'Original'} on {p.source_name || 'the preprint server'} ↗
          </a>
        )}
        {past && (
          <a className="sourcelink" href={`/api/documents/${p.id}/record?format=md`}>
            Download the review record ↓
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
  const { me, refreshUnread } = useMe()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [notes, setNotes] = useState(null)
  const [works, setWorks] = useState(null)
  const [worksError, setWorksError] = useState(null)
  const [importing, setImporting] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!me?.orcid) return
    get('/api/documents/mine').then(setData).catch((e) => setError(e.message))
    get('/api/documents/my-works')
      .then((r) => setWorks(r.works))
      .catch((e) => setWorksError(e.message))
    get('/api/notifications')
      .then((r) => {
        setNotes(r.notifications)
        // seen once the list is open; the badge should not nag afterwards
        if (r.unread > 0) postJSON('/api/notifications/read', {}).then(refreshUnread)
      })
      .catch(() => setNotes([]))
  }, [me?.orcid, refreshUnread])

  if (me && !me.logged_in) {
    return <main className="page"><p className="muted">Sign in to see your papers.</p></main>
  }
  if (error) return <main className="page"><p className="error">{error}</p></main>
  if (!data) return <main className="page"><p>Loading…</p></main>

  return (
    <main className="page">
      <h1>Your papers</h1>
      <p className="muted" title={me?.orcid}>Papers you are listed on, matched by ORCID iD.</p>

      {notes?.length > 0 && (
        <>
          <h2 className="sectionhead">Replies to your comments</h2>
          <ul className="doclist">
            {notes.map((n) => (
              <li key={n.id} className={n.read ? 'doccard' : 'doccard unread'}>
                <Link to={`/doc/${n.document_id}#comment-${n.comment_id}`} className="doctitle">
                  {n.document_title}
                </Link>
                <blockquote className="quote">{n.your_comment}</blockquote>
                <div className="metrics">
                  <span><strong>{n.reply_alias}</strong>{n.by_author ? ' (author)' : ''} replied:</span>
                </div>
                <p className="commentbody">{n.reply}</p>
              </li>
            ))}
          </ul>
        </>
      )}

      <h2 className="sectionhead">Under review</h2>
      {data.under_review.length === 0 ? (
        <p className="muted">
          Nothing under review yet. Add one of your preprints above, then open a review window on it.
        </p>
      ) : (
        <ul className="doclist">
          {data.under_review.map((p) => <PaperRow key={p.id} p={p} />)}
        </ul>
      )}

      <h2 className="sectionhead">Your other preprints</h2>
      {worksError && <p className="error">{worksError}</p>}
      {works === null && !worksError && <p className="muted">Looking up your preprints…</p>}
      {works && works.filter((w) => !w.document_id).length > 0 && (
        <p className="formnote warranty">
          By adding a paper you confirm you have the right to post it here on behalf of its
          co-authors. Any listed author can contact us about a paper posted without their
          agreement.
        </p>
      )}
      {works?.filter((w) => !w.document_id).length === 0 && (
        <p className="muted">
          Every preprint under your ORCID iD is already here. New ones take a few days to be
          indexed after posting.
        </p>
      )}
      {works && works.filter((w) => !w.document_id).length > 0 && (
        <ul className="worklist card">
          {works.filter((w) => !w.document_id).map((w) => (
            <li key={w.openalex_id}>
              <div>
                <span className="worktitle">{w.title}</span>
                <span className="workmeta">
                  {[w.year, w.source].filter(Boolean).join(' · ')}
                  {!w.likely_fetchable && ' · publisher may block automatic download'}
                </span>
              </div>
              <button className="primary small" disabled={!!importing} onClick={async () => {
                setImporting(w.openalex_id)
                try {
                  const { id } = await postJSON('/api/documents/import', { openalex_id: w.openalex_id })
                  navigate(`/doc/${id}`)
                } catch (e) {
                  setWorksError(e.message)
                  setImporting(null)
                }
              }}>
                {importing === w.openalex_id ? 'Adding…' : 'Add for review'}
              </button>
            </li>
          ))}
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
