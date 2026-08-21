import { useEffect, useRef, useState } from 'react'
import { getDocument } from './pdfSetup'
import { confidentHit, findQuote, findQuoteInPages, selectionToAnchor } from './anchors'
import PdfPage from './PdfPage'

const closestTextLayer = (node) => {
  const el = node?.nodeType === Node.TEXT_NODE ? node.parentElement : node
  return el?.closest?.('.textLayer') ?? null
}

export default function PdfViewer({ url, docVersion, comments, activeCommentId, onSelectAnchor, onHighlightClick, onResolutions }) {
  const [pdfDoc, setPdfDoc] = useState(null)
  const [error, setError] = useState(null)
  const [textTick, setTextTick] = useState(0) // bumped as each page's text layer readies
  const [resolutions, setResolutions] = useState({}) // commentId -> {page,start,end} | {page,pin}
  const pageDataRef = useRef({}) // pageNum -> pageData
  const rootRef = useRef(null)

  useEffect(() => {
    let cancelled = false
    pageDataRef.current = {}
    setResolutions({})
    const task = getDocument({ url: new URL(url, window.location.href).href })
    task.promise
      .then((doc) => { if (!cancelled) setPdfDoc(doc) })
      .catch((err) => { if (!cancelled) setError(err.message) })
    return () => {
      cancelled = true
      task.destroy()
      setPdfDoc(null)
    }
  }, [url])

  // Resolve each anchor to a concrete page+offsets. Own page first; once every
  // page's text is available, fall back to searching outward across the document.
  useEffect(() => {
    if (!pdfDoc) return
    const pages = pageDataRef.current
    const allLoaded = Object.keys(pages).length === pdfDoc.numPages
    const next = {}
    for (const c of comments) {
      if (!c.anchor) continue
      const own = pages[c.anchor.page]
      if (own) {
        const hit = findQuote(c.anchor, own.pageText)
        if (hit && confidentHit(c.anchor, hit)) {
          next[c.id] = { page: c.anchor.page, start: hit.start, end: hit.end }
          continue
        }
      }
      if (!allLoaded) continue // don't pin until every page's text has been checked
      // Cross-page re-attachment is reserved for comments written on an OLDER
      // version: on an unchanged document a quote missing from its own page is
      // a bad anchor, not moved text, and must pin rather than guess.
      const mayReattach = (c.version ?? 1) < (docVersion ?? 1)
      next[c.id] = (mayReattach ? findQuoteInPages(c.anchor, pages, pdfDoc.numPages) : null)
        ?? { page: Math.min(c.anchor.page, pdfDoc.numPages), pin: true }
    }
    setResolutions(next)
  }, [pdfDoc, docVersion, comments, textTick])

  useEffect(() => { onResolutions?.(resolutions) }, [resolutions, onResolutions])

  const handleMouseUp = () => {
    const sel = window.getSelection()
    if (!sel || sel.isCollapsed || sel.rangeCount === 0) return
    const range = sel.getRangeAt(0)
    const startLayer = closestTextLayer(range.startContainer)
    const endLayer = closestTextLayer(range.endContainer)
    if (!startLayer || startLayer !== endLayer) {
      if (startLayer || endLayer) onSelectAnchor?.(null, null, 'Select within a single page to comment.')
      return
    }
    const pageNum = +startLayer.dataset.page
    const pageData = pageDataRef.current[pageNum]
    if (!pageData) return
    const anchor = selectionToAnchor(range, pageNum, startLayer, pageData)
    if (anchor) onSelectAnchor?.(anchor, range.getBoundingClientRect(), null)
  }

  if (error) return <div className="pdfcolumn"><p className="error">Failed to load PDF: {error}</p></div>

  const byPage = {}
  for (const c of comments) {
    const r = resolutions[c.id]
    if (!c.anchor || !r) continue
    if (!byPage[r.page]) byPage[r.page] = []
    byPage[r.page].push({ id: c.id, start: r.start, end: r.end, pin: !!r.pin, active: c.id === activeCommentId })
  }

  return (
    <div className="pdfcolumn" ref={rootRef} onMouseUp={handleMouseUp}>
      {!pdfDoc && <p className="muted loadingpdf">Loading PDF…</p>}
      {pdfDoc &&
        Array.from({ length: pdfDoc.numPages }, (_, i) => (
          <PdfPage
            key={i + 1}
            pdfDoc={pdfDoc}
            pageNum={i + 1}
            highlights={byPage[i + 1] ?? []}
            onTextReady={(n, data) => { pageDataRef.current[n] = data; setTextTick((t) => t + 1) }}
            onHighlightClick={onHighlightClick}
          />
        ))}
    </div>
  )
}
