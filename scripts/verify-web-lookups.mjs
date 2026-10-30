#!/usr/bin/env node
/**
 * Verify the browser data path with the real engine functions.
 *
 * Imports web/src/lib/engine.ts directly (Node 24 strips TS types), loads the
 * slim opponent index and the copied Steve index, and rehearses the US1–US4
 * lookups. Exits non-zero on any failed assertion.
 *
 * Run from web/: npm run verify      (or: node scripts/verify-web-lookups.mjs)
 */
import assert from 'node:assert/strict'
import { readFile, stat } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  blockAdvantage,
  blockPunishIds,
  chTrapIds,
  toCounterMove,
  whiffPunishIds,
  wsPunishIds,
} from '../web/src/lib/engine.ts'
import { sortMoves } from '../web/src/lib/sort.ts'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const opponentsPath = resolve(ROOT, 'web/src/data/opponents.json')
const index = JSON.parse(await readFile(resolve(ROOT, 'web/src/data/steve_index.json'), 'utf8'))
const opponents = JSON.parse(await readFile(opponentsPath, 'utf8'))
const moves = opponents.moves

const findMove = (id) => {
  const move = moves.find((entry) => entry.id === id)
  assert.ok(move, `missing opponent move ${id}`)
  return move
}
const details = (ids) => ids.map((id) => {
  const move = toCounterMove(id, index)
  assert.ok(move, `id ${id} is missing from steve_index.moves`)
  return move
})
const maxStartup = (ids) => Math.max(...ids.map((id) => index.moves[id].startup_min))

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

const size = (await stat(opponentsPath)).size
const f4 = findMove('Heihachi-f+4')

check('slim opponent index shape', () => {
  assert.equal(opponents.count, moves.length)
  assert.equal(moves.length, 6247)
  assert.ok(size < 1.5 * 1024 * 1024, `opponents.json is ${size} bytes`)
  assert.equal(moves.filter((m) => m.char === 'Steve').length, 0)
  return `${moves.length} moves, ${(size / 1024).toFixed(1)} KB, no Steve rows`
})

check('Heihachi-f+4 parsed as expected', () => {
  assert.equal(f4.block, 4)
  assert.equal(f4.recovery, 27)
  assert.equal(f4.startupMin, 19)
  assert.deepEqual(f4.target, ['MID'])
  assert.equal(blockAdvantage(f4), -4)
  return `block +4, recovery 27, i19–20, MID`
})

check('Heihachi-f+4 → NO block punish (safe on block)', () => {
  const ids = blockPunishIds(f4, index)
  assert.deepEqual(ids, [])
  return `${ids.length} punishers; block is +4`
})

check('Heihachi-f+4 → whiff punishers, max startup i12', () => {
  const ids = whiffPunishIds(f4, index, 15)
  assert.ok(ids.length > 0, 'expected whiff punishers')
  assert.equal(maxStartup(ids), 12)
  const slowest = details(ids).filter((m) => (m.startup_min ?? 0) > 12)
  assert.equal(slowest.length, 0)
  const names = details(ids).slice(0, 3).map((m) => m.input).join(', ')
  return `${ids.length} ids, all <= i12 (recovery 27 - reaction 15 = i12 window); first: ${names}`
})

check('Heihachi-f+4 → reaction 20 removes the whiff window', () => {
  const ids = whiffPunishIds(f4, index, 20)
  assert.deepEqual(ids, [])
  return `0 ids at recovery 27 - reaction 20 = 7f`
})

check('Heihachi-f+4 → linear, sidesteppable', () => {
  assert.equal(Boolean(f4.homing), false)
  return 'homing=false'
})

const minus13 = moves.find((m) => m.block === -13)
const minus10 = moves.find((m) => m.block === -10)
const high = moves.find((m) => m.target.includes('HIGH'))
const minus1 = moves.find((m) => m.block === -1)

check('-13 opponent move → block punishers include b+1', () => {
  const ids = blockPunishIds(minus13, index)
  assert.ok(ids.includes('Steve-b+1'), 'b+1 missing')
  return `${minus13.id}: ${ids.length} punishers, includes b+1 (i13)`
})

check('-10 opponent move → block punishers include 1,2,1,2', () => {
  const ids = blockPunishIds(minus10, index)
  assert.ok(ids.includes('Steve-1,2,1,2'), '1,2,1,2 missing')
  return `${minus10.id}: ${ids.length} punishers, includes 1,2,1,2 (i10)`
})

check('HIGH opponent move → WS punishers non-empty', () => {
  const ids = wsPunishIds(high, index)
  assert.ok(ids.length > 0)
  assert.deepEqual(ids, index.ws_punishers)
  return `${high.id} (${high.input}): ${ids.length} WS tools (${details(ids).slice(0, 3).map((m) => m.input).join(', ')})`
})

check('CH trap: -1 blocked, opponent i13 → b+1 counter-hits', () => {
  const ids = chTrapIds(minus1, index, 13)
  assert.ok(ids.includes('Steve-b+1'), 'b+1 missing from CH trap')
  return `${minus1.id}: A=+1, 1 < 13 < 14 → ${details(ids).map((m) => m.input).join(', ')}`
})

check('Recommended sort mirrors sort.py priority', () => {
  const sorted = sortMoves(details(blockPunishIds(minus13, index)), 'recommended')
  assert.ok(sorted[0].launcher || sorted[0].ch_launcher)
  assert.ok(sorted[0].damage >= 0)
  return `first: ${sorted[0].input} (launcher=${sorted[0].launcher}, CH=${sorted[0].ch_launcher}, dmg=${sorted[0].damage})`
})

console.log(
  failures === 0
    ? '\nAll data-path assertions passed.'
    : `\n${failures} assertion(s) FAILED.`,
)
process.exitCode = failures === 0 ? 0 : 1
