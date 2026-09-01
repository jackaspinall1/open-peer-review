import { chromium } from 'playwright'
import { readFileSync } from 'fs'
const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
await ctx.addCookies([{ name: 'session', value: readFileSync('/tmp/session_cookie.txt','utf8').trim(), domain: 'localhost', path: '/' }])
const page = await ctx.newPage()
await page.goto('http://localhost:5173/me')
await page.waitForSelector('.worklist li', { timeout: 30000 })
await page.waitForTimeout(600)
const rows = await page.evaluate(() => [...document.querySelectorAll('.worklist li')].map((li) => {
  const b = li.querySelector('button').getBoundingClientRect()
  const t = li.querySelector('.worktitle')
  const m = li.querySelector('.workmeta')
  return {
    button: `${Math.round(b.width)}x${Math.round(b.height)}`,
    titleFont: getComputedStyle(t).fontSize,
    titleLines: Math.round(t.getBoundingClientRect().height / parseFloat(getComputedStyle(t).lineHeight || 20)),
    metaFont: getComputedStyle(m).fontSize,
    title: t.textContent.slice(0, 34),
  }
}))
rows.forEach((r) => console.log(`  btn ${r.button.padEnd(8)} title ${r.titleFont}/${r.titleLines}ln meta ${r.metaFont}  ${r.title}`))
console.log('  distinct button sizes:', new Set(rows.map(r => r.button)).size)
await page.screenshot({ path: process.env.SP + '/list_before.png', fullPage: true })
await browser.close()
