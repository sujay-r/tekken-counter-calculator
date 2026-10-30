/** Move search by command or move name, scoped to a character when chosen. */
import type { OpponentMove } from './types'

export interface MoveSearchResult {
  move: OpponentMove
  score: number
}

/** Characters that are state-group prefixes or non-roster buckets, not roster entries. */
export function isRosterChar(char: string): boolean {
  return char !== 'Generic' && char !== 'Steve' && !char.includes('.')
}

export function searchMoves(
  moves: OpponentMove[],
  query: string,
  char: string | null,
  limit = 40,
): OpponentMove[] {
  const q = query.trim().toLowerCase()
  if (!q) return []
  const tokens = q.split(/\s+/)
  const last = tokens[tokens.length - 1]

  // Typing a character name ("alisa 2,3,4") widens the search to all
  // characters even when the selector is still on someone else.
  const mentionsChar = [...new Set(moves.map((move) => move.char))]
    .filter(isRosterChar)
    .some((name) => q.includes(name.toLowerCase()))
  const scopedChar = mentionsChar ? null : char

  const scored: MoveSearchResult[] = []
  for (const move of moves) {
    if (scopedChar && move.char !== scopedChar) continue
    const input = move.input.toLowerCase()
    const name = (move.name ?? '').toLowerCase()
    const haystack = `${move.char} ${input} ${name} ${move.id}`.toLowerCase()
    if (!tokens.every((token) => haystack.includes(token))) continue

    let score = 10
    if (input === q) score = 100
    else if (input === last) score = 80
    else if (input.startsWith(last)) score = 60
    else if (name.includes(q)) score = 50
    else if (name.split(/\s+/).some((word) => word.startsWith(last))) score = 40

    scored.push({ move, score })
  }

  return scored
    .sort(
      (a, b) =>
        b.score - a.score ||
        (a.move.startupMin ?? 999) - (b.move.startupMin ?? 999) ||
        a.move.input.localeCompare(b.move.input),
    )
    .slice(0, limit)
    .map((entry) => entry.move)
}

export function groupChars(moves: OpponentMove[]): { letter: string; chars: string[] }[] {
  const chars = [...new Set(moves.map((m) => m.char))]
    .filter(isRosterChar)
    .sort((a, b) => a.localeCompare(b))
  const groups = new Map<string, string[]>()
  for (const char of chars) {
    const letter = char[0].toUpperCase()
    const bucket = groups.get(letter) ?? []
    bucket.push(char)
    groups.set(letter, bucket)
  }
  return [...groups.entries()].map(([letter, list]) => ({ letter, chars: list }))
}
