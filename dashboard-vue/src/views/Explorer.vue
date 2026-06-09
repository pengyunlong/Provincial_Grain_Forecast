<template>
  <div class="explorer-container animate-fade-in">
    <!-- Header -->
    <div class="page-header glass-panel">
      <h1>原始明细数据浏览器</h1>
      <p>浏览、模糊检索及多维筛选31个省级行政区的核心人口、经济以及粮食供需最新年指标明细。</p>
    </div>

    <!-- Filters Bar -->
    <div class="filters-bar glass-panel">
      <div class="filter-group search-box">
        <label>模糊检索</label>
        <div class="input-wrapper">
          <input 
            type="text" 
            v-model="searchQuery" 
            placeholder="输入省份名称或区划代码..."
            @input="handleFilter"
          />
        </div>
      </div>

      <div class="filter-group">
        <label>主聚类类别 (M0)</label>
        <select v-model="clusterFilter" @change="handleFilter" class="glass-input">
          <option value="all">全部类别 (0-4)</option>
          <option value="0">类别 0 (北方粮食增量区)</option>
          <option value="1">类别 1 (直辖市都市群)</option>
          <option value="2">类别 2 (中西部平缓追赶区)</option>
          <option value="3">类别 3 (东南沿海发达区)</option>
          <option value="4">类别 4 (高原边疆消耗区)</option>
        </select>
      </div>

      <div class="filter-group">
        <label>稳定性排序</label>
        <select v-model="stabilityFilter" @change="handleFilter" class="glass-input">
          <option value="all">不限稳定性</option>
          <option value="high">高稳定性 (5-6)</option>
          <option value="mid">中等稳定性 (3-4)</option>
          <option value="low">低稳定性 (1-2)</option>
        </select>
      </div>

      <div class="results-counter">
        共找到 <strong>{{ filteredProvinces.length }}</strong> 条记录
      </div>
    </div>

    <!-- Table Grid -->
    <div class="table-card glass-panel">
      <div class="table-wrapper">
        <table class="explorer-table">
          <thead>
            <tr>
              <th @click="handleSort('name')" class="sortable">
                省份 <span class="sort-indicator">{{ getSortIcon('name') }}</span>
              </th>
              <th @click="handleSort('code')" class="sortable">
                代码 <span class="sort-indicator">{{ getSortIcon('code') }}</span>
              </th>
              <th @click="handleSort('cluster_m0')" class="sortable">
                分群类别 (M0) <span class="sort-indicator">{{ getSortIcon('cluster_m0') }}</span>
              </th>
              <th @click="handleSort('pop_density')" class="sortable numeric">
                人口密度 (人/km²) <span class="sort-indicator">{{ getSortIcon('pop_density') }}</span>
              </th>
              <th @click="handleSort('disposable_income')" class="sortable numeric">
                可支配收入 (元) <span class="sort-indicator">{{ getSortIcon('disposable_income') }}</span>
              </th>
              <th @click="handleSort('food_grain')" class="sortable numeric">
                年人均口粮 (kg) <span class="sort-indicator">{{ getSortIcon('food_grain') }}</span>
              </th>
              <th @click="handleSort('feed_grain')" class="sortable numeric">
                年人均饲料粮 (kg) <span class="sort-indicator">{{ getSortIcon('feed_grain') }}</span>
              </th>
              <th @click="handleSort('stability')" class="sortable numeric">
                稳定性评分 <span class="sort-indicator">{{ getSortIcon('stability') }}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="prov in sortedProvinces" :key="prov.code" class="table-row">
              <td>
                <div class="prov-name-cell">
                  <span class="color-dot" :style="{ backgroundColor: getClusterColor(prov.cluster_m0) }"></span>
                  <strong>{{ prov.name }}</strong>
                </div>
              </td>
              <td class="code-cell">{{ prov.code }}</td>
              <td>
                <span class="cluster-badge" :style="{ backgroundColor: getClusterColor(prov.cluster_m0) }">
                  类别 {{ prov.cluster_m0 }}
                </span>
              </td>
              <td class="numeric font-mono">{{ prov.metrics.pop_density.toFixed(1) }}</td>
              <td class="numeric font-mono">{{ prov.metrics.disposable_income.toLocaleString() }}</td>
              <td class="numeric font-mono">{{ prov.metrics.food_grain.toFixed(1) }}</td>
              <td class="numeric font-mono">{{ prov.metrics.feed_grain.toFixed(1) }}</td>
              <td>
                <span class="stab-bar-outer">
                  <span class="stab-bar-inner" :class="getStabilityClass(prov.stability)" :style="{ width: (prov.stability / 6 * 100) + '%' }"></span>
                  <span class="stab-num">{{ prov.stability }}/6</span>
                </span>
              </td>
            </tr>
            <tr v-if="filteredProvinces.length === 0">
              <td colspan="8" class="no-data-cell">
                <p>未找到匹配该筛选条件的省份数据</p>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'

interface ProvinceData {
  name: string
  code: string
  cluster_m0: number
  cluster_label: string
  stability: number
  metrics: {
    pop_density: number
    disposable_income: number
    food_grain: number
    feed_grain: number
  }
  labels: Record<string, number>
}

const provinces = ref<ProvinceData[]>([])
const searchQuery = ref('')
const clusterFilter = ref('all')
const stabilityFilter = ref('all')

// Sort states
const sortBy = ref('cluster_m0') // default sort key
const sortOrder = ref<'asc' | 'desc'>('asc')

const fetchProvinces = async () => {
  try {
    const response = await axios.get('/api/provinces')
    provinces.value = response.data
  } catch (err) {
    console.error('Failed to load explorer data:', err)
  }
}

onMounted(() => {
  fetchProvinces()
})

const handleFilter = () => {
  // trigger reactivity
}

const filteredProvinces = computed(() => {
  return provinces.value.filter(prov => {
    // 1. Search Query filter
    const matchesSearch = prov.name.includes(searchQuery.value) || prov.code.includes(searchQuery.value)
    
    // 2. Cluster Filter
    const matchesCluster = clusterFilter.value === 'all' || prov.cluster_m0.toString() === clusterFilter.value
    
    // 3. Stability Filter
    let matchesStability = true
    if (stabilityFilter.value === 'high') {
      matchesStability = prov.stability >= 5
    } else if (stabilityFilter.value === 'mid') {
      matchesStability = prov.stability >= 3 && prov.stability <= 4
    } else if (stabilityFilter.value === 'low') {
      matchesStability = prov.stability >= 1 && prov.stability <= 2
    }

    return matchesSearch && matchesCluster && matchesStability
  })
})

const sortedProvinces = computed(() => {
  const list = [...filteredProvinces.value]
  return list.sort((a, b) => {
    let aVal: any
    let bVal: any

    // Extract sort values
    if (sortBy.value === 'name' || sortBy.value === 'code' || sortBy.value === 'cluster_m0' || sortBy.value === 'stability') {
      aVal = a[sortBy.value as keyof ProvinceData]
      bVal = b[sortBy.value as keyof ProvinceData]
    } else {
      // Metric sort keys
      const metricKey = sortBy.value as 'pop_density' | 'disposable_income' | 'food_grain' | 'feed_grain'
      aVal = a.metrics[metricKey]
      bVal = b.metrics[metricKey]
    }

    // Sort comparison
    if (typeof aVal === 'string') {
      return sortOrder.value === 'asc' 
        ? aVal.localeCompare(bVal) 
        : bVal.localeCompare(aVal)
    } else {
      return sortOrder.value === 'asc' 
        ? aVal - bVal 
        : bVal - aVal
    }
  })
})

const handleSort = (key: string) => {
  if (sortBy.value === key) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortBy.value = key
    sortOrder.value = 'asc'
  }
}

const getSortIcon = (key: string) => {
  if (sortBy.value !== key) return '↕'
  return sortOrder.value === 'asc' ? '▲' : '▼'
}

const clusterColors = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ec4899']
const getClusterColor = (idx: number) => {
  return clusterColors[idx] || '#4b5563'
}

const getStabilityClass = (val: number) => {
  if (val >= 5) return 'stab-high'
  if (val >= 3) return 'stab-mid'
  return 'stab-low'
}
</script>

<style scoped>
.explorer-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  height: 100%;
}

.page-header {
  padding: 1.25rem 1.5rem;
}

.page-header h1 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.35rem;
}

.page-header p {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.filters-bar {
  padding: 1.25rem;
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
  align-items: flex-end;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.filter-group label {
  font-size: 0.825rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.search-box {
  flex: 1;
  min-width: 240px;
}

.input-wrapper {
  position: relative;
  width: 100%;
}

.input-wrapper input {
  width: 100%;
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  border-radius: 6px;
  outline: none;
  transition: var(--transition-smooth);
}

.input-wrapper input:focus {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-glow);
}

.glass-input {
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  border-radius: 6px;
  outline: none;
  min-width: 200px;
  cursor: pointer;
  transition: var(--transition-smooth);
}

.glass-input:focus {
  border-color: var(--color-primary);
}

.glass-input option {
  background-color: var(--bg-secondary);
  color: var(--text-primary);
}

.results-counter {
  font-size: 0.825rem;
  color: var(--text-secondary);
  margin-left: auto;
  align-self: center;
}

.table-card {
  padding: 0.5rem;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.table-wrapper {
  overflow-y: auto;
  flex: 1;
}

.explorer-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 0.85rem;
}

.explorer-table th {
  background: rgba(255, 255, 255, 0.02);
  padding: 0.9rem 1rem;
  color: var(--text-secondary);
  font-weight: 600;
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  z-index: 10;
}

.explorer-table th.sortable {
  cursor: pointer;
  user-select: none;
  transition: var(--transition-smooth);
}

.explorer-table th.sortable:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.04);
}

.explorer-table th.numeric, .explorer-table td.numeric {
  text-align: right;
}

.sort-indicator {
  font-size: 0.7rem;
  margin-left: 0.25rem;
  color: var(--text-muted);
}

.explorer-table td {
  padding: 0.85rem 1rem;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-secondary);
  vertical-align: middle;
}

.table-row {
  transition: var(--transition-smooth);
}

.table-row:hover {
  background: rgba(255, 255, 255, 0.015);
  color: var(--text-primary);
}

.prov-name-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.prov-name-cell .color-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.code-cell {
  color: var(--text-muted);
}

.cluster-badge {
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.725rem;
  font-weight: 600;
  color: #fff;
}

.font-mono {
  font-family: 'Fira Code', 'Courier New', Courier, monospace;
}

.stab-bar-outer {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100px;
}

.stab-bar-inner {
  height: 5px;
  border-radius: 3px;
  display: inline-block;
}

.stab-bar-inner.stab-high { background: var(--color-success); }
.stab-bar-inner.stab-mid { background: var(--color-warning); }
.stab-bar-inner.stab-low { background: var(--color-danger); }

.stab-num {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-weight: 500;
}

.no-data-cell {
  text-align: center;
  padding: 3rem 0;
  color: var(--text-muted);
}
</style>
