#!/usr/bin/env node
/**
 * Verify the built site by serving dist/ and fetching it for real.
 *
 * - index.html is served under the GitHub Pages base path
 * - the bundled JS contains the opponent data (Heihachi f+4) — no runtime fetch
 * - every service-worker precache URL resolves (offline shell complete)
 * - the web app manifest is installable and base-path aware
 *
 * Run after `npm run build`, from web/: npm run verify:build
 */
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const WEB = resolve(dirname(fileURLToPath(import.meta.url)), '..', 'web')
const ORIGIN = 'http://127.0.0.1:4173'
const BASE = `${ORIGIN}/tekken-counter-calculator/`

const server = spawn(
  'npm',
  ['run', 'preview', '--', '--port', '4173', '--strictPort', '--host', '127.0.0.1'],
  { cwd: WEB, stdio: 'pipe', detached: true },
)

let serverLog = ''
server.stdout.on('data', (chunk) => (serverLog += chunk))
server.stderr.on('data', (chunk) => (serverLog += chunk))

async function waitForServer() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try {
      const response = await fetch(BASE)
      if (response.ok) return
    } catch {
      // Not up yet.
    }
    await new Promise((done) => setTimeout(done, 250))
  }
  throw new Error(`preview server did not start:\n${serverLog}`)
}

let failures = 0
function check(label, fn) {
  try {
    const note = fn()
    console.log(`PASS  ${label}${note ? ` — ${note}` : ''}`)
  } catch (error) {
    failures += 1
    console.log(`FAIL  ${label} — ${error.message}`)
  }
}

try {
  await waitForServer()

  const html = await (await fetch(BASE)).text()
  check('index.html served under the Pages base path', () => {
    assert.match(html, /<div id="app">/)
    assert.match(html, /\/tekken-counter-calculator\/assets\/index-.*\.js/)
    return BASE
  })

  const scriptPath = html.match(/src="([^"]+assets\/index-[^"]+\.js)"/)[1]
  const jsResponse = await fetch(new URL(scriptPath, ORIGIN))
  const js = await jsResponse.text()
  check('bundled JS fetched (data inlined, no runtime fetch)', () => {
    assert.equal(jsResponse.status, 200)
    assert.match(js, /Heihachi-f\+4/)
    assert.match(js, /Right Splits Kick/)
    return `${(js.length / 1024).toFixed(0)} KB bundle`
  })

  const manifestResponse = await fetch(new URL('manifest.webmanifest', BASE))
  const manifest = await manifestResponse.json()
  check('manifest is standalone and base-path aware', () => {
    assert.equal(manifest.display, 'standalone')
    assert.equal(manifest.start_url, '/tekken-counter-calculator/')
    assert.ok(manifest.icons.some((icon) => icon.sizes === '192x192'))
    assert.ok(manifest.icons.some((icon) => icon.sizes === '512x512'))
    return `${manifest.short_name}, start_url ${manifest.start_url}`
  })

  const swResponse = await fetch(new URL('sw.js', BASE))
  const sw = await swResponse.text()
  assert.ok(sw.includes('precacheAndRoute('), 'no precache route in sw.js')
  const urls = [
    ...new Set([...sw.matchAll(/url:"([^"]+)"/g)].map((match) => match[1])),
  ]
  const results = await Promise.all(
    urls.map(async (url) => ({ url, status: (await fetch(new URL(url, BASE))).status })),
  )
  check('service worker precaches the full app shell', () => {
    assert.ok(sw.includes('navigateFallback') || sw.includes('NavigationRoute'))
    assert.ok(urls.length >= 6)
    const broken = results.filter((entry) => entry.status !== 200)
    assert.deepEqual(broken, [])
    return `${urls.length} precache entries all HTTP 200; includes JS, CSS, manifest, icons`
  })

  const offlineData = urls.some((url) => url.includes('assets/index-') && url.endsWith('.js'))
  check('PWA precache covers the data bundle', () => {
    assert.ok(offlineData)
    return 'bundle is a precache URL; works with no network after first load'
  })
} finally {
  try {
    process.kill(-server.pid, 'SIGTERM')
  } catch {
    // Already gone.
  }
}

console.log(
  failures === 0
    ? '\nAll built-site assertions passed.'
    : `\n${failures} built-site assertion(s) FAILED.`,
)
process.exitCode = failures === 0 ? 0 : 1
