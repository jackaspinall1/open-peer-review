// Legacy build: identical API, but ships polyfills for very new JS features
// (e.g. Map.prototype.getOrInsertComputed) that the modern build assumes native.
// Safari and slightly older Chrome/Firefox need this.
import { getDocument, GlobalWorkerOptions, TextLayer } from 'pdfjs-dist/legacy/build/pdf.mjs'

GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/legacy/build/pdf.worker.min.mjs',
  import.meta.url,
).toString()
// If a future Vite upgrade breaks the new URL(...) pattern, switch to:
//   import workerUrl from 'pdfjs-dist/legacy/build/pdf.worker.min.mjs?url'

export { getDocument, TextLayer }
