import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { get, postForm, postJSON } from '../api'
import PdfViewer from '../pdf/PdfViewer'
import SelectionPopover from '../pdf/SelectionPopover'
import CommentSidebar from '../components/CommentSidebar'

export default function ViewerPage() {
  const { id } = useParams()
  const [doc, setDoc] = useState(null)
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null)
  const [popover, setPopover] = useState(null) // {x, y, anchor}
  const [draft, setDraft] = useState(null) // {anchor} or {anchor: null} for general comment
  const [activeId, setActiveId] = useState(null)
  const [resolutions, setResolutions] = useState({})

  useEffect(() => {
    get(`/api/documents/${id}`).then(setDoc).catch((e) => setError(e.message))
  }, [id])

  const uploadRevision = async (file) => {
    if (!file) return
    try {
      await postForm(`/api/documents/${id}/revision`, (() => { const fd = new FormData(); fd.append('pdf', file); return fd })())
      setActiveId(null)
      setDraft(null)
      setDoc(await get(`/api/documents/${id}`))
      setToast('Revision uploaded — comments are re-anchoring against the new version.')
    } catch (e) {
      setToast(e.message)
    }
  }

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 3000)
    return () => clearTimeout(t)
  }, [toast])

  const onSelectAnchor = useCallback((anchor, rect, warning) => {
    if (warning) { setToast(warning); setPopover(null); return }
    setPopover({ x: rect.right, y: rect.bottom, anchor })
  }, [])

  const startDraft = () => {
    setDraft({ anchor: popover.anchor })
    setPopover(null)
    window.getSelection()?.removeAllRanges()
  }

  const postComment = async ({ body, anchor, parentId }) => {
    const resp = await postJSON(`/api/documents/${id}/comments`, {
      body,
      anchor: anchor ?? undefined,
      parent_id: parentId ?? undefined,
    })
    setDoc((d) => ({ ...d, comments: resp.comments }))
    setDraft(null)
    return resp.id
  }

  const vote = async (commentId, value) => {
    const votes = await postJSON(`/api/comments/${commentId}/vote`, { value })
    setDoc((d) => ({
      ...d,
      comments: d.comments.map((c) => {
        if (c.id === commentId) return { ...c, votes }
        return { ...c, replies: c.replies.map((r) => (r.id === commentId ? { ...r, votes } : r)) }
      }),
    }))
  }

  const focusComment = useCallback((commentId) => {
    setActiveId(commentId)
    document.getElementById(`comment-${commentId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [])

  const focusHighlight = (commentId) => {
    setActiveId(commentId)
    const el = document.querySelector(`.pdfcolumn [data-comment-id="${commentId}"]`)
    const target = el ?? (() => {
      const c = doc.comments.find((x) => x.id === commentId)
      const page = resolutions[commentId]?.page ?? c?.anchor?.page
      return page ? document.querySelector(`.pdfpage[data-page="${page}"]`) : null
    })()
    target?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  if (error) return <main className="page"><p className="error">{error}</p></main>
  if (!doc) return <main className="page"><p>Loading…</p></main>

  return (
    <div className="viewer" onMouseDown={() => setPopover(null)}>
      <div className="viewerhead">
        <div>
          <h1>{doc.title}</h1>
          <div className="docmeta">
            <span>{doc.authors.map((a) => a.name).join(', ')}</span>
            {doc.doi && <span className="doi">DOI: {doc.doi}</span>}
            <span>v{doc.version}</span>
          </div>
        </div>
        {doc.is_uploader && (
          <label className="linkbtn revisionbtn">
            Upload revision
            <input
              type="file"
              accept="application/pdf"
              style={{ display: 'none' }}
              onChange={(e) => { uploadRevision(e.target.files[0]); e.target.value = '' }}
            />
          </label>
        )}
      </div>
      <div className="viewerbody">
        <PdfViewer
          url={`/api/documents/${id}/pdf?v=${doc.version}`}
          docVersion={doc.version}
          comments={doc.comments}
          activeCommentId={activeId}
          onSelectAnchor={onSelectAnchor}
          onHighlightClick={focusComment}
          onResolutions={setResolutions}
        />
        <CommentSidebar
          comments={doc.comments}
          docVersion={doc.version}
          resolutions={resolutions}
          draft={draft}
          activeId={activeId}
          onCancelDraft={() => setDraft(null)}
          onPost={postComment}
          onVote={(cid, v) => vote(cid, v).catch((e) => setToast(e.message))}
          onFocus={focusHighlight}
          onStartGeneral={() => setDraft({ anchor: null })}
        />
      </div>
      <SelectionPopover popover={popover} onComment={startDraft} />
      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}
