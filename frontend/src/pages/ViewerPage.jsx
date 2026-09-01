import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useMe } from '../auth'
import { del, get, postForm, postJSON } from '../api'
import PdfViewer from '../pdf/PdfViewer'
import SelectionPopover from '../pdf/SelectionPopover'
import CommentSidebar from '../components/CommentSidebar'
import RoundStatus from '../components/RoundStatus'

/** Human-readable licence, e.g. "cc-by-nc-nd" -> "CC BY-NC-ND". */
function licenceLabel(code) {
  if (!code) return null
  return code.startsWith('cc-') ? code.replace('cc-', 'CC ').toUpperCase().replace('CC ', 'CC ') : code
}

export default function ViewerPage() {
  const { id } = useParams()
  const { me } = useMe()
  const [doc, setDoc] = useState(null)
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null)
  const [popover, setPopover] = useState(null) // {x, y, anchor}
  const [draft, setDraft] = useState(null) // {anchor} or {anchor: null} for general comment
  const [activeId, setActiveId] = useState(null)
  const [resolutions, setResolutions] = useState({})
  const [standing, setStanding] = useState(null)

  useEffect(() => {
    get(`/api/documents/${id}`).then(setDoc).catch((e) => setError(e.message))
  }, [id])

  const [roundBusy, setRoundBusy] = useState(false)

  const roundAction = async (path, okMsg) => {
    setRoundBusy(true)
    try {
      await postJSON(`/api/documents/${id}/${path}`, {})
      setDoc(await get(`/api/documents/${id}`))
      setToast(okMsg)
    } catch (e) {
      setToast(e.message)
    } finally {
      setRoundBusy(false)
    }
  }

  const checkSource = async () => {
    setToast('Checking the preprint server…')
    try {
      const r = await postJSON(`/api/documents/${id}/check-source`, {})
      setDoc(await get(`/api/documents/${id}`))
      setToast(
        r.updated
          ? `New version found — now showing v${r.version}. Comments are re-anchoring.`
          : 'Already showing the latest version on the preprint server.',
      )
    } catch (e) {
      setToast(e.message)
    }
  }

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

  // The badges a comment from this reader would carry. Re-checked shortly after
  // arriving because the relationship is computed off the request path.
  useEffect(() => {
    if (!me?.logged_in) { setStanding(null); return }
    let cancelled = false
    const load = () => get(`/api/documents/${id}/my-relationship`).then((r) => {
      if (cancelled) return r
      setStanding(r)
      return r
    })
    load().then((r) => {
      if (!cancelled && (r.coi.status === 'pending' || r.expertise.level === 'pending')) {
        const t = setTimeout(load, 4000)
        return () => clearTimeout(t)
      }
    }).catch(() => {})
    return () => { cancelled = true }
  }, [id, me?.orcid, me?.logged_in])

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

  const deleteComment = async (comment) => {
    if (!window.confirm('Delete this comment? Replies to it will remain.')) return
    try {
      await del(`/api/comments/${comment.id}`)
      setDoc(await get(`/api/documents/${id}`))
    } catch (e) {
      setToast(e.message)
    }
  }

  const reportComment = async (comment) => {
    const reason = window.prompt('Report this comment for a moderator to review. Reason (optional):')
    if (reason === null) return
    try {
      await postJSON(`/api/comments/${comment.id}/report`, { reason })
      setToast('Reported. A moderator will review it; nothing is hidden automatically.')
    } catch (e) {
      setToast(e.message)
    }
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
            <span title={doc.authors.map((a) => (a.affiliation ? `${a.name} — ${a.affiliation}` : a.name)).join('\n')}>
              {doc.authors.map((a) => a.name).join(', ')}
            </span>
            {doc.doi && <span className="doi">DOI: {doc.doi}</span>}
            <span>v{doc.version}</span>
            {doc.license && <span className="licence">{licenceLabel(doc.license)}</span>}
            {doc.source_url && (
              <a className="sourcelink" href={doc.source_url} target="_blank" rel="noreferrer">
                Original on {doc.source_name || 'the preprint server'} ↗
              </a>
            )}
            <RoundStatus round={doc.round} />
          </div>
        </div>
        {doc.can_manage && !doc.round?.open && (
          <button className="linkbtn revisionbtn" disabled={roundBusy}
            onClick={() => roundAction('rounds', 'Review window open for 14 days. Now go and ask people.')}>
            {doc.round ? 'Open a new round' : 'Open review'}
          </button>
        )}
        {doc.can_manage && doc.round?.open && doc.round.extendable && (
          <button className="linkbtn revisionbtn" disabled={roundBusy}
            onClick={() => {
              // Extensions are recorded on the review record, so say so before
              // taking one rather than after.
              const ok = window.confirm(
                `Extend this review window by a week?\n\n` +
                `It closes in ${doc.round.days_left} day${doc.round.days_left === 1 ? '' : 's'}. ` +
                `Extensions are shown on the paper's review record, so a round that ran long ` +
                `is visible to readers.`,
              )
              if (ok) roundAction('rounds/extend', 'Extended by a week.')
            }}>
            Extend by a week
          </button>
        )}
        {doc.can_manage && doc.has_source && (
          <button className="linkbtn revisionbtn" onClick={checkSource}>
            Check for new version
          </button>
        )}
        {doc.can_manage && (
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
          round={doc.round}
          canManage={doc.can_manage}
          standing={standing}
          resolutions={resolutions}
          draft={draft}
          activeId={activeId}
          onCancelDraft={() => setDraft(null)}
          onPost={postComment}
          onVote={(cid, v) => vote(cid, v).catch((e) => setToast(e.message))}
          onFocus={focusHighlight}
          onStartGeneral={() => setDraft({ anchor: null })}
          onDelete={deleteComment}
          onReport={reportComment}
        />
      </div>
      <SelectionPopover popover={popover} onComment={startDraft} />
      {toast && <div className="toast">{toast}</div>}
    </div>
  )
}
