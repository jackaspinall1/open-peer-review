/**
 * Pure anchoring logic: text offsets <-> DOM selections over a PDF.js text layer.
 *
 * pageData = { pageText, cumStarts, strLens, textDivs }
 *   pageText:  canonical page string: item.str + ('\n' where item.hasEOL), joined
 *   cumStarts: cumStarts[i] = offset of item i's str within pageText
 *   strLens:   strLens[i] = item i's str length (excludes the virtual '\n')
 *   textDivs:  the TextLayer's spans, 1:1 with items, tagged span.dataset.idx = i
 */

const MAX_QUOTE = 2000
const CONTEXT = 32

export function buildPageData(textContent, textDivs) {
  let pageText = ''
  const cumStarts = []
  const strLens = []
  for (const it of textContent.items) {
    cumStarts.push(pageText.length)
    strLens.push(it.str.length)
    pageText += it.str + (it.hasEOL ? '\n' : '')
  }
  return { pageText, cumStarts, strLens, textDivs }
}

function spanFor(node) {
  const el = node.nodeType === Node.TEXT_NODE ? node.parentElement : node
  return el?.closest?.('span[data-idx]') ?? null
}

/** Map a DOM boundary point to a global character offset in pageText, or null. */
function domPointToOffset(container, offset, textLayerEl, pageData) {
  const { cumStarts, strLens, pageText } = pageData
  if (container.nodeType === Node.TEXT_NODE) {
    const span = spanFor(container)
    if (!span || !textLayerEl.contains(span)) return null
    const idx = +span.dataset.idx
    return cumStarts[idx] + Math.min(offset, strLens[idx])
  }
  if (container === textLayerEl) {
    // e.g. triple-click: offset is a child index into the layer div
    const children = container.children
    if (offset >= children.length) return pageText.length
    const span = spanFor(children[offset])
    return span ? cumStarts[+span.dataset.idx] : null
  }
  const span = spanFor(container)
  if (!span || !textLayerEl.contains(span)) return null
  const idx = +span.dataset.idx
  return cumStarts[idx] + (offset === 0 ? 0 : strLens[idx])
}

const isSpace = (ch) => /\s/.test(ch)

/** Build an anchor from a selection Range known to lie within one text layer. */
export function selectionToAnchor(range, pageNum, textLayerEl, pageData) {
  const { pageText } = pageData
  let s = domPointToOffset(range.startContainer, range.startOffset, textLayerEl, pageData)
  let e = domPointToOffset(range.endContainer, range.endOffset, textLayerEl, pageData)
  if (s === null || e === null) return null
  if (s > e) [s, e] = [e, s]
  while (s < e && isSpace(pageText[s])) s++
  while (e > s && isSpace(pageText[e - 1])) e--
  if (s >= e || e - s > MAX_QUOTE) return null
  return {
    page: pageNum,
    start: s,
    end: e,
    quote: pageText.slice(s, e),
    prefix: pageText.slice(Math.max(0, s - CONTEXT), s),
    suffix: pageText.slice(e, e + CONTEXT),
  }
}

function commonSuffixLen(a, b) {
  let n = 0
  while (n < a.length && n < b.length && a[a.length - 1 - n] === b[b.length - 1 - n]) n++
  return n
}

function commonPrefixLen(a, b) {
  let n = 0
  while (n < a.length && n < b.length && a[n] === b[n]) n++
  return n
}

const SCAN_CAP = 500
const CONFIDENT_QUOTE_LEN = 20
const CONFIDENT_SCORE = 12

/**
 * Locate anchor.quote in pageText; returns {start, end, score} or null.
 * score = matching context characters (prefix tail + suffix head), 0..64.
 * Scanning stops early on a perfect context match, so common short quotes
 * ("the") don't cost a full-page scan.
 */
export function findQuote(anchor, pageText) {
  const { quote } = anchor
  const prefix = anchor.prefix ?? ''
  const suffix = anchor.suffix ?? ''
  const maxScore = prefix.length + suffix.length
  let best = null
  let bestRank = -Infinity
  let scanned = 0
  let i = pageText.indexOf(quote)
  while (i !== -1 && scanned++ < SCAN_CAP) {
    const before = pageText.slice(Math.max(0, i - CONTEXT), i)
    const after = pageText.slice(i + quote.length, i + quote.length + CONTEXT)
    const score = commonSuffixLen(before, prefix) + commonPrefixLen(after, suffix)
    const rank = score - Math.abs(i - (anchor.start ?? 0)) / Math.max(1, pageText.length)
    if (rank > bestRank) {
      bestRank = rank
      best = { start: i, end: i + quote.length, score }
      if (maxScore > 0 && score === maxScore) break
    }
    i = pageText.indexOf(quote, i + 1)
  }
  return best
}

/**
 * Is this hit trustworthy enough to draw a highlight? Long quotes are
 * self-evidently unique; short ones (a single word) need corroborating
 * context, else we pin instead of guessing among many occurrences.
 */
export function confidentHit(anchor, hit) {
  return anchor.quote.length >= CONFIDENT_QUOTE_LEN || hit.score >= CONFIDENT_SCORE
}

/**
 * Search for the quote across pages: the stored page first, then outward by
 * distance (p±1, p±2, ...) covering the whole document. A moved passage is
 * found; a changed one is deliberately NOT (that means the text was revised).
 * pages: {pageNum: pageData}. Returns {page, start, end} or null.
 */
export function findQuoteInPages(anchor, pages, numPages) {
  const order = Array.from({ length: numPages }, (_, i) => i + 1).sort(
    (a, b) => Math.abs(a - anchor.page) - Math.abs(b - anchor.page) || a - b,
  )
  const maxScore = (anchor.prefix ?? '').length + (anchor.suffix ?? '').length
  let best = null
  for (const p of order) {
    const data = pages[p]
    if (!data) continue
    const hit = findQuote(anchor, data.pageText)
    if (!hit || !confidentHit(anchor, hit)) continue
    if (!best || hit.score > best.score) {
      best = { page: p, start: hit.start, end: hit.end, score: hit.score }
      if (maxScore > 0 && hit.score === maxScore) break // perfect context at the nearest page
    }
  }
  return best && { page: best.page, start: best.start, end: best.end }
}

/** Convert global [start, end) offsets back to a DOM Range over the text layer. */
export function offsetsToRange(start, end, pageData) {
  const { cumStarts, strLens, textDivs } = pageData

  const locate = (offset, preferEnd) => {
    // last idx with cumStarts[idx] <= offset
    let lo = 0, hi = cumStarts.length - 1, idx = 0
    while (lo <= hi) {
      const mid = (lo + hi) >> 1
      if (cumStarts[mid] <= offset) { idx = mid; lo = mid + 1 } else hi = mid - 1
    }
    let local = Math.min(offset - cumStarts[idx], strLens[idx])
    // skip items with no text node (empty strs) in the appropriate direction
    let guard = 0
    while (guard++ < cumStarts.length) {
      const div = textDivs[idx]
      const textNode = div?.firstChild
      if (textNode?.nodeType === Node.TEXT_NODE && strLens[idx] > 0) {
        return { node: textNode, offset: Math.min(local, textNode.length) }
      }
      idx += preferEnd ? -1 : 1
      if (idx < 0 || idx >= textDivs.length) return null
      local = preferEnd ? strLens[idx] : 0
    }
    return null
  }

  const s = locate(start, false)
  const e = locate(Math.max(start, end - 1) + 1, true) ?? locate(end, true)
  if (!s || !e) return null
  const range = document.createRange()
  try {
    range.setStart(s.node, s.offset)
    range.setEnd(e.node, e.offset)
  } catch {
    return null
  }
  if (range.collapsed) return null
  return range
}

/** Client rects of a Range, converted to coordinates relative to pageEl. */
export function rectsForRange(range, pageEl) {
  const pageRect = pageEl.getBoundingClientRect()
  return Array.from(range.getClientRects())
    .map((r) => ({
      left: r.left - pageRect.left,
      top: r.top - pageRect.top,
      width: r.width,
      height: r.height,
    }))
    .filter((r) => r.width > 1.5 && r.height > 1)
}
