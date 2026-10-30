<script setup lang="ts">
import { computed } from 'vue'
import {
  activeFilterCount,
  emptyFilters,
  REWARD_FILTERS,
  RISK_OPTIONS,
  UTILITY_FILTERS,
  type FilterDef,
} from '../lib/filters'
import type { FilterState } from '../lib/types'

const props = defineProps<{ filters: FilterState }>()
const emit = defineEmits<{ (event: 'update:filters', value: FilterState): void }>()

const activeCount = computed(() => activeFilterCount(props.filters))

function toggle(key: string, group: 'reward' | 'utility') {
  const current = props.filters[group]
  const next = current.includes(key)
    ? current.filter((entry) => entry !== key)
    : [...current, key]
  emit('update:filters', { ...props.filters, [group]: next })
}

function setRisk(event: Event) {
  const value = (event.target as HTMLSelectElement).value as FilterState['risk']
  emit('update:filters', { ...props.filters, risk: value })
}

function reset() {
  emit('update:filters', emptyFilters())
}

function isOn(def: FilterDef, group: 'reward' | 'utility'): boolean {
  return props.filters[group].includes(def.key as string)
}
</script>

<template>
  <details class="filters" :open="activeCount > 0">
    <summary>
      Filters
      <span v-if="activeCount" class="count">{{ activeCount }}</span>
      <span class="filters-summary">reward · risk · utility</span>
    </summary>

    <div class="filters-body">
      <fieldset class="filter-group">
        <legend>Reward</legend>
        <div class="chips">
          <button
            v-for="def in REWARD_FILTERS"
            :key="def.key"
            type="button"
            class="chip"
            :class="{ 'is-on': isOn(def, 'reward') }"
            :aria-pressed="isOn(def, 'reward')"
            @click="toggle(def.key as string, 'reward')"
          >
            {{ def.label }}
          </button>
        </div>
      </fieldset>

      <fieldset class="filter-group">
        <legend>Risk</legend>
        <div class="chips">
          <label class="select-chip">
            <span class="sr-only">Safety on block</span>
            <select class="control control-small" :value="filters.risk" @change="setRisk">
              <option v-for="option in RISK_OPTIONS" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>
        </div>
      </fieldset>

      <fieldset class="filter-group">
        <legend>Utility</legend>
        <div class="chips">
          <button
            v-for="def in UTILITY_FILTERS"
            :key="def.key"
            type="button"
            class="chip"
            :class="{ 'is-on': isOn(def, 'utility') }"
            :aria-pressed="isOn(def, 'utility')"
            @click="toggle(def.key as string, 'utility')"
          >
            {{ def.label }}
          </button>
        </div>
      </fieldset>

      <button v-if="activeCount" type="button" class="link-button" @click="reset">
        Clear all filters
      </button>
    </div>
  </details>
</template>
