import { chromium } from 'playwright'
const browser = await chromium.launch()
const ctx = await browser.newContext()          // fresh: nobody signed in
const page = await ctx.newPage()
page.on('pageerror', (e) => console.log('PAGEERROR:', e.message))

await page.goto('http://localhost:5173/doc/2')
await page.waitForSelector('.pdfpage canvas', { timeout: 30000 })
await page.waitForTimeout(1500)
console.log('landing on a paper link, signed out:')
console.log('  header shows      :', (await page.locator('.topbar nav').innerText()).replace(/\n/g, ' | '))
console.log('  paper readable    :', (await page.locator('.pdfpage canvas').count()) > 0)
console.log('  comments visible  :', await page.locator('.commentcard').count())
console.log('  sidebar prompt    :', (await page.locator('.sidebar').innerText()).split('\n').filter(Boolean).slice(0, 2).join(' | '))
console.log('  standing panel    :', await page.locator('.standing').count(), '(0 = only shown when signed in)')

// what happens when they try to act
const before = page.url()
await page.locator('.linkbtn', { hasText: 'Sign in to reply' }).first().click().catch(() => {})
await page.waitForTimeout(800)
console.log('  clicking "Sign in to reply" goes to:', page.url().replace('http://localhost:5173', ''))
const opts = await page.locator('main.page').innerText()
console.log('  login page offers :', opts.includes('Sign in with ORCID') ? 'ORCID button' : 'no ORCID button',
            '|', opts.includes('Development mode') ? 'AND a dev form (local only)' : 'no dev form')
await page.screenshot({ path: process.env.SP + '/signedout_login.png' })
await browser.close()
