import { useEffect, useRef, useState } from 'react'

/**
 * Shown the moment a review window opens, because that is the moment the ask
 * has to happen.
 *
 * It offers the link and nothing else. A direct message from an author to a
 * named colleague is the highest converting request in this system, and a share
 * button pointed at a feed is not, so the useful thing is a URL on the
 * clipboard.
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
          Reviews happen because someone was asked. A message to three colleagues who know this
          work will do more than any post.
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
