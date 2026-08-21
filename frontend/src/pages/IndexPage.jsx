import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { get } from '../api'

export default function IndexPage() {
  const [docs, setDocs] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    get('/api/documents').then(setDocs).catch((e) => setError(e.message))
  }, [])

  if (error) return <main className="page"><p className="error">{error}</p></main>
  if (docs === null) return <main className="page"><p>Loading…</p></main>

  return (
    <main className="page">
      <h1>Papers under review</h1>
      {docs.length === 0 && (
        <p className="muted">Nothing here yet. <Link to="/upload">Upload the first paper.</Link></p>
      )}
      <ul className="doclist">
        {docs.map((d) => (
          <li key={d.id} className="doccard">
            <Link to={`/doc/${d.id}`} className="doctitle">{d.title}</Link>
            <div className="docmeta">
              <span>{d.authors.map((a) => a.name).join(', ') || 'Unknown authors'}</span>
              {d.doi && <span className="doi">DOI: {d.doi}</span>}
              <span className="count">{d.comment_count} comment{d.comment_count === 1 ? '' : 's'}</span>
            </div>
          </li>
        ))}
      </ul>
    </main>
  )
}
