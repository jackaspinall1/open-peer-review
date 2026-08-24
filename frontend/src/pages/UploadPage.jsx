import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { get, postForm, postJSON } from '../api'
import { useMe } from '../auth'
import { extractPdfMeta } from '../pdf/extractMeta'

const EMPTY = { name: '', orcid: '', affiliation: '' }

export default function UploadPage() {
  const { me } = useMe()
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [doi, setDoi] = useState('')
  const [authors, setAuthors] = useState([{ ...EMPTY }])
  const [file, setFile] = useState(null)
  const [error, setError] = useState(null)
  const [metaMsg, setMetaMsg] = useState(null)
  const [busy, setBusy] = useState(false)
  const [works, setWorks] = useState(null)
  const [importing, setImporting] = useState(null)

  useEffect(() => {
    if (!me?.logged_in) return
    get('/api/documents/my-works').then((r) => setWorks(r.works)).catch(() => setWorks([]))
  }, [me?.logged_in])

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

  const onFile = async (f) => {
    setFile(f)
    if (!f) return
    setMetaMsg('Reading paper…')
    try {
      const { title: t, doi: d } = await extractPdfMeta(f)
      const res = await postJSON('/api/documents/resolve-metadata', { title: t, doi: d })
      if (res.found) {
        setTitle(res.title || t || '')
        if (res.doi) setDoi(res.doi)
        if (res.authors.length)
          setAuthors(res.authors.map((a) => ({
            name: a.name, orcid: a.orcid || '', affiliation: a.affiliation || '',
          })))
        setMetaMsg(
          `Metadata found on OpenAlex via ${res.source === 'doi' ? 'DOI' : 'title match'} — check and edit before uploading.`,
        )
      } else {
        if (t) setTitle((cur) => cur || t)
        if (d) setDoi((cur) => cur || d)
        setMetaMsg('Not found on OpenAlex — extracted what was possible; fill in the rest.')
      }
    } catch (err) {
      setMetaMsg(`Could not read metadata (${err.message}) — fill in manually.`)
    }
  }

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
      <h1>Add a paper</h1>

      {works === null && <p className="muted">Looking up your papers…</p>}
      {works?.length > 0 && (
        <section className="card" style={{ marginBottom: 20 }}>
          <h2>Your preprints</h2>
          <p className="formnote">
            Preprints listed under your ORCID iD. Adding one fetches the PDF and author
            record automatically — nothing to type. When you post a revised version to the
            preprint server, use “Check for new version” on the paper to pull it through.
          </p>
          <p className="formnote warranty">
            By adding a paper you confirm you have the right to post it here on behalf of its
            co-authors. Any listed author can ask for it to be removed.
          </p>
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
                  {importing === w.openalex_id ? 'Importing…' : 'Add for review'}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
      {works?.length === 0 && (
        <p className="muted">
          No preprints found under your ORCID iD (it can take a few days for a new preprint
          to be indexed) — upload a PDF instead.
        </p>
      )}

      <h2 style={{ margin: '24px 0 10px' }}>Or upload a PDF</h2>
      <form onSubmit={submit} className="card form">
        <label>PDF file
          <input type="file" accept="application/pdf" onChange={(e) => onFile(e.target.files[0])} required />
        </label>
        {metaMsg && <div className="formnote">{metaMsg}</div>}
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
              <input placeholder="Affiliation (optional)" value={a.affiliation} onChange={(e) => setAuthor(i, 'affiliation', e.target.value)} />
              <button type="button" className="linkbtn" onClick={() => setAuthors(authors.filter((_, j) => j !== i))} disabled={authors.length === 1}>✕</button>
            </div>
          ))}
          <button type="button" className="linkbtn" onClick={() => setAuthors([...authors, { ...EMPTY }])}>+ Add author</button>
        </fieldset>
        <p className="formnote warranty">
          By uploading you confirm you have the right to post this paper here on behalf of its
          co-authors. Any listed author can ask for it to be removed.
        </p>
        {error && <p className="error">{error}</p>}
        <button type="submit" className="primary" disabled={busy || !file}>{busy ? 'Uploading…' : 'Upload'}</button>
      </form>
    </main>
  )
}
