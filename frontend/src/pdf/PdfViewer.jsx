import { useCallback, useEffect, useRef, useState } from 'react'
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
  const [zoom, setZoom] = useState(1)
  const [fitWidth, setFitWidth] = useState(820)

  // Fit the page to the column instead of assuming a desktop-width window.
  // Rounded to 10px so a resize drag does not re-render every page continuously.
  useEffect(() => {
    const el = rootRef.current
    if (!el) return
    const measure = () => {
      const available = el.clientWidth - 32   // column padding
      setFitWidth(Math.max(280, Math.min(820, Math.round(available / 10) * 10)))
    }
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [pdfDoc])
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

  const ZOOM_MIN = 0.6
  const ZOOM_MAX = 3
  const STEPS = [0.6, 0.75, 1, 1.25, 1.5, 2, 2.5, 3]

  /** Zoom about the viewport centre so the reader keeps their place. */
  const applyZoom = useCallback((next) => {
    const el = rootRef.current
    const clamped = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, next))
    setZoom((prev) => {
      if (clamped === prev || !el) return clamped
      const ratio = clamped / prev
      const midpoint = el.scrollTop + el.clientHeight / 2
      requestAnimationFrame(() => {
        el.scrollTop = midpoint * ratio - el.clientHeight / 2
      })
      return clamped
    })
  }, [])

  const step = (dir) => {
    const i = STEPS.findIndex((s) => s >= zoom - 0.001)
    applyZoom(STEPS[Math.min(STEPS.length - 1, Math.max(0, i + dir))] ?? zoom)
  }

  // Ctrl/Cmd + wheel is the standard zoom gesture; without preventDefault the
  // browser zooms the whole page instead, which is exactly what we do not want.
  useEffect(() => {
    const el = rootRef.current
    if (!el) return
    const onWheel = (e) => {
      if (!e.ctrlKey && !e.metaKey) return
      e.preventDefault()
      applyZoom(zoom * (e.deltaY < 0 ? 1.1 : 1 / 1.1))
    }
    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
  }, [zoom, applyZoom])

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
      <div className="zoombar" role="group" aria-label="Zoom">
        <button onClick={() => step(-1)} disabled={zoom <= ZOOM_MIN} title="Zoom out">−</button>
        <button className="zoomlevel" onClick={() => applyZoom(1)} title="Reset to 100%">
          {Math.round(zoom * 100)}%
        </button>
        <button onClick={() => step(1)} disabled={zoom >= ZOOM_MAX} title="Zoom in">+</button>
      </div>
      {!pdfDoc && <p className="muted loadingpdf">Loading PDF…</p>}
      {pdfDoc &&
        Array.from({ length: pdfDoc.numPages }, (_, i) => (
          <PdfPage
            key={i + 1}
            pdfDoc={pdfDoc}
            pageNum={i + 1}
            width={fitWidth}
            zoom={zoom}
            highlights={byPage[i + 1] ?? []}
            onTextReady={(n, data) => { pageDataRef.current[n] = data; setTextTick((t) => t + 1) }}
            onHighlightClick={onHighlightClick}
          />
        ))}
    </div>
  )
}
