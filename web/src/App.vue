<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import OpponentPicker from './components/OpponentPicker.vue'
import MoveCard from './components/MoveCard.vue'
import QueryControls from './components/QueryControls.vue'
import ResultsPanel from './components/ResultsPanel.vue'
import FrameDial from './components/FrameDial.vue'
import RecentLookups from './components/RecentLookups.vue'
import { opponentMoves, steveIndex } from './data'
import { computeScenarios } from './lib/engine'
import { applyFilters, emptyFilters } from './lib/filters'
import { fmtBlock } from './lib/format'
import { advantageToInput, fmtAdvantage } from './lib/frames'
import {
  addRecent,
  clearRecent,
  loadRecent,
  recentKey,
  saveRecent,
  type RecentItem,
  type RecentLookup,
  type RecentStorage,
} from './lib/recent'
import { sortMoves } from './lib/sort'
import type { FilterState, OpponentMove, SortMode } from './lib/types'

const DEFAULT_REACTION = steveIndex.meta.default_reaction ?? 15
const REACTION_KEY = 'steve-counter:reaction'

function getStorage(): RecentStorage | null {
  try {
    return window.localStorage
  } catch {
    // Storage unavailable (private mode) — every helper handles null.
    return null
  }
}

const storage = getStorage()

function loadReaction(): number {
  try {
    const raw = localStorage.getItem(REACTION_KEY)
    const parsed = raw == null ? Number.NaN : Number(raw)
    if (Number.isFinite(parsed)) return Math.min(40, Math.max(1, Math.round(parsed)))
  } catch {
    // Storage unavailable (private mode) — fall back to the index default.
  }
  return DEFAULT_REACTION
}

const char = ref('')
const query = ref('')
const selected = ref<OpponentMove | null>(null)
const sort = ref<SortMode>('recommended')
const filters = ref<FilterState>(emptyFilters())
const followupInput = ref<string | number>('')
const reaction = ref(loadReaction())
const dialInput = ref('')
const recents = ref<RecentLookup[]>(loadRecent(storage))

const moveById = new Map(opponentMoves.map((move) => [move.id, move]))

const reactionValue = computed(() => {
  const value = Math.round(Number(reaction.value))
  if (!Number.isFinite(value)) return DEFAULT_REACTION
  return Math.min(40, Math.max(1, value))
})

const followupValue = computed(() => {
  const raw = followupInput.value
  if (raw === '' || raw == null) return null
  const value = Math.round(Number(raw))
  if (!Number.isFinite(value)) return null
  return value > 0 && value <= 200 ? value : null
})

const dialEmpty = computed(() => dialInput.value.trim() === '')

watch(reactionValue, (value) => {
  try {
    localStorage.setItem(REACTION_KEY, String(value))
  } catch {
    // Ignore storage failures.
  }
})

watch(char, (value) => {
  if (selected.value && value && selected.value.char !== value) {
    selected.value = null
  }
})

const scenario = computed(() => {
  if (!selected.value) return null
  return computeScenarios(
    selected.value,
    steveIndex,
    reactionValue.value,
    followupValue.value,
  )
})

const blockResults = computed(() =>
  scenario.value ? sortMoves(applyFilters(scenario.value.block, filters.value), sort.value) : [],
)
const whiffResults = computed(() =>
  scenario.value ? sortMoves(applyFilters(scenario.value.whiff, filters.value), sort.value) : [],
)
const wsResults = computed(() =>
  scenario.value ? sortMoves(applyFilters(scenario.value.ws, filters.value), sort.value) : [],
)
const chResults = computed(() =>
  scenario.value ? sortMoves(applyFilters(scenario.value.ch, filters.value), sort.value) : [],
)

const blockNote = computed(() => {
  const move = selected.value
  if (!move) return ''
  if (move.block_unblockable) return 'Unblockable — nothing to punish on block.'
  if (move.block == null) return 'No block frame data for this move.'
  if (move.block >= 0) {
    return `${fmtBlock(move.block)} on block — Steve cannot punish this.`
  }
  return `${fmtBlock(move.block)} on block → punish with i${-move.block} or faster.`
})

const whiffNote = computed(() => {
  const move = selected.value
  if (!move) return ''
  if (move.recovery == null) return 'No recovery data for this move.'
  const threshold = move.recovery - reactionValue.value
  if (threshold < 10) {
    return `Recovery ${move.recovery}f − reaction ${reactionValue.value}f = ${threshold}f — no Steve move is fast enough.`
  }
  return `Recovery ${move.recovery}f − reaction ${reactionValue.value}f = i${threshold} window.`
})

const chNote = computed(() => {
  const move = selected.value
  if (!move) return ''
  if (move.block == null) return 'No block data — cannot compute a CH window.'
  const advantage = -move.block
  if (advantage <= 0) {
    return `Steve is ${signed(advantage)} after blocking — not plus, so there is no CH window.`
  }
  if (followupValue.value == null) {
    return `Steve is +${advantage} after blocking. Enter the follow-up's startup to test the trap.`
  }
  return `Steve is +${advantage}; opponent i${followupValue.value} → CH tools with ${advantage} < startup < ${advantage + followupValue.value}.`
})

const blockEmpty = computed(() => {
  const current = scenario.value
  const move = selected.value
  if (!current || !move) return ''
  if (current.block.length > 0) return 'No results match the active filters.'
  if (move.block_unblockable) return 'Unblockable — nothing to punish on block.'
  if (move.block == null) return 'No block data for this move.'
  if (move.block >= 0) {
    return `Safe on block (${fmtBlock(move.block)}) — no block punish exists.`
  }
  return `No Steve move fits i${-move.block} with the active filters.`
})

const whiffEmpty = computed(() => {
  const current = scenario.value
  const move = selected.value
  if (!current || !move) return ''
  if (current.whiff.length > 0) return 'No results match the active filters.'
  if (move.recovery == null) return 'No recovery data for this move.'
  const threshold = move.recovery - reactionValue.value
  if (threshold < 10) return `Whiff window is ${threshold}f — below Steve's fastest i10.`
  return `No Steve move fits i${threshold} with the active filters.`
})

const wsEmpty = computed(() => {
  const current = scenario.value
  if (!current) return ''
  if (current.ws.length > 0) return 'No results match the active filters.'
  return 'No while-standing punisher data available.'
})

const chEmpty = computed(() => {
  const current = scenario.value
  const move = selected.value
  if (!current || !move) return ''
  if (current.ch.length > 0) return 'No results match the active filters.'
  if (move.block == null) return 'No block data for this move.'
  if (move.block >= 0) return 'Not minus on block — no CH window.'
  if (followupValue.value == null) return 'Enter the follow-up startup above to test the trap.'
  return 'No CH launcher lands in that startup window.'
})

const recentItems = computed<RecentItem[]>(() =>
  recents.value.flatMap((entry): RecentItem[] => {
    if (entry.kind === 'move') {
      const move = moveById.get(entry.moveId)
      if (!move) return []
      const title = move.name ? `${move.char} · ${move.name}` : move.char
      return [
        {
          key: recentKey(entry),
          entry,
          label: move.input,
          sub: `${title} · react ${entry.reaction}f`,
        },
      ]
    }
    return [
      {
        key: recentKey(entry),
        entry,
        label: fmtAdvantage(entry.advantage),
        sub:
          entry.advantage < 0
            ? `block punish · react ${entry.reaction}f`
            : `frame check · react ${entry.reaction}f`,
      },
    ]
  }),
)

function signed(value: number): string {
  return value > 0 ? `+${value}` : String(value)
}

function recordRecent(entry: RecentLookup) {
  recents.value = addRecent(recents.value, entry)
  saveRecent(recents.value, storage)
}

function onFrameCommit(payload: { advantage: number; reaction: number }) {
  recordRecent({
    kind: 'frames',
    advantage: payload.advantage,
    reaction: payload.reaction,
  })
}

function setMove(move: OpponentMove) {
  selected.value = move
  // Keep the character selector in sync when a move was found globally.
  char.value = move.char
  // Collapse the result list so the counters are immediately visible.
  query.value = ''
}

function selectMove(move: OpponentMove) {
  setMove(move)
  recordRecent({
    kind: 'move',
    moveId: move.id,
    reaction: reactionValue.value,
  })
}

function clearSelection() {
  selected.value = null
  query.value = ''
}

function restoreRecent(entry: RecentLookup) {
  reaction.value = entry.reaction

  if (entry.kind === 'move') {
    const move = moveById.get(entry.moveId)
    if (!move) {
      // Stale id from an older data build — drop it rather than render a
      // lookup that cannot be restored.
      recents.value = recents.value.filter(
        (item) => recentKey(item) !== recentKey(entry),
      )
      saveRecent(recents.value, storage)
      return
    }
    setMove(move)
    void nextTick(() => {
      document
        .getElementById('move-results')
        ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
    return
  }

  dialInput.value = advantageToInput(entry.advantage)
  void nextTick(() => {
    document
      .getElementById('frame-dial-panel')
      ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

function clearRecents() {
  recents.value = []
  clearRecent(storage)
}

function bumpReaction(delta: number) {
  reaction.value = Math.min(40, Math.max(1, reactionValue.value + delta))
}

const dataDate = steveIndex.meta.generated.slice(0, 10)
</script>

<template>
  <div class="app">
    <header class="topbar">
      <div class="brand">
        <h1>Steve Counter</h1>
        <p class="brand-sub">Tekken 8 · block / whiff / CH</p>
      </div>

      <div class="reaction" role="group" aria-label="Whiff reaction time">
        <span class="reaction-label">Reaction</span>
        <button
          type="button"
          class="step"
          aria-label="Decrease reaction time"
          @click="bumpReaction(-1)"
        >
          −
        </button>
        <input
          v-model.number="reaction"
          class="reaction-input"
          type="number"
          inputmode="numeric"
          min="1"
          max="40"
          step="1"
          aria-label="Reaction time in frames"
        />
        <button
          type="button"
          class="step"
          aria-label="Increase reaction time"
          @click="bumpReaction(1)"
        >
          +
        </button>
        <span class="unit">f</span>
      </div>
    </header>

    <main class="main">
      <RecentLookups
        v-if="recentItems.length"
        :items="recentItems"
        @restore="restoreRecent"
        @clear="clearRecents"
      />

      <FrameDial
        v-model:value="dialInput"
        :reaction="reactionValue"
        @commit="onFrameCommit"
      />

      <section class="panel">
        <header class="panel-head">
          <h2>1 · Opponent move</h2>
          <p class="note">Pick a character, then search the command or move name.</p>
        </header>

        <OpponentPicker
          v-model:char="char"
          v-model:query="query"
          :moves="opponentMoves"
          :selected-id="selected?.id ?? null"
          @select="selectMove"
        />

        <MoveCard v-if="selected" :move="selected" :reaction="reactionValue" />

        <button v-if="selected" type="button" class="link-button" @click="clearSelection">
          Clear move
        </button>
      </section>

      <template v-if="selected && scenario">
        <section class="panel query-panel" id="move-results">
          <header class="panel-head">
            <h2>2 · Steve counters</h2>
            <p class="note">Tap a sort; narrow with filters if the list is long.</p>
          </header>

          <QueryControls v-model:sort="sort" v-model:filters="filters" />

          <label class="field followup-field">
            <span class="field-label">
              Opponent follow-up
              <span class="field-note">optional · startup frames</span>
            </span>
            <input
              v-model="followupInput"
              class="control"
              type="number"
              inputmode="numeric"
              min="1"
              max="99"
              placeholder="e.g. 13"
            />
          </label>
          <p class="hint" aria-live="polite">{{ chNote }}</p>
        </section>

        <ResultsPanel
          title="Block punish"
          tone="block"
          :note="blockNote"
          :moves="blockResults"
          :total="scenario.block.length"
          :empty="blockEmpty"
        />

        <ResultsPanel
          title="Whiff punish"
          tone="whiff"
          :note="whiffNote"
          :moves="whiffResults"
          :total="scenario.whiff.length"
          :empty="whiffEmpty"
        />

        <ResultsPanel
          v-if="scenario.isHigh"
          title="Duck → WS punish"
          tone="ws"
          note="High attack — duck it, then punish from while standing."
          :moves="wsResults"
          :total="scenario.ws.length"
          :empty="wsEmpty"
        />

        <ResultsPanel
          title="CH trap"
          tone="ch"
          :note="chNote"
          :moves="chResults"
          :total="scenario.ch.length"
          :empty="chEmpty"
        />
      </template>

      <p v-else-if="dialEmpty" class="empty-state">
        Search for an opponent move to see Steve's block, whiff and CH counters.
      </p>
    </main>

    <footer class="footer">
      <p>Offline-ready · frame data {{ dataDate }} · Steve only</p>
    </footer>
  </div>
</template>
