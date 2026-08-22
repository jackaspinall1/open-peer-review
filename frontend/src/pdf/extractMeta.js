import { getDocument } from './pdfSetup'

/**
 * Best-effort local extraction before upload: a title candidate (largest-font
 * text run in the upper part of page 1) and a DOI string (regex over the first
 * two pages). Both are only hints — OpenAlex resolution supplies the verified
 * record, and every field stays editable.
 */
export async function extractPdfMeta(file) {
  const task = getDocument({ data: await file.arrayBuffer() })
  try {
    const doc = await task.promise
    const page = await doc.getPage(1)
    const tc = await page.getTextContent()
    const vh = page.getViewport({ scale: 1 }).height

    const top = tc.items.filter(
      (it) => it.str.trim() && vh - it.transform[5] < vh * 0.45,
    )
    let title = null
    if (top.length) {
      const max = Math.max(...top.map((it) => Math.abs(it.transform[3])))
      title = top
        .filter((it) => Math.abs(it.transform[3]) >= max * 0.92)
        .map((it) => it.str)
        .join(' ')
        .replace(/\s+/g, ' ')
        .trim()
      if (title.length < 8 || title.length > 300) title = null
    }

    let doi = null
    for (let n = 1; n <= Math.min(2, doc.numPages) && !doi; n++) {
      const text = (await (await doc.getPage(n)).getTextContent()).items
        .map((i) => i.str)
        .join(' ')
      const m = text.match(/\b10\.\d{4,9}\/[^\s"'<>,;]+/)
      if (m) doi = m[0].replace(/[).,;]+$/, '')
    }
    return { title, doi }
  } finally {
    task.destroy()
  }
}
