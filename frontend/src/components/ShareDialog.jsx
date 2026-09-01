import { useEffect, useRef, useState } from 'react'

/**
 * Shown the moment a review window opens, because that is the moment the ask
 * has to happen.
 *
 * Broadcast is offered because it is what people expect, but the copyable link
 * is first: a direct message from an author to a named colleague is the highest
 * converting request in this whole system, and posting to a feed is not.
 */
export default function ShareDialog({ url, title, days, onClose }) {
  const [copied, setCopied] = useState(false)
  const closeRef = useRef(null)

  useEffect(() => {
    closeRef.current?.focus()
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const text = `I have opened my preprint for public peer review: “${title}”. Comments welcome over the next ${days} days.`
  const x = `https://x.com/intent/post?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`
  const linkedin = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`

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

        <div className="sharerow">
          <a className="sharebtn" href={x} target="_blank" rel="noreferrer">Share on X</a>
          <a className="sharebtn" href={linkedin} target="_blank" rel="noreferrer">Share on LinkedIn</a>
        </div>

        <button ref={closeRef} className="linkbtn" onClick={onClose}>Done</button>
      </div>
    </div>
  )
}
