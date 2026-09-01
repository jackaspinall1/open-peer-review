import { useEffect, useRef, useState } from 'react'

/**
 * Shown the moment a review window opens, because that is the moment the ask
 * has to happen.
 *
 * It offers the link and nothing else, because the useful thing is a URL on the
 * clipboard rather than a button pointed at a feed.
 *
 * The copy nudges toward second-order contacts: people in the same community
 * rather than immediate collaborators. A co-author's comment carries a conflict
 * badge and is discounted accordingly, so the reviewer worth reaching is one
 * who knows the field but is not on the paper.
 */
export default function ShareDialog({ url, onClose }) {
  const [copied, setCopied] = useState(false)
  const closeRef = useRef(null)

  useEffect(() => {
    closeRef.current?.focus()
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div className="modalveil" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-label="Share this paper">
        <h2>Open for review. Now ask people.</h2>
        <p className="muted">
          Reviews happen because someone was asked. Share with your network via messages and posts.
          The most useful reviewers know this area well but are not your co-authors.
        </p>

        <div className="sharelink">
          <input readOnly value={url} onFocus={(e) => e.target.select()} />
          <button className="primary small" onClick={copy}>{copied ? 'Copied' : 'Copy link'}</button>
        </div>

        <button ref={closeRef} className="linkbtn" onClick={onClose}>Done</button>
      </div>
    </div>
  )
}
