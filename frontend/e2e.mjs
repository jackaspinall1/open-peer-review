import { chromium, webkit } from 'playwright'
const engine = process.env.BROWSER === 'webkit' ? webkit : chromium

const BASE = 'http://localhost:5173'
const shot = (p, name) => p.screenshot({ path: process.env.SP + '/' + name, fullPage: false })

const browser = await engine.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
page.on('console', (m) => { if (m.type() === 'error') console.log('CONSOLE ERROR:', m.text()) })
page.on('pageerror', (e) => console.log('PAGE ERROR:', e.message))

// 1. Viewer renders PDF with text layer
await page.goto(`${BASE}/doc/1`)
await page.waitForSelector('.pdfpage canvas', { timeout: 20000 })
await page.waitForFunction(() => document.querySelectorAll('.textLayer span').length > 100, null, { timeout: 20000 })
const nPages = await page.locator('.pdfpage').count()
const nSpans = await page.evaluate(() => document.querySelectorAll('.textLayer span').length)
console.log(`STEP1 OK: ${nPages} pages, ${nSpans} text spans`)
await shot(page, 'viewer_initial.png')

// Existing comment (fake anchor from curl test) should re-anchor or pin on page 2
const hlCount = await page.evaluate(() => document.querySelectorAll('.hl').length)
const pinCount = await page.evaluate(() => document.querySelectorAll('.hl-pin').length)
console.log(`STEP1b: existing comment -> ${hlCount} highlight rects, ${pinCount} pins`)

// 2. Mock login
await page.goto(`${BASE}/login`)
await page.fill('input[placeholder="0000-0002-1825-0097"]', '0000-0002-9999-000X')
await page.click('button[type=submit]')
await page.waitForSelector('.username', { timeout: 5000 })
console.log('STEP2 OK: logged in as', await page.locator('.username').textContent())

// 3. Select a sentence on page 1 and comment on it
await page.goto(`${BASE}/doc/1`)
await page.waitForFunction(() => document.querySelectorAll('.pdfpage[data-page="1"] .textLayer span').length > 50, null, { timeout: 20000 })
const quote = await page.evaluate(() => {
  const layer = document.querySelector('.pdfpage[data-page="1"] .textLayer')
  const spans = [...layer.querySelectorAll('span[data-idx]')].filter((s) => (s.firstChild?.textContent ?? '').trim().length > 40)
  const span = spans[3]
  const textNode = span.firstChild
  const range = document.createRange()
  range.setStart(textNode, 0)
  range.setEnd(textNode, Math.min(60, textNode.length))
  const sel = window.getSelection()
  sel.removeAllRanges()
  sel.addRange(range)
  document.querySelector('.pdfcolumn').dispatchEvent(new MouseEvent('mouseup', { bubbles: true }))
  return range.toString()
})
console.log('STEP3 selecting:', JSON.stringify(quote))
await page.waitForSelector('.selpopover', { timeout: 5000 })
await page.click('.selpopover')
await page.waitForSelector('.draft textarea', { timeout: 5000 })
await page.fill('.draft textarea', 'This sentence needs a citation.')
await page.click('.draft button[type=submit]')
await page.waitForFunction(() => document.querySelectorAll('.commentcard:not(.draft)').length >= 2, null, { timeout: 5000 })
console.log('STEP3 OK: comment posted, aliases:', await page.evaluate(() => [...document.querySelectorAll('.alias')].map((e) => e.textContent)))

// 4. Reload -> highlight re-anchors
await page.reload()
await page.waitForFunction(() => document.querySelectorAll('.pdfpage[data-page="1"] .hl').length > 0, null, { timeout: 20000 })
const hlQuoteOk = await page.evaluate(() => {
  const cards = [...document.querySelectorAll('.commentcard .quote')]
  return cards.map((c) => c.textContent.slice(0, 40))
})
console.log('STEP4 OK: highlights re-anchored after reload; quotes:', hlQuoteOk)
await shot(page, 'viewer_commented.png')

// 5. Click highlight -> sidebar card activates
await page.evaluate(() => {
  const hl = document.querySelector('.pdfpage[data-page="1"] .hl')
  const r = hl.getBoundingClientRect()
  const el = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2)
  el.dispatchEvent(new MouseEvent('click', { bubbles: true, clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 }))
})
await page.waitForSelector('.commentcard.active', { timeout: 5000 })
console.log('STEP5 OK: highlight click activates sidebar card')

// 6. Same-version: quotes missing from their stored page must PIN, never re-attach
const ids = await page.evaluate(async () => {
  const doc = await (await fetch('/api/documents/1')).json()
  const src = doc.comments.find((c) => c.anchor && c.anchor.page === 1)
  const q = src.anchor.quote
  const word = q.split(' ')[0] // e.g. "convolutional" — occurs on several pages
  const post = async (body, anchor) =>
    (await (await fetch('/api/documents/1/comments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ body, anchor }),
    })).json()).id
  return {
    longQ: await post('cross-page fallback test', { ...src.anchor, page: 7 }),
    wordCtx: await post('single word with context', {
      page: 7, quote: word, prefix: src.anchor.prefix,
      suffix: q.slice(word.length, word.length + 32),
      start: src.anchor.start, end: src.anchor.start + word.length,
    }),
    noCtx: await post('ambiguous word no context', { page: 3, quote: 'the', prefix: 'zzz', suffix: 'zzz', start: 0, end: 3 }),
  }
})
await page.reload()
await page.waitForFunction(
  (id) => document.querySelector(`.pdfpage[data-page="7"] .hl-pin[data-comment-id="${id}"]`),
  ids.longQ, { timeout: 30000 },
)
console.log('STEP6 OK: on the same version, a wrong-page anchor pins instead of re-attaching')

// 7. Author uploads a revision -> older comments may re-attach across pages
await page.goto(`${BASE}/login`)
await page.fill('input[placeholder="0000-0002-1825-0097"]', '0000-0002-1825-0097') // the uploader
await page.click('button[type=submit]')
await page.waitForSelector('.username', { timeout: 5000 })
await page.goto(`${BASE}/doc/1`)
await page.waitForSelector('.revisionbtn input[type=file]', { state: 'attached', timeout: 10000 })
await page.setInputFiles('.revisionbtn input[type=file]', process.env.SP + '/test_paper.pdf')
await page.waitForFunction(() => document.querySelector('.viewerhead .docmeta')?.textContent.includes('v2'), null, { timeout: 15000 })
await page.waitForFunction(
  (id) => document.querySelector(`.pdfpage[data-page="1"] .hl[data-comment-id="${id}"]`),
  ids.longQ, { timeout: 30000 },
)
await page.waitForFunction(
  (id) => document.querySelector(`.pdfpage[data-page="1"] .hl[data-comment-id="${id}"]`),
  ids.wordCtx, { timeout: 30000 },
)
await page.waitForFunction(
  (id) => document.querySelector(`.pdfpage[data-page="3"] .hl-pin[data-comment-id="${id}"]`),
  ids.noCtx, { timeout: 30000 },
)
const ref = (await page.locator(`#comment-${ids.longQ} .pageref`).textContent()).trim()
if (!ref.includes('p. 1') || !ref.includes('v1')) throw new Error(`pageref was "${ref}"`)
console.log(`STEP7 OK: after revision, long quote + context-backed word re-attached to p.1 ("${ref}"); context-free 'the' stayed pinned`)

await browser.close()
console.log('ALL STEPS PASSED')
