/**
 * Punish lookup — deliberately thin.
 *
 * All frame math is precomputed by the Python pipeline into
 * steve_index.json; this module only selects table rows and joins them to
 * Steve move details. The one runtime calculation is the CH-trade
 * inequality from Scope §6.3, which the scope explicitly leaves to the
 * browser.
 */
import type { FrameLookup, ParsedAdvantage } from './frames'
import type {
  CounterMove,
  OpponentMove,
  Scenario,
  SteveIndex,
  SteveMove,
} from './types'

export const PUNISH_MIN = 10
export const PUNISH_MAX = 30

export function clampPunishFrame(frame: number): number {
  return Math.min(PUNISH_MAX, Math.max(PUNISH_MIN, frame))
}

export function toCounterMove(id: string, index: SteveIndex): CounterMove | null {
  const move = index.moves[id]
  if (!move) return null
  return { id, ...move, ws: move.input.startsWith('WS.') }
}

function join(ids: string[] | undefined, index: SteveIndex): CounterMove[] {
  if (!ids) return []
  const out: CounterMove[] = []
  for (const id of ids) {
    const move = toCounterMove(id, index)
    if (move) out.push(move)
  }
  return out
}

/** Signed frame advantage from the opponent's perspective (-13 = punishable). */
export function blockAdvantage(move: OpponentMove): number | null {
  if (move.block == null) return null
  return -move.block
}

/**
 * Punishers for a signed opponent advantage (-13 = 13 frames of
 * disadvantage). Positive/zero means there is no block punish.
 */
export function advantagePunishIds(
  advantage: number,
  index: SteveIndex,
): string[] {
  if (!Number.isFinite(advantage) || advantage >= 0) return []
  const frames = Math.round(-advantage)
  if (frames < PUNISH_MIN) return []
  return index.punish[String(clampPunishFrame(frames))] ?? []
}

/** US1: block punish. `block < 0` means the opponent is punishable. */
export function blockPunishIds(move: OpponentMove, index: SteveIndex): string[] {
  if (move.block == null) return []
  return advantagePunishIds(move.block, index)
}

/**
 * Feature 1: direct frame-advantage lookup, sharing blockPunishIds' table
 * selection. A > 30 reads the i30 row and is explicitly flagged as capped.
 */
export function lookupAdvantage(
  parsed: ParsedAdvantage,
  index: SteveIndex,
): FrameLookup {
  if (parsed.status === 'empty' || parsed.status === 'invalid') {
    return {
      kind: parsed.status,
      advantage: null,
      ids: [],
      moves: [],
      capped: false,
      tableFrame: null,
    }
  }

  const advantage = parsed.advantage
  if (advantage >= 0) {
    return {
      kind: 'advantage',
      advantage,
      ids: [],
      moves: [],
      capped: false,
      tableFrame: null,
    }
  }

  const frames = Math.round(-advantage)
  if (frames < PUNISH_MIN) {
    return {
      kind: 'below_min',
      advantage,
      ids: [],
      moves: [],
      capped: false,
      tableFrame: null,
    }
  }

  const capped = frames > PUNISH_MAX
  const tableFrame = clampPunishFrame(frames)
  const ids = advantagePunishIds(advantage, index)
  return {
    kind: capped ? 'capped' : 'punishable',
    advantage,
    ids,
    moves: join(ids, index),
    capped,
    tableFrame,
  }
}

/**
 * US2: whiff punish at a user-tunable reaction time.
 *
 * whiff[R] holds Steve moves with startup <= R - defaultReaction, keyed by
 * the opponent's recovery R (not by "effective frames"). To evaluate a
 * custom reaction we ask the table for the recovery that yields the same
 * threshold: R = recovery - reaction + defaultReaction. Keys are dense for
 * every threshold that matters here (0–60), so the largest key <= R is exact.
 */
export function whiffPunishIds(
  move: OpponentMove,
  index: SteveIndex,
  reaction: number,
): string[] {
  if (move.recovery == null) return []
  const defaultReaction = index.meta.default_reaction ?? 15
  const safeReaction = Math.max(1, Math.round(reaction))
  const tableRecovery = move.recovery - safeReaction + defaultReaction

  let bestKey: string | null = null
  let bestValue = -Infinity
  for (const key of Object.keys(index.whiff)) {
    const value = Number(key)
    if (value <= tableRecovery && value > bestValue) {
      bestValue = value
      bestKey = key
    }
  }
  return bestKey ? (index.whiff[bestKey] ?? []) : []
}

/** US4a: high attacks can be ducked, so Steve gets his while-standing tools. */
export function wsPunishIds(move: OpponentMove, index: SteveIndex): string[] {
  return move.target.includes('HIGH') ? index.ws_punishers : []
}

/**
 * US3: CH frame trap. After blocking, Steve is A = -block frames plus.
 * A CH tool with startup S counter-hits their follow-up (startup So) iff
 * A < S < A + So.
 */
export function chTrapIds(
  move: OpponentMove,
  index: SteveIndex,
  followupStartup: number | null,
): string[] {
  if (move.block == null || move.block >= 0) return []
  if (followupStartup == null || followupStartup <= 0) return []
  const advantage = -move.block
  return index.ch_launchers.filter((id) => {
    const startup = index.moves[id]?.startup_min
    return (
      startup != null && startup > advantage && startup < advantage + followupStartup
    )
  })
}

export function computeScenarios(
  move: OpponentMove,
  index: SteveIndex,
  reaction: number,
  followupStartup: number | null,
): Scenario {
  const advantage = blockAdvantage(move)
  return {
    block: join(blockPunishIds(move, index), index),
    whiff: join(whiffPunishIds(move, index, reaction), index),
    ws: join(wsPunishIds(move, index), index),
    ch: join(chTrapIds(move, index, followupStartup), index),
    blockAdvantage: advantage,
    whiffThreshold: move.recovery == null ? null : move.recovery - reaction,
    isHigh: move.target.includes('HIGH'),
    sidesteppable: !move.homing,
  }
}

/** Only used by the verification script/tests. */
export function moveDetails(id: string, index: SteveIndex): SteveMove | undefined {
  return index.moves[id]
}
