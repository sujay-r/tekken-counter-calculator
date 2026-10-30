#!/usr/bin/env node
/**
 * Verify the frame-advantage dial and recent-lookup logic.
 *
 * Imports the same TS modules the Vue app uses (Node 24 strips types), so the
 * assertions cover the real implementation rather than a copy.
 *
 * Run from web/: npm run verify
 */
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { lookupAdvantage } from '../web/src/lib/engine.ts'
import { fmtAdvantage, parseAdvantage } from '../web/src/lib/frames.ts'
import {
  addRecent,
  clearRecent,
  loadRecent,
  normalizeRecent,
  parseRecentJson,
  RECENT_LIMIT,
  recentKey,
  saveRecent,
} from '../web/src/lib/recent.ts'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const index = JSON.parse(
  await readFile(resolve(ROOT, 'web/src/data/steve_index.json'), 'utf8'),
)

const lookup = (raw) => lookupAdvantage(parseAdvantage(raw), index)
const startupOf = (id) => index.moves[id].startup_min

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

check('dial parser is lenient and bare numbers mean disadvantage', () => {
  assert.deepEqual(parseAdvantage('-13'), { status: 'ok', advantage: -13 })
  assert.deepEqual(parseAdvantage('−13'), { status: 'ok', advantage: -13 })
  assert.deepEqual(parseAdvantage('13'), { status: 'ok', advantage: -13 })
  assert.deepEqual(parseAdvantage(' +5 '), { status: 'ok', advantage: 5 })
  assert.deepEqual(parseAdvantage('0'), { status: 'ok', advantage: 0 })
  assert.deepEqual(parseAdvantage(''), { status: 'empty' })
  assert.deepEqual(parseAdvantage('   '), { status: 'empty' })
  assert.deepEqual(parseAdvantage('abc'), { status: 'invalid' })
  assert.deepEqual(parseAdvantage('1.5'), { status: 'invalid' })
  assert.equal(fmtAdvantage(-13), '−13')
  assert.equal(fmtAdvantage(5), '+5')
  return '−13 / 13 / +5 / 0 parsed; junk rejected'
})

check('A = 13 → includes b+1 (i13)', () => {
  const result = lookup('13')
  assert.equal(result.kind, 'punishable')
  assert.equal(result.tableFrame, 13)
  assert.ok(result.ids.includes('Steve-b+1'), 'b+1 missing')
  assert.ok(result.moves.some((move) => move.id === 'Steve-b+1'))
  assert.ok(result.ids.every((id) => startupOf(id) <= 13))
  return `${result.ids.length} ids, all startup <= 13, includes b+1`
})

check('A = 10 → includes 1,2,1,2', () => {
  const result = lookup('10')
  assert.equal(result.kind, 'punishable')
  assert.ok(result.ids.includes('Steve-1,2,1,2'), '1,2,1,2 missing')
  assert.ok(result.ids.every((id) => startupOf(id) <= 10))
  return `${result.ids.length} ids, includes 1,2,1,2 (i10)`
})

check('A = 12 → only startup <= 12', () => {
  const result = lookup('12')
  assert.equal(result.kind, 'punishable')
  assert.deepEqual(result.ids, index.punish['12'])
  assert.ok(result.ids.length > 0)
  assert.ok(result.ids.every((id) => startupOf(id) <= 12))
  return `${result.ids.length} ids, max startup i${Math.max(...result.ids.map(startupOf))}`
})

check('A = 9 → empty (below Steve\'s i10)', () => {
  const result = lookup('9')
  assert.equal(result.kind, 'below_min')
  assert.deepEqual(result.ids, [])
  assert.deepEqual(result.moves, [])
  assert.equal(result.capped, false)
  return '0 punishers; below i10'
})

check('A = 31 → punish["30"] and flagged capped', () => {
  const result = lookup('31')
  assert.equal(result.kind, 'capped')
  assert.equal(result.capped, true)
  assert.equal(result.tableFrame, 30)
  assert.deepEqual(result.ids, index.punish['30'])
  assert.ok(result.ids.every((id) => startupOf(id) <= 30))
  return `${result.ids.length} ids equals punish["30"]; capped=true`
})

check('A = 0 and positive advantage → empty, not punishable', () => {
  const zero = lookup('0')
  const plus = lookup('+5')
  assert.equal(zero.kind, 'advantage')
  assert.equal(plus.kind, 'advantage')
  assert.deepEqual(zero.ids, [])
  assert.deepEqual(plus.ids, [])
  assert.deepEqual(zero.moves, [])
  assert.deepEqual(plus.moves, [])
  assert.equal(zero.capped, false)
  assert.equal(plus.capped, false)
  return '0 and +5 return no punishers'
})

check('recent lookups de-duplicate by identity and move to front', () => {
  let list = []
  list = addRecent(list, { kind: 'frames', advantage: -13, reaction: 15 })
  list = addRecent(list, { kind: 'frames', advantage: -13, reaction: 20 })
  assert.equal(list.length, 1)
  assert.deepEqual(list[0], { kind: 'frames', advantage: -13, reaction: 20 })

  const move = { kind: 'move', moveId: 'Heihachi-f+4', reaction: 15 }
  list = addRecent(list, move)
  list = addRecent(list, move)
  assert.equal(list.length, 2)
  assert.deepEqual(list[0], move)
  assert.equal(recentKey(list[0]), 'move:Heihachi-f+4')
  assert.equal(recentKey(list[1]), 'frames:-13')
  return '2 identities after 4 inserts; newest first'
})

check(`recent lookups cap at ${RECENT_LIMIT}, most-recent-first`, () => {
  let list = []
  for (let frames = 1; frames <= 20; frames += 1) {
    list = addRecent(list, {
      kind: 'frames',
      advantage: -frames,
      reaction: 15,
    })
  }
  assert.equal(list.length, RECENT_LIMIT)
  assert.deepEqual(
    list.map((entry) => entry.advantage),
    Array.from({ length: RECENT_LIMIT }, (_, i) => -(20 - i)),
  )
  return `${list.length} entries: ${list[0].advantage} … ${list.at(-1).advantage}`
})

check('malformed / old JSON loads as empty, never throws', () => {
  assert.deepEqual(parseRecentJson('{not json'), [])
  assert.deepEqual(parseRecentJson('null'), [])
  assert.deepEqual(parseRecentJson('{"kind":"frames"}'), [])
  assert.deepEqual(parseRecentJson('[]'), [])

  const mixed = parseRecentJson(
    JSON.stringify([
      { kind: 'frames', advantage: -13, reaction: 15, extra: 'dropped' },
      { kind: 'move', moveId: 42, reaction: 15 },
      { kind: 'frames', advantage: '-9', reaction: 15 },
      null,
    ]),
  )
  assert.deepEqual(mixed, [{ kind: 'frames', advantage: -13, reaction: 15 }])
  assert.deepEqual(normalizeRecent({ kind: 'frames' }), [])
  return 'junk discarded; valid rows keep only kind/value/reaction'
})

check('storage unavailable or throwing → safe fallback', () => {
  const throwing = {
    getItem() {
      throw new Error('private mode')
    },
    setItem() {
      throw new Error('private mode')
    },
    removeItem() {
      throw new Error('private mode')
    },
  }
  assert.deepEqual(loadRecent(null), [])
  assert.deepEqual(loadRecent(throwing), [])
  assert.equal(saveRecent([], null), false)
  assert.equal(saveRecent([], throwing), false)
  clearRecent(null)
  clearRecent(throwing)
  return 'null + throwing storage both degrade to empty/no-op'
})

console.log(
  failures === 0
    ? '\nAll dial and recent-lookup assertions passed.'
    : `\n${failures} assertion(s) FAILED.`,
)
process.exitCode = failures === 0 ? 0 : 1
