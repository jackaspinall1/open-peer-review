import { useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useMe } from '../auth'
import CommentThread from './CommentThread'

function DraftCard({ draft, onPost, onCancel }) {
  const { me } = useMe()
  const location = useLocation()
  const [body, setBody] = useState('')
  const [error, setError] = useState(null)
  const ref = useRef(null)

  useEffect(() => { ref.current?.focus() }, [])

  if (!me?.logged_in) {
    return (
      <div className="commentcard draft">
        {draft.anchor && <blockquote className="quote">{draft.anchor.quote}</blockquote>}
        <p className="muted">
          <Link to="/login" state={{ from: location.pathname }}>Sign in with ORCID</Link> to post this comment.
        </p>
        <button className="linkbtn" onClick={onCancel}>Discard</button>
      </div>
    )
  }

  const submit = async (e) => {
    e.preventDefault()
    setError(null)
    try {
      await onPost({ body, anchor: draft.anchor })
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <form className="commentcard draft" onSubmit={submit}>
      {draft.anchor ? (
        <blockquote className="quote">
          {draft.anchor.quote.length > 180 ? draft.anchor.quote.slice(0, 180) + '…' : draft.anchor.quote}
          <span className="pageref">p. {draft.anchor.page}</span>
        </blockquote>
      ) : (
        <div className="formnote">General comment on the whole paper</div>
      )}
      <textarea
        ref={ref}
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="Write your review comment…"
        rows={4}
        required
      />
      {error && <p className="error">{error}</p>}
      <div className="formrow">
        <button type="submit" className="primary small">Post comment</button>
        <button type="button" className="linkbtn" onClick={onCancel}>Cancel</button>
      </div>
      <p className="formnote">Posted as your per-paper pseudonym (e.g. “Reviewer 2”), never your name.</p>
    </form>
  )
}

export default function CommentSidebar({ comments, docVersion, resolutions, draft, activeId, onPost, onCancelDraft, onVote, onFocus, onStartGeneral, onDelete, onReport }) {
  return (
    <aside className="sidebar">
      <div className="sidebarhead">
        <h2>Comments ({comments.reduce((n, c) => n + 1 + c.replies.length, 0)})</h2>
        {!draft && <button className="linkbtn" onClick={onStartGeneral}>+ General comment</button>}
      </div>
      {draft && <DraftCard draft={draft} onPost={onPost} onCancel={onCancelDraft} />}
      {comments.length === 0 && !draft && (
        <p className="muted sidebarhint">
          Select a sentence in the paper to leave the first comment.
        </p>
      )}
      {comments.length > 0 && (
        <p className="conduct">Criticise the work, not the person.</p>
      )}
      {comments.map((c) => (
        <CommentThread
          key={c.id}
          comment={c}
          docVersion={docVersion}
          resolution={resolutions?.[c.id]}
          active={c.id === activeId}
          onVote={onVote}
          onPost={onPost}
          onFocus={onFocus}
          onDelete={onDelete}
          onReport={onReport}
        />
      ))}
    </aside>
  )
}
