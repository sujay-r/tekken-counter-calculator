/** Scope §7 taxonomy exposed as filters. */
import type { CounterMove, FilterState } from './types'

export interface FilterDef {
  key: keyof CounterMove
  label: string
  short: string
}

export const REWARD_FILTERS: FilterDef[] = [
  { key: 'launcher', label: 'Launcher', short: 'L' },
  { key: 'ch_launcher', label: 'CH launcher', short: 'CH' },
  { key: 'downed', label: 'Knockdown / oki', short: 'KD' },
  { key: 'stagger', label: 'Stagger', short: 'STG' },
  { key: 'wall_crush', label: 'Wall crush', short: 'WC' },
]

export const UTILITY_FILTERS: FilterDef[] = [
  { key: 'powercrush', label: 'Powercrush', short: 'PC' },
  { key: 'high_crush', label: 'High crush', short: 'HC' },
  { key: 'low_crush', label: 'Low crush', short: 'LC' },
  { key: 'homing', label: 'Homing', short: 'HM' },
]

export const RISK_OPTIONS: { value: FilterState['risk']; label: string }[] = [
  { value: 'any', label: 'Any safety' },
  { value: 'safe', label: 'Safe on block' },
  { value: 'semi', label: 'Semi-safe' },
  { value: 'punishable', label: 'Punishable' },
]

export function emptyFilters(): FilterState {
  return { reward: [], utility: [], risk: 'any' }
}

export function activeFilterCount(filters: FilterState): number {
  return filters.reward.length + filters.utility.length + (filters.risk === 'any' ? 0 : 1)
}

export function applyFilters(moves: CounterMove[], filters: FilterState): CounterMove[] {
  return moves.filter((move) => {
    for (const key of [...filters.reward, ...filters.utility]) {
      if (!move[key as keyof CounterMove]) return false
    }
    if (filters.risk === 'safe' && move.safety !== 'SAFE') return false
    if (filters.risk === 'semi' && move.safety !== 'SEMI') return false
    if (filters.risk === 'punishable' && move.safety !== 'PUNISHABLE') return false
    return true
  })
}
