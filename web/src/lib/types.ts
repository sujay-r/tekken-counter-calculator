/** Types shared by the query UI. Mirrors the JSON written by build-web-data.mjs. */

export interface SteveMove {
  input: string
  name: string
  startup_min: number | null
  startup_max: number | null
  damage: number
  block: number | null
  recovery: number | null
  launcher: boolean
  ch_launcher: boolean
  downed: boolean
  stagger: boolean
  wall_crush: boolean
  guard_recover: boolean
  safety: 'SAFE' | 'SEMI' | 'PUNISHABLE' | null
  homing: boolean
  high_crush: boolean
  low_crush: boolean
  powercrush: boolean
}

export interface SteveIndex {
  meta: {
    default_reaction: number
    generated: string
    move_count: number
  }
  moves: Record<string, SteveMove>
  punish: Record<string, string[]>
  whiff: Record<string, string[]>
  launchers: string[]
  ch_launchers: string[]
  downed: string[]
  stagger: string[]
  wall_crush: string[]
  ws_punishers: string[]
  by_startup: Record<string, string[]>
}

/** A slim opponent move from opponents.json. Optional fields are omitted when empty. */
export interface OpponentMove {
  id: string
  char: string
  input: string
  target: string[]
  name?: string
  startupMin?: number
  startupMax?: number
  block?: number
  block_unblockable?: boolean
  recovery?: number
  homing?: boolean
  chFrames?: number
  chEffect?: string
  isLauncher?: boolean
}

export interface OpponentIndex {
  generated: string
  count: number
  moves: OpponentMove[]
}

export type SortMode = 'recommended' | 'max_damage' | 'fastest_startup'

export type RiskFilter = 'any' | 'safe' | 'semi' | 'punishable'

export interface FilterState {
  reward: string[]
  utility: string[]
  risk: RiskFilter
}

/** A Steve move joined from an id, plus UI-only derived flags. */
export interface CounterMove extends SteveMove {
  id: string
  ws: boolean
}

export interface Scenario {
  block: CounterMove[]
  whiff: CounterMove[]
  ws: CounterMove[]
  ch: CounterMove[]
  blockAdvantage: number | null
  whiffThreshold: number | null
  isHigh: boolean
  sidesteppable: boolean
}
