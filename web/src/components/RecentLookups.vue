<script setup lang="ts">
import type { RecentItem, RecentLookup } from '../lib/recent'

defineProps<{ items: RecentItem[] }>()
const emit = defineEmits<{
  (event: 'restore', entry: RecentLookup): void
  (event: 'clear'): void
}>()
</script>

<template>
  <section class="panel recents" aria-label="Recent lookups">
    <header class="recents-head">
      <h2>Recent</h2>
      <button type="button" class="link-button recents-clear" @click="emit('clear')">
        Clear all
      </button>
    </header>

    <div class="recent-chips">
      <button
        v-for="item in items"
        :key="item.key"
        type="button"
        class="recent-chip"
        :aria-label="`Restore ${item.label}: ${item.sub}`"
        @click="emit('restore', item.entry)"
      >
        <span class="recent-label mono">{{ item.label }}</span>
        <span class="recent-sub">{{ item.sub }}</span>
      </button>
    </div>
  </section>
</template>
