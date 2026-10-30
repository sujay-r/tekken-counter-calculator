import type { OpponentMove } from './types'

/** Signed notation from the move owner's perspective (-13, +4, 0). */
export function fmtBlock(block: number | null | undefined): string {
  if (block == null) return '—'
  return block > 0 ? `+${block}` : String(block)
}

export function fmtStartup(move: OpponentMove): string {
  if (move.startupMin == null) return '?'
  if (move.startupMax != null && move.startupMax !== move.startupMin) {
    return `i${move.startupMin}–${move.startupMax}`
  }
  return `i${move.startupMin}`
}

export function capitalise(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase()
}

export function hitLevels(move: OpponentMove): string {
  return move.target.length ? move.target.join(' / ') : '—'
}
