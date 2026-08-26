import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useMe } from '../auth'
import CoiBadge, { ExpertiseBadge } from './CoiBadge'
import VoteButtons from './VoteButtons'

function timeAgo(iso) {
  const s = (Date.now() - new Date(iso).getTime()) / 1000
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  return new Date(iso).toLocaleDateString()
}

function CommentCard({ comment, onVote, canVote, onDelete, onReport, children }) {
  return (
    <div className="commenthead">
      <div className="commentmeta">
        <span
          className={comment.coi?.status === 'author' ? 'alias author' : 'alias'}
          title={comment.coi?.status === 'author' ? comment.coi?.detail : undefined}
        >
          {comment.alias}
        </span>
        {comment.coi?.status !== 'author' && <CoiBadge coi={comment.coi} />}
        {comment.coi?.status !== 'author' && <ExpertiseBadge expertise={comment.expertise} />}
        <span className="muted time">{timeAgo(comment.created_at)}</span>
        {comment.after_window && (
          <span className="latemark" title="Posted after the review window closed; not counted in the round record">
            after the window
          </span>
        )}
      </div>
      <p className={comment.deleted ? 'commentbody muted' : 'commentbody'}>{comment.body}</p>
      {!comment.deleted && (
        <div className="commentactions">
          <VoteButtons comment={comment} onVote={onVote} disabled={!canVote || comment.is_mine} />
          {children}
          {canVote && comment.is_mine && (
            <button className="linkbtn" onClick={() => onDelete(comment)}>Delete</button>
          )}
          {canVote && !comment.is_mine && (
            <button className="linkbtn subtle" onClick={() => onReport(comment)}>Report</button>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * What the record shows about a thread: whether an author answered it, and, once
 * a revision exists, whether the passage it quotes is still there.
 *
 * No resolved/unresolved verdict is asserted. Traditional peer review surfaces a
 * criticism and a response and lets the reader judge; the one thing it cannot do
 * is verify "we have revised the text accordingly", which the anchoring already
 * knows for free.
 */
function ThreadState({ comment, docVersion, resolution }) {
  if (comment.by_author || comment.deleted) return null
  const superseded = comment.version < docVersion
  const revised = superseded && resolution?.pin
  return (
    <div className="threadstate">
      <span className={comment.answered ? 'answered' : 'unanswered'}>
        {comment.answered ? 'Answered by an author' : 'Awaiting author response'}
      </span>
      {superseded && (
        <span
          className="muted"
          title={
            revised
              ? `The quoted passage is no longer in v${docVersion}`
              : `The quoted passage is unchanged in v${docVersion}`
          }
        >
          {revised ? `passage revised in v${docVersion}` : `passage unchanged in v${docVersion}`}
        </span>
      )}
    </div>
  )
}

export default function CommentThread({ comment, docVersion, resolution, active, onVote, onPost, onFocus, onDelete, onReport }) {
  const { me } = useMe()
  const location = useLocation()
  const [replying, setReplying] = useState(false)
  const [replyText, setReplyText] = useState('')
  const [error, setError] = useState(null)
  const loggedIn = me?.logged_in

  const submitReply = async (e) => {
    e.preventDefault()
    setError(null)
    try {
      await onPost({ body: replyText, parentId: comment.id })
      setReplyText('')
      setReplying(false)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div id={`comment-${comment.id}`} className={`commentcard ${active ? 'active' : ''}`}>
      {comment.anchor && (
        <blockquote className="quote" onClick={() => onFocus(comment.id)} title="Show in document">
          {comment.anchor.quote.length > 180 ? comment.anchor.quote.slice(0, 180) + '…' : comment.anchor.quote}
          <span className="pageref">
            p. {resolution?.page ?? comment.anchor.page}{resolution?.pin ? ' (approx.)' : ''}
            {comment.version < docVersion ? ` · written on v${comment.version}` : ''}
          </span>
        </blockquote>
      )}
      <ThreadState comment={comment} docVersion={docVersion} resolution={resolution} />
      <CommentCard comment={comment} onVote={onVote} canVote={loggedIn} onDelete={onDelete} onReport={onReport}>
        {loggedIn ? (
          <button className="linkbtn" onClick={() => setReplying(!replying)}>Reply</button>
        ) : (
          <Link className="linkbtn" to="/login" state={{ from: location.pathname }}>Sign in to reply</Link>
        )}
      </CommentCard>
      {comment.replies.map((r) => (
        <div key={r.id} id={`comment-${r.id}`} className="reply">
          <CommentCard comment={r} onVote={onVote} canVote={loggedIn} onDelete={onDelete} onReport={onReport} />
        </div>
      ))}
      {replying && (
        <form className="replyform" onSubmit={submitReply}>
          <textarea
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            placeholder="Write a reply…"
            rows={3}
            required
          />
          {error && <p className="error">{error}</p>}
          <div className="formrow">
            <button type="submit" className="primary small">Post reply</button>
            <button type="button" className="linkbtn" onClick={() => setReplying(false)}>Cancel</button>
          </div>
        </form>
      )}
    </div>
  )
}
