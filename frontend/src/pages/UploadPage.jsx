import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { get, postJSON } from '../api'
import { useMe } from '../auth'

/**
 * Adding a paper means importing one of your own preprints.
 *
 * There is deliberately no manual upload path. Every paper on the platform is
 * therefore one its author chose to submit for public review, which is both the
 * intended culture and the basis of the position that criticism here was
 * invited rather than convened on someone uninvited.
 */
export default function AddPaperPage() {
  const { me } = useMe()
  const navigate = useNavigate()
  const [works, setWorks] = useState(null)
  const [importing, setImporting] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!me?.orcid) return
    get('/api/documents/my-works').then((r) => setWorks(r.works)).catch(() => setWorks([]))
  }, [me?.orcid])

  if (me && !me.logged_in) {
    return (
      <main className="page narrow">
        <h1>Add a paper</h1>
        <p className="muted">You need to <Link to="/login">sign in with ORCID</Link> to add a paper.</p>
      </main>
    )
  }

  const importWork = async (w) => {
    setError(null)
    setImporting(w.openalex_id)
    try {
      const { id } = await postJSON('/api/documents/import', { openalex_id: w.openalex_id })
      navigate(`/doc/${id}`)
    } catch (err) {
      setError(err.message)
      setImporting(null)
    }
  }

  return (
    <main className="page narrow">
      <h1>Add a paper</h1>
      <p className="muted">
        You can add your own preprints, matched to your ORCID iD. Papers here are always submitted
        for review by one of their authors.
      </p>

      {works === null && <p className="muted">Looking up your preprints…</p>}

      {works?.length > 0 && (
        <section className="card">
          <p className="formnote">
            Adding one fetches the PDF and the author record automatically. When you post a revised
            version to the preprint server, use “Check for new version” on the paper to pull it
            through.
          </p>
          <p className="formnote warranty">
            By adding a paper you confirm you have the right to post it here on behalf of its
            co-authors. Any listed author can ask for it to be removed.
          </p>
          {error && <p className="error">{error}</p>}
          <ul className="worklist">
            {works.map((w) => (
              <li key={w.openalex_id}>
                <div>
                  <span className="worktitle">{w.title}</span>
                  <span className="workmeta">
                    {[w.year, w.source].filter(Boolean).join(' · ')}
                    {!w.likely_fetchable && ' · publisher may block automatic download'}
                  </span>
                </div>
                <button className="primary small" disabled={!!importing} onClick={() => importWork(w)}>
                  {importing === w.openalex_id ? 'Adding…' : 'Add for review'}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {works?.length === 0 && (
        <div className="card">
          <p className="muted">
            No preprints found under your ORCID iD. Indexing takes a few days after posting to a
            preprint server, so a very recent one may not appear yet.
          </p>
        </div>
      )}
    </main>
  )
}
