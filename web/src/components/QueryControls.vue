<script setup lang="ts">
import FilterBar from './FilterBar.vue'
import { SORT_OPTIONS } from '../lib/sort'
import type { FilterState, SortMode } from '../lib/types'

const props = defineProps<{ sort: SortMode; filters: FilterState }>()
const emit = defineEmits<{
  (event: 'update:sort', value: SortMode): void
  (event: 'update:filters', value: FilterState): void
}>()
</script>

<template>
  <div class="query-controls">
    <div class="sort-row" role="group" aria-label="Sort results">
      <span class="sort-label">Sort</span>
      <button
        v-for="option in SORT_OPTIONS"
        :key="option.value"
        type="button"
        class="sort-button"
        :class="{ 'is-on': props.sort === option.value }"
        :aria-pressed="props.sort === option.value"
        @click="emit('update:sort', option.value)"
      >
        {{ option.label }}
      </button>
    </div>

    <FilterBar
      :filters="props.filters"
      @update:filters="emit('update:filters', $event)"
    />
  </div>
</template>
