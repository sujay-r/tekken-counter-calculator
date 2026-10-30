<script setup lang="ts">
import { computed } from 'vue'
import { groupChars, searchMoves } from '../lib/search'
import { fmtBlock } from '../lib/format'
import type { OpponentMove } from '../lib/types'

const props = defineProps<{
  moves: OpponentMove[]
  char: string
  query: string
  selectedId: string | null
}>()

const emit = defineEmits<{
  (event: 'update:char', value: string): void
  (event: 'update:query', value: string): void
  (event: 'select', move: OpponentMove): void
}>()

const groups = computed(() => groupChars(props.moves))
const results = computed(() =>
  searchMoves(props.moves, props.query, props.char || null),
)

function onChar(event: Event) {
  emit('update:char', (event.target as HTMLSelectElement).value)
}

function onQuery(event: Event) {
  emit('update:query', (event.target as HTMLInputElement).value)
}
</script>

<template>
  <div class="picker">
    <label class="field">
      <span class="field-label">Character</span>
      <select :value="char" class="control" @change="onChar">
        <option value="">All characters</option>
        <optgroup
          v-for="group in groups"
          :key="group.letter"
          :label="`${group.letter} — ${group.chars.length}`"
        >
          <option v-for="name in group.chars" :key="name" :value="name">
            {{ name }}
          </option>
        </optgroup>
      </select>
    </label>

    <label class="field">
      <span class="field-label">
        Move search
        <span class="field-note">command or name</span>
      </span>
      <input
        :value="query"
        class="control"
        type="search"
        inputmode="search"
        autocomplete="off"
        autocapitalize="off"
        spellcheck="false"
        placeholder="f+4, Right Splits Kick, df+1…"
        @input="onQuery"
      />
    </label>

    <p v-if="!char" class="hint">
      Tip: include the character — “heihachi f+4” works without the selector.
    </p>

    <ul v-if="query.trim()" class="move-results" aria-label="Matching moves">
      <li v-for="move in results" :key="move.id">
        <button
          type="button"
          class="move-option"
          :class="{ 'is-selected': move.id === selectedId }"
          :aria-pressed="move.id === selectedId"
          @click="emit('select', move)"
        >
          <span class="mono move-input">{{ move.input }}</span>
          <span class="move-meta">
            <span class="move-name">{{ move.name || '—' }}</span>
            <span class="move-sub">
              {{ move.char }} · i{{ move.startupMin ?? '?' }}
              <template v-if="move.block != null">
                · {{ fmtBlock(move.block) }} on block
              </template>
            </span>
          </span>
        </button>
      </li>
      <li v-if="results.length === 0" class="empty">
        No move matches “{{ query }}”{{ char ? ` for ${char}` : '' }}.
      </li>
    </ul>
    <p v-else-if="char" class="hint">
      Type a command (e.g. <code>f+4</code>) or a move name.
    </p>
  </div>
</template>
