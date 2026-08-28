import { useEffect, useRef, useState } from 'react'
import { TextLayer } from './pdfSetup'
import { buildPageData, offsetsToRange, rectsForRange } from './anchors'


export default function PdfPage({ pdfDoc, pageNum, width = 820, zoom = 1, highlights, onTextReady, onHighlightClick }) {
  const containerRef = useRef(null)
  const canvasRef = useRef(null)
  const textLayerRef = useRef(null)
  const pageDataRef = useRef(null)
  const [size, setSize] = useState(null)
  const [textReady, setTextReady] = useState(false)
  const [rects, setRects] = useState([])

  // Render page: measure, text layer (eager), canvas (lazy via IntersectionObserver)
  useEffect(() => {
    let cancelled = false
    let renderTask = null
    let textLayer = null
    let observer = null

    const run = async () => {
      const page = await pdfDoc.getPage(pageNum)
      if (cancelled) return
      const scale = (width * zoom) / page.getViewport({ scale: 1 }).width
      const viewport = page.getViewport({ scale })
      setSize({ width: viewport.width, height: viewport.height })

      const layerEl = textLayerRef.current
      layerEl.innerHTML = ''
      // pdf.js 6 sizes spans from --total-scale-factor, which its own stylesheet
      // derives inside a .pdfViewer .page wrapper we do not use, so set both.
      layerEl.style.setProperty('--scale-factor', viewport.scale)
      layerEl.style.setProperty('--total-scale-factor', viewport.scale)
      const textContent = await page.getTextContent()
      if (cancelled) return
      textLayer = new TextLayer({ textContentSource: textContent, container: layerEl, viewport })
      try {
        await textLayer.render()
      } catch (err) {
        if (err?.name === 'AbortException' || cancelled) return
        throw err
      }
      if (cancelled) return
      textLayer.textDivs.forEach((div, i) => { div.dataset.idx = i })
      pageDataRef.current = buildPageData(textContent, textLayer.textDivs)
      setTextReady(true)
      onTextReady?.(pageNum, pageDataRef.current)

      // Canvas only when (nearly) visible: ~30 hi-dpi canvases would eat serious memory
      const renderCanvas = async () => {
        const canvas = canvasRef.current
        if (!canvas || cancelled) return
        const dpr = window.devicePixelRatio || 1
        canvas.width = Math.floor(viewport.width * dpr)
        canvas.height = Math.floor(viewport.height * dpr)
        renderTask = page.render({
          canvasContext: canvas.getContext('2d'),
          viewport,
          transform: dpr !== 1 ? [dpr, 0, 0, dpr, 0, 0] : undefined,
        })
        try {
          await renderTask.promise
        } catch (err) {
          if (err?.name !== 'RenderingCancelledException') throw err
        }
      }
      observer = new IntersectionObserver(
        (entries) => {
          if (entries.some((en) => en.isIntersecting)) {
            observer.disconnect()
            renderCanvas()
          }
        },
        { rootMargin: '150%' },
      )
      observer.observe(containerRef.current)
    }

    run().catch((err) => console.error(`page ${pageNum}:`, err))

    return () => {
      cancelled = true
      observer?.disconnect()
      renderTask?.cancel()
      textLayer?.cancel()
      if (textLayerRef.current) textLayerRef.current.innerHTML = ''
      pageDataRef.current = null
      setTextReady(false)
    }
  }, [pdfDoc, pageNum, width, zoom])

  // Re-anchor highlights whenever comments or text layer change
  useEffect(() => {
    if (!textReady || !pageDataRef.current) { setRects([]); return }
    const pageData = pageDataRef.current
    const out = []
    for (const h of highlights) {
      if (h.pin) { out.push({ id: h.id, active: h.active, pin: true, rects: [] }); continue }
      const range = offsetsToRange(h.start, h.end, pageData)
      if (!range) { out.push({ id: h.id, active: h.active, pin: true, rects: [] }); continue }
      out.push({ id: h.id, active: h.active, pin: false, rects: rectsForRange(range, containerRef.current) })
    }
    setRects(out)
  }, [highlights, textReady])

  const hitTest = (e) => {
    const sel = window.getSelection()
    if (sel && !sel.isCollapsed) return // don't steal clicks that end a selection
    const box = containerRef.current.getBoundingClientRect()
    const x = e.clientX - box.left
    const y = e.clientY - box.top
    for (const h of rects) {
      if (h.rects.some((r) => x >= r.left && x <= r.left + r.width && y >= r.top && y <= r.top + r.height)) {
        onHighlightClick?.(h.id)
        return
      }
    }
  }

  return (
    <div
      ref={containerRef}
      className="pdfpage"
      data-page={pageNum}
      onClick={hitTest}
      style={size ? { width: size.width, height: size.height } : { width: width * zoom, height: width * zoom * 1.294 }}
    >
      <canvas ref={canvasRef} style={size ? { width: size.width, height: size.height } : undefined} />
      <div className="highlightLayer">
        {rects.map((h) =>
          h.pin ? (
            <button
              key={h.id}
              className={`hl-pin ${h.active ? 'active' : ''}`}
              data-comment-id={h.id}
              title="Comment position approximate on this page"
              onClick={() => onHighlightClick?.(h.id)}
            >💬</button>
          ) : (
            h.rects.map((r, i) => (
              <div
                key={`${h.id}-${i}`}
                className={`hl ${h.active ? 'active' : ''}`}
                data-comment-id={i === 0 ? h.id : undefined}
                style={{ left: r.left, top: r.top, width: r.width, height: r.height }}
              />
            ))
          ),
        )}
      </div>
      <div ref={textLayerRef} className="textLayer" data-page={pageNum} />
    </div>
  )
}
