/**
 * Recent lookups — pure normalisation plus defensive storage helpers.
 *
 * Everything that can be unit-tested lives here without touching the DOM.
 * The App passes in localStorage (or null when unavailable); every access is
 * wrapped so private mode / malformed JSON can never break rendering.
 */

export const RECENT_KEY = 'tcc.recent.v1'
export const RECENT_LIMIT = 15

export type RecentLookup =
  | { kind: 'move'; moveId: string; reaction: number }
  | { kind: 'frames'; advantage: number; reaction: number }

export interface RecentItem {
  key: string
  entry: RecentLookup
  label: string
  sub: string
}

/** The small slice of Storage we use, so tests can pass fakes. */
export interface RecentStorage {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
  removeItem(key: string): void
}

const MIN_REACTION = 1
const MAX_REACTION = 40

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
}

function validReaction(value: unknown): number | null {
  if (typeof value !== 'number' || !Number.isFinite(value)) return null
  const rounded = Math.round(value)
  return rounded >= MIN_REACTION && rounded <= MAX_REACTION ? rounded : null
}

export function recentKey(entry: RecentLookup): string {
  return entry.kind === 'move' ? `move:${entry.moveId}` : `frames:${entry.advantage}`
}

/**
 * Validate and de-duplicate a value loaded from storage. Unknown fields are
 * dropped, so we never persist or render more than a lookup needs.
 */
export function normalizeRecent(value: unknown): RecentLookup[] {
  if (!Array.isArray(value)) return []

  const out: RecentLookup[] = []
  const seen = new Set<string>()

  for (const raw of value) {
    const record = asRecord(raw)
    if (!record) continue

    const reaction = validReaction(record.reaction)
    if (reaction == null) continue

    let entry: RecentLookup | null = null
    if (record.kind === 'move') {
      if (typeof record.moveId !== 'string' || !record.moveId.trim()) continue
      entry = { kind: 'move', moveId: record.moveId, reaction }
    } else if (record.kind === 'frames') {
      if (
        typeof record.advantage !== 'number' ||
        !Number.isSafeInteger(record.advantage)
      ) {
        continue
      }
      entry = {
        kind: 'frames',
        advantage: record.advantage === 0 ? 0 : record.advantage,
        reaction,
      }
    }

    if (!entry) continue
    const key = recentKey(entry)
    if (seen.has(key)) continue
    seen.add(key)
    out.push(entry)
    if (out.length === RECENT_LIMIT) break
  }

  return out
}

/** Malformed or old JSON returns an empty list; it never throws. */
export function parseRecentJson(raw: string | null): RecentLookup[] {
  if (raw == null || raw === '') return []
  try {
    return normalizeRecent(JSON.parse(raw) as unknown)
  } catch {
    return []
  }
}

/** Most-recent-first, de-duplicated by lookup identity, capped at 15. */
export function addRecent(
  list: RecentLookup[],
  entry: RecentLookup,
): RecentLookup[] {
  const normalized = normalizeRecent(list)
  const [next] = normalizeRecent([entry])
  if (!next) return normalized

  const key = recentKey(next)
  return [
    next,
    ...normalized.filter((item) => recentKey(item) !== key),
  ].slice(0, RECENT_LIMIT)
}

export function loadRecent(storage?: RecentStorage | null): RecentLookup[] {
  try {
    return parseRecentJson(storage?.getItem(RECENT_KEY) ?? null)
  } catch {
    return []
  }
}

/** Returns false when storage is missing or refuses the write. */
export function saveRecent(
  list: RecentLookup[],
  storage?: RecentStorage | null,
): boolean {
  try {
    if (!storage) return false
    storage.setItem(RECENT_KEY, JSON.stringify(normalizeRecent(list)))
    return true
  } catch {
    return false
  }
}

export function clearRecent(storage?: RecentStorage | null): void {
  try {
    storage?.removeItem(RECENT_KEY)
  } catch {
    // Storage unavailable — nothing to clear.
  }
}
