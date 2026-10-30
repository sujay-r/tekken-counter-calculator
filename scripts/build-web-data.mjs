#!/usr/bin/env node
/**
 * Build the slim browser data files from the canonical pipeline output.
 *
 * Inputs (committed, produced by the Python precompute):
 *   data/moves.clean.json   ~9.6 MB, every character, every move
 *   data/steve_index.json   precomputed Steve lookup tables
 *
 * Outputs (committed, imported by Vite — no runtime fetch):
 *   web/src/data/opponents.json
 *   web/src/data/steve_index.json
 *
 * The opponent index keeps only the fields the query UI reads. Steve is
 * dropped: this is an opponent lookup, and Steve's own data ships in full
 * via steve_index.json.
 *
 * Run: node scripts/build-web-data.mjs
 */
import { readFile, writeFile, mkdir, stat } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const SRC_MOVES = resolve(ROOT, 'data/moves.clean.json')
const SRC_INDEX = resolve(ROOT, 'data/steve_index.json')
const OUT_DIR = resolve(ROOT, 'web/src/data')

/** First segment of the Cargo id is the character/state-group prefix. */
function charOf(id) {
  const at = id.indexOf('-')
  return at === -1 ? id : id.slice(0, at)
}

function tagList(tags) {
  if (!tags) return []
  return String(tags)
    .split(/[,\s]+/)
    .map((t) => t.trim().toLowerCase())
    .filter(Boolean)
}

function hasHomingTag(tags) {
  const list = tagList(tags)
  return list.includes('hom') || list.includes('homing') || list.includes('hmg')
}

const HTML_ENTITIES = {
  '&amp;': '&',
  '&lt;': '<',
  '&gt;': '>',
  '&quot;': '"',
  '&#039;': "'",
  '&#39;': "'",
  '&nbsp;': ' ',
}

/** Scraped names contain HTML entities and, rarely, raw markup. */
function cleanName(name) {
  if (!name) return ''
  let text = String(name).replace(
    /&(?:amp|lt|gt|quot|#0?39|nbsp);/gi,
    (entity) => HTML_ENTITIES[entity.toLowerCase()] ?? entity,
  )
  if (/[<>]/.test(text)) {
    text = text
      .replace(/<[^>]*>/g, ' ')
      .replace(/^\s*\*+\s*/gm, '')
      .replace(/\s+/g, ' ')
      .trim()
  }
  return text
}

const raw = JSON.parse(await readFile(SRC_MOVES, 'utf8'))
if (!Array.isArray(raw)) throw new Error('moves.clean.json must be an array')

const moves = []
for (const m of raw) {
  const char = charOf(m.id)
  if (char === 'Steve') continue

  const startup = Array.isArray(m.startup) && m.startup.length > 0 ? m.startup[0] : null
  const ch = m.ch ?? null

  // Falsy optional fields are omitted (not set to null/false). The UI reads
  // them with `??`, so absence means "no/unknown" and the file stays ~1 MB.
  const move = {
    id: m.id,
    char,
    input: m.input ?? '',
    target: Array.isArray(m.target) ? m.target : [],
  }
  const name = cleanName(m.name)
  if (name) move.name = name
  if (startup?.min != null) move.startupMin = startup.min
  if (startup?.max != null) move.startupMax = startup.max
  if (m.block != null) move.block = m.block
  if (m.block_unblockable || m.categories?.unblockable) move.block_unblockable = true
  if (m.recovery != null) move.recovery = m.recovery
  if (m.categories?.homing || hasHomingTag(m.tags)) move.homing = true
  if (ch?.frames != null) move.chFrames = ch.frames
  if (ch?.effect) move.chEffect = ch.effect
  if (m.categories?.launcher) move.isLauncher = true
  moves.push(move)
}

const payload = {
  generated: new Date().toISOString(),
  count: moves.length,
  moves,
}
// Compact (no indentation) — this file is a build artifact for the browser.
await mkdir(OUT_DIR, { recursive: true })
const outOpponents = resolve(OUT_DIR, 'opponents.json')
await writeFile(outOpponents, JSON.stringify(payload), 'utf8')

// Copy the canonical Steve index verbatim so the browser bundle cannot drift
// from the file the Python tests cover.
const indexText = await readFile(SRC_INDEX, 'utf8')
const outIndex = resolve(OUT_DIR, 'steve_index.json')
await writeFile(outIndex, indexText, 'utf8')

const [oppSize, idxSize] = await Promise.all([stat(outOpponents), stat(outIndex)])
const kb = (n) => `${(n / 1024).toFixed(1)} KB`
console.log(`opponents.json: ${moves.length} moves, ${kb(oppSize.size)}`)
console.log(`steve_index.json: ${kb(idxSize.size)}`)
