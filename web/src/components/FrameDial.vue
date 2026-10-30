<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import QueryControls from './QueryControls.vue'
import ResultsPanel from './ResultsPanel.vue'
import { steveIndex } from '../data'
import { lookupAdvantage } from '../lib/engine'
import { applyFilters, emptyFilters } from '../lib/filters'
import {
  fmtAdvantage,
  parseAdvantage,
  type FrameLookup,
} from '../lib/frames'
import { sortMoves } from '../lib/sort'
import type { FilterState, SortMode } from '../lib/types'

const props = defineProps<{ value: string; reaction: number }>()
const emit = defineEmits<{
  (event: 'update:value', value: string): void
  (event: 'commit', payload: { advantage: number; reaction: number }): void
}>()

const QUICK_PICKS = [-10, -12, -13, -15, -20, 5] as const

const sort = ref<SortMode>('recommended')
const filters = ref<FilterState>(emptyFilters())

const parsed = computed(() => parseAdvantage(props.value))
const lookup = computed<FrameLookup>(() =>
  lookupAdvantage(parsed.value, steveIndex),
)
const showResults = computed(
  () => lookup.value.kind === 'punishable' || lookup.value.kind === 'capped',
)
const results = computed(() =>
  sortMoves(applyFilters(lookup.value.moves, filters.value), sort.value),
)

const message = computed(() => {
  const result = lookup.value
  switch (result.kind) {
    case 'empty':
      return 'Enter a frame number — or use move search below.'
    case 'invalid':
      return 'Not a frame number — try −13, 13 or +5.'
    case 'advantage': {
      const advantage = result.advantage ?? 0
      return advantage > 0
        ? `Not punishable — you're at advantage (${fmtAdvantage(advantage)}).`
        : 'Not punishable — 0 on block. Nobody is at advantage.'
    }
    case 'below_min':
      return `${fmtAdvantage(result.advantage ?? 0)} on block — nothing punishes it. Steve's fastest move is i10.`
    case 'punishable':
      return `${fmtAdvantage(result.advantage ?? 0)} on block → punish with i${-(
        result.advantage ?? 0
      )} or faster.`
    case 'capped':
      return `${fmtAdvantage(result.advantage ?? 0)} on block — the table caps at −30; showing i30 and faster (a conservative floor).`
  }
  return ''
})

const statusClass = computed(() => {
  switch (lookup.value.kind) {
    case 'advantage':
      return 'is-good'
    case 'punishable':
      return 'is-bad'
    case 'capped':
      return 'is-warn'
    default:
      return 'is-muted'
  }
})

const resultNote = computed(() => {
  const result = lookup.value
  if (result.kind === 'capped') {
    return `Table caps at −30; showing i30 and faster. ${result.ids.length} options before filters.`
  }
  return `${result.ids.length} options with startup i${result.tableFrame} or faster.`
})

const emptyMessage = computed(() => {
  const result = lookup.value
  if (result.moves.length > 0) return ''
  if (result.ids.length > 0) return 'No Steve move matches the active filters.'
  return 'No Steve punisher found in the table.'
})

let commitTimer: ReturnType<typeof setTimeout> | null = null

function clearTimer() {
  if (commitTimer != null) {
    clearTimeout(commitTimer)
    commitTimer = null
  }
}

function emitCommit() {
  clearTimer()
  const current = parsed.value
  if (current.status === 'ok') {
    emit('commit', {
      advantage: current.advantage,
      reaction: props.reaction,
    })
  }
}

watch(parsed, (current) => {
  clearTimer()
  // Only auto-record once a two-digit punish value settles; blur/Enter and
  // quick picks record immediately.
  if (current.status === 'ok' && Math.abs(current.advantage) >= 10) {
    commitTimer = setTimeout(emitCommit, 900)
  }
})

onBeforeUnmount(clearTimer)

function onInput(event: Event) {
  emit('update:value', (event.target as HTMLInputElement).value)
}

function setPick(value: number) {
  emit('update:value', String(value))
  emit('commit', { advantage: value, reaction: props.reaction })
}

function clearInput() {
  clearTimer()
  emit('update:value', '')
}
</script>

<template>
  <section class="panel dial-panel" id="frame-dial-panel">
    <header class="panel-head dial-head">
      <div>
        <h2>Frame check</h2>
        <p class="note">Type the number the game shows on block.</p>
      </div>
      <button
        v-if="props.value.trim()"
        type="button"
        class="link-button dial-clear"
        @click="clearInput"
      >
        Clear
      </button>
    </header>

    <label class="field dial-field">
      <span class="field-label">
        Opponent's frame advantage
        <span class="field-note">minus = punishable</span>
      </span>
      <input
        id="frame-dial"
        class="dial-input"
        type="text"
        inputmode="tel"
        autocomplete="off"
        autocapitalize="off"
        spellcheck="false"
        enterkeyhint="done"
        placeholder="−13"
        :value="props.value"
        :aria-invalid="lookup.kind === 'invalid'"
        aria-describedby="dial-help dial-status"
        @input="onInput"
        @keydown.enter.prevent="emitCommit"
        @blur="emitCommit"
      />
    </label>

    <p id="dial-help" class="dial-help">
      No sign means disadvantage: <b>13</b> = <b>−13</b>. Use <b>+5</b> for
      advantage.
    </p>

    <div class="quick-picks" role="group" aria-label="Quick frame picks">
      <button
        v-for="pick in QUICK_PICKS"
        :key="pick"
        type="button"
        class="quick-pick mono"
        @click="setPick(pick)"
      >
        {{ fmtAdvantage(pick) }}
      </button>
    </div>

    <p id="dial-status" class="dial-status" :class="statusClass" aria-live="polite">
      {{ message }}
    </p>
  </section>

  <template v-if="showResults">
    <section class="panel query-panel">
      <header class="panel-head">
        <h2>Steve counters</h2>
        <p class="note">Tap a sort; narrow with filters if the list is long.</p>
      </header>
      <QueryControls v-model:sort="sort" v-model:filters="filters" />
    </section>

    <ResultsPanel
      title="Block punish"
      tone="block"
      :note="resultNote"
      :moves="results"
      :total="lookup.ids.length"
      :empty="emptyMessage"
    />
  </template>
</template>
