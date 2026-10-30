/** Sort heuristics — mirrors src/tekken_counter/sort.py (Scope §8). */
import type { CounterMove, SortMode } from './types'

export const SORT_OPTIONS: { value: SortMode; label: string }[] = [
  { value: 'recommended', label: 'Recommended' },
  { value: 'max_damage', label: 'Max damage' },
  { value: 'fastest_startup', label: 'Fastest' },
]

const startup = (m: CounterMove): number => m.startup_min ?? 999
const byInput = (a: CounterMove, b: CounterMove): number => a.input.localeCompare(b.input)

export function sortRecommended(moves: CounterMove[]): CounterMove[] {
  return [...moves].sort(
    (a, b) =>
      Number(b.launcher) - Number(a.launcher) ||
      Number(b.ch_launcher) - Number(a.ch_launcher) ||
      Number(b.downed || b.stagger) - Number(a.downed || a.stagger) ||
      b.damage - a.damage ||
      startup(a) - startup(b) ||
      byInput(a, b),
  )
}

export function sortMaxDamage(moves: CounterMove[]): CounterMove[] {
  return [...moves].sort(
    (a, b) =>
      b.damage - a.damage ||
      Number(b.launcher) - Number(a.launcher) ||
      startup(a) - startup(b) ||
      byInput(a, b),
  )
}

export function sortFastestStartup(moves: CounterMove[]): CounterMove[] {
  return [...moves].sort(
    (a, b) => startup(a) - startup(b) || b.damage - a.damage || byInput(a, b),
  )
}

export function sortMoves(moves: CounterMove[], mode: SortMode): CounterMove[] {
  switch (mode) {
    case 'max_damage':
      return sortMaxDamage(moves)
    case 'fastest_startup':
      return sortFastestStartup(moves)
    case 'recommended':
    default:
      return sortRecommended(moves)
  }
}
