import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { postForm } from '../api'
import { useMe } from '../auth'

export default function UploadPage() {
  const { me } = useMe()
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [doi, setDoi] = useState('')
  const [authors, setAuthors] = useState([{ name: '', orcid: '' }])
  const [file, setFile] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  if (me && !me.logged_in) {
    return (
      <main className="page narrow">
        <h1>Upload a paper</h1>
        <p className="muted">You need to <a href="/login">sign in</a> to upload.</p>
      </main>
    )
  }

  const setAuthor = (i, field, value) =>
    setAuthors(authors.map((a, j) => (j === i ? { ...a, [field]: value } : a)))

  const submit = async (e) => {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const fd = new FormData()
      fd.append('pdf', file)
      fd.append('title', title)
      fd.append('doi', doi)
      fd.append('authors', JSON.stringify(authors.filter((a) => a.name.trim())))
      const { id } = await postForm('/api/documents', fd)
      navigate(`/doc/${id}`)
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <main className="page narrow">
      <h1>Upload a paper</h1>
      <form onSubmit={submit} className="card form">
        <label>PDF file
          <input type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files[0])} required />
        </label>
        <label>Title
          <input value={title} onChange={(e) => setTitle(e.target.value)} required />
        </label>
        <label>DOI <span className="muted">(optional)</span>
          <input value={doi} onChange={(e) => setDoi(e.target.value)} placeholder="10.1000/xyz123" />
        </label>
        <fieldset>
          <legend>Authors <span className="muted">(ORCIDs enable the conflict-of-interest check)</span></legend>
          {authors.map((a, i) => (
            <div key={i} className="authorrow">
              <input placeholder="Name" value={a.name} onChange={(e) => setAuthor(i, 'name', e.target.value)} />
              <input placeholder="ORCID (optional)" value={a.orcid} onChange={(e) => setAuthor(i, 'orcid', e.target.value)} />
              <button type="button" className="linkbtn" onClick={() => setAuthors(authors.filter((_, j) => j !== i))} disabled={authors.length === 1}>✕</button>
            </div>
          ))}
          <button type="button" className="linkbtn" onClick={() => setAuthors([...authors, { name: '', orcid: '' }])}>+ Add author</button>
        </fieldset>
        {error && <p className="error">{error}</p>}
        <button type="submit" className="primary" disabled={busy || !file}>{busy ? 'Uploading…' : 'Upload'}</button>
      </form>
    </main>
  )
}
