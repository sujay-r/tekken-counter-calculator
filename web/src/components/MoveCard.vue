<script setup lang="ts">
import { computed } from 'vue'
import { fmtBlock, fmtStartup, hitLevels } from '../lib/format'
import type { OpponentMove } from '../lib/types'

const props = defineProps<{ move: OpponentMove; reaction: number }>()

const blockLabel = computed(() => {
  if (props.move.block == null) return 'No block data'
  if (props.move.block_unblockable) return 'Unblockable'
  if (props.move.block >= 0) return `${fmtBlock(props.move.block)} · safe`
  return `${fmtBlock(props.move.block)} · punishable`
})

const whiffWindow = computed(() => {
  if (props.move.recovery == null) return '—'
  const threshold = props.move.recovery - props.reaction
  return threshold >= 10 ? `i${threshold}` : 'below i10'
})
</script>

<template>
  <article class="move-card">
    <header class="move-card-head">
      <div>
        <p class="move-card-char">{{ move.char }}</p>
        <h3 class="move-card-name">
          <span class="mono">{{ move.input }}</span>
          <span class="move-card-title">{{ move.name || '—' }}</span>
        </h3>
      </div>
      <div class="pill-row">
        <span v-if="move.isLauncher" class="pill pill-launcher">Launcher</span>
        <span v-if="move.homing" class="pill pill-homing">Homing</span>
        <span v-else class="pill pill-step">Sidesteppable</span>
      </div>
    </header>

    <dl class="stat-grid">
      <div class="stat-cell">
        <dt>Block</dt>
        <dd :class="{ 'is-neg': (move.block ?? 0) < 0 }">{{ blockLabel }}</dd>
      </div>
      <div class="stat-cell">
        <dt>Startup</dt>
        <dd>{{ fmtStartup(move) }}</dd>
      </div>
      <div class="stat-cell">
        <dt>Recovery</dt>
        <dd>{{ move.recovery != null ? `${move.recovery}f` : '—' }}</dd>
      </div>
      <div class="stat-cell">
        <dt>Hit level</dt>
        <dd>{{ hitLevels(move) }}</dd>
      </div>
      <div class="stat-cell">
        <dt>On CH</dt>
        <dd>
          {{ move.chFrames != null ? `${move.chFrames >= 0 ? '+' : ''}${move.chFrames}` : '—' }}
          <template v-if="move.chEffect"> · {{ move.chEffect }}</template>
        </dd>
      </div>
      <div class="stat-cell">
        <dt>Whiff window</dt>
        <dd>{{ whiffWindow }}</dd>
      </div>
    </dl>
  </article>
</template>
