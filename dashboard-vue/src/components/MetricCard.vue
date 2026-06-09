<template>
  <div class="glass-panel metric-card animate-fade-in">
    <div class="card-header">
      <span class="card-title">{{ title }}</span>
      <div class="card-icon" :class="themeClass">
        <slot name="icon"></slot>
      </div>
    </div>
    
    <div class="card-body">
      <span class="card-value">{{ formattedValue }}</span>
      <span class="card-unit" v-if="unit">{{ unit }}</span>
    </div>

    <div class="card-footer" v-if="hasFooter">
      <slot name="footer"></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  value: {
    type: [Number, String],
    required: true
  },
  unit: {
    type: String,
    default: ''
  },
  theme: {
    type: String,
    default: 'indigo' // indigo, emerald, amber, rose, cyan
  },
  hasFooter: {
    type: Boolean,
    default: false
  }
})

const formattedValue = computed(() => {
  if (typeof props.value === 'number') {
    // If integer, don't show decimals, else show 2 decimals
    return Number.isInteger(props.value) ? props.value.toString() : props.value.toFixed(2)
  }
  return props.value
})

const themeClass = computed(() => `theme-${props.theme}`)
</script>

<style scoped>
.metric-card {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 120px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.card-title {
  font-size: 0.875rem;
  color: var(--text-secondary);
  font-weight: 500;
  letter-spacing: 0.025em;
}

.card-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.05);
}

.card-body {
  display: flex;
  align-items: baseline;
}

.card-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.025em;
}

.card-unit {
  font-size: 0.875rem;
  color: var(--text-muted);
  margin-left: 0.35rem;
  font-weight: 500;
}

.card-footer {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  font-size: 0.75rem;
  color: var(--text-secondary);
}

/* Theme color modifications */
.theme-indigo {
  color: #818cf8;
  background: rgba(99, 102, 241, 0.15) !important;
}
.theme-emerald {
  color: #34d399;
  background: rgba(16, 185, 129, 0.15) !important;
}
.theme-amber {
  color: #fbbf24;
  background: rgba(245, 158, 11, 0.15) !important;
}
.theme-rose {
  color: #f87171;
  background: rgba(239, 68, 68, 0.15) !important;
}
.theme-cyan {
  color: #22d3ee;
  background: rgba(6, 182, 212, 0.15) !important;
}
</style>
