/**
 * Frame-advantage dial parsing and result shape.
 *
 * The practice-mode display shows the opponent's advantage directly, e.g.
 * "−13" or "+5". Parsing is deliberately lenient: the common punish case is
 * a bare positive number ("13"), which means 13 frames of disadvantage.
 */
import type { CounterMove } from './types'

export type ParsedAdvantage =
  | { status: 'empty' }
  | { status: 'invalid' }
  | { status: 'ok'; advantage: number }

/** All the dash-like characters a phone keyboard or paste may produce. */
const MINUSES = /[\u2212\u2010-\u2015\uFE63\uFF0D]/g

/**
 * Parse "-13", "−13" (U+2212), "13", "+5", " 13 " into a signed advantage.
 * Negative means the opponent is minus (Steve can punish); positive means
 * the opponent is plus. A bare number is disadvantage.
 */
export function parseAdvantage(raw: string): ParsedAdvantage {
  const cleaned = raw.replace(MINUSES, '-').replace(/\s+/g, '')
  if (!cleaned) return { status: 'empty' }

  const match = /^([+-]?)(\d+)$/.exec(cleaned)
  if (!match) return { status: 'invalid' }

  const magnitude = Number(match[2])
  if (!Number.isSafeInteger(magnitude)) return { status: 'invalid' }
  if (magnitude === 0) return { status: 'ok', advantage: 0 }

  const sign = match[1]
  return { status: 'ok', advantage: sign === '+' ? magnitude : -magnitude }
}

/** Display form: +5, −13, 0 (uses a true minus sign). */
export function fmtAdvantage(value: number): string {
  if (value > 0) return `+${value}`
  if (value < 0) return `−${Math.abs(value)}`
  return '0'
}

/** Value to put back into the input when restoring a recent lookup. */
export function advantageToInput(value: number): string {
  return value > 0 ? `+${value}` : String(value)
}

export type FrameLookupKind =
  | 'empty'
  | 'invalid'
  | 'advantage'
  | 'below_min'
  | 'punishable'
  | 'capped'

/** A completed dial lookup, including the joined Steve moves. */
export interface FrameLookup {
  kind: FrameLookupKind
  /** Signed advantage: -13 means the opponent is -13. */
  advantage: number | null
  /** Raw ids from punish[tableFrame], before filters/sorting. */
  ids: string[]
  moves: CounterMove[]
  /** True when A > 30 and the i30 row was used as a conservative floor. */
  capped: boolean
  /** The punish-table row actually read (10..30), if any. */
  tableFrame: number | null
}
