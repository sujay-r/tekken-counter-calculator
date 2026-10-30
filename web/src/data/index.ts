import steveIndexJson from './steve_index.json'
import opponentsJson from './opponents.json'
import type { OpponentIndex, SteveIndex } from '../lib/types'

// Static imports: Vite inlines both JSON files into the JS bundle, so the
// query works offline with no runtime fetch of a large payload.
export const steveIndex = steveIndexJson as unknown as SteveIndex
export const opponents = opponentsJson as unknown as OpponentIndex
export const opponentMoves = opponents.moves
