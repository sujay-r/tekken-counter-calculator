<script setup lang="ts">
import { computed } from 'vue'
import type { CounterMove } from '../lib/types'

const props = defineProps<{
  title: string
  note?: string
  moves: CounterMove[]
  total: number
  empty: string
  tone: 'block' | 'whiff' | 'ws' | 'ch'
}>()

const filtered = computed(() => props.moves.length !== props.total)

function safetyClass(move: CounterMove): string {
  if (move.safety === 'SAFE') return 'safe'
  if (move.safety === 'PUNISHABLE') return 'unsafe'
  return 'semi'
}

function safetyLabel(move: CounterMove): string {
  if (move.safety === 'SAFE') return 'safe'
  if (move.safety === 'PUNISHABLE') return 'punishable'
  if (move.safety === 'SEMI') return 'semi-safe'
  return '—'
}
</script>

<template>
  <section class="panel results" :class="`tone-${tone}`">
    <header class="panel-head">
      <h2>
        {{ title }}
        <span class="count">
          {{ moves.length }}<template v-if="filtered"> / {{ total }}</template>
        </span>
      </h2>
      <p v-if="note" class="note">{{ note }}</p>
    </header>

    <ul v-if="moves.length" class="result-list">
      <li v-for="move in moves" :key="move.id" class="result">
        <div class="result-main">
          <span class="mono result-input">{{ move.input }}</span>
          <span class="result-name">{{ move.name }}</span>
        </div>

        <div class="result-stats">
          <span class="stat"><b>i{{ move.startup_min ?? '?' }}</b> start</span>
          <span class="stat"><b>{{ move.damage }}</b> dmg</span>
          <span class="stat" :class="`safety-${safetyClass(move)}`">
            {{ safetyLabel(move) }}
          </span>
        </div>

        <div class="badges">
          <span v-if="move.ws" class="badge badge-ws">WS</span>
          <span v-if="move.launcher" class="badge badge-launcher">Launcher</span>
          <span v-if="move.ch_launcher" class="badge badge-ch">CH launch</span>
          <span v-if="move.downed" class="badge">Knockdown</span>
          <span v-if="move.stagger" class="badge">Stagger</span>
          <span v-if="move.wall_crush" class="badge">Wall crush</span>
          <span v-if="move.powercrush" class="badge">Powercrush</span>
          <span v-if="move.high_crush" class="badge">High crush</span>
          <span v-if="move.low_crush" class="badge">Low crush</span>
          <span v-if="move.homing" class="badge">Homing</span>
        </div>
      </li>
    </ul>

    <p v-else class="empty">{{ empty }}</p>
  </section>
</template>
