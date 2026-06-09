<template>
  <div class="overview-container animate-fade-in">
    <!-- Header Summary KPIs -->
    <div class="kpi-grid">
      <MetricCard title="覆盖省级行政区" :value="31" unit="个" theme="indigo">
        <template #icon>
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-6 h-6"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>
        </template>
      </MetricCard>
      
      <MetricCard title="设定聚类类别数 (K)" :value="5" unit="类" theme="cyan">
        <template #icon>
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-6 h-6"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/><path d="M12 6v6l4 2"/></svg>
        </template>
      </MetricCard>

      <MetricCard title="全国人均口粮均值" :value="averageFoodGrain" unit="kg/人/年" theme="emerald">
        <template #icon>
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-6 h-6"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
        </template>
      </MetricCard>

      <MetricCard title="全国人均饲料粮均值" :value="averageFeedGrain" unit="kg/人/年" theme="amber">
        <template #icon>
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-6 h-6"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>
        </template>
      </MetricCard>
    </div>

    <!-- Main Workspace -->
    <div class="workspace-grid">
      <!-- Map Visualisation Column -->
      <div class="map-column">
        <div class="map-card-wrapper">
          <ChinaMap 
            v-if="provinces.length > 0"
            :provincesData="provinces"
            activeExperiment="M0"
            visualType="cluster"
            labelMode="none"
            title="M0 四域联合聚类空间分布"
            subtitle="颜色表示省份所属类别，鼠标悬停可查看省份与类别信息"
            @select-province="handleSelectProvince"
          />
          <div v-else class="map-skeleton skeleton glass-panel"></div>
        </div>
      </div>

      <!-- Detail Info Panel Column -->
      <div class="detail-column">
        <div class="glass-panel detail-panel">
          <!-- Default State (No selection) -->
          <div v-if="!selectedProvince" class="empty-detail">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="w-12 h-12 empty-icon"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
            <h4>请点击地图省份查看详细画像</h4>
            <p>可直接查看该省的分类属性、数据偏离度及联合聚类主要特征。</p>
            
            <div class="summary-list">
              <div class="summary-item">
                <span class="label">类0北方增量区:</span>
                <span class="val">6个省份</span>
              </div>
              <div class="summary-item">
                <span class="label">类1都市高收入区:</span>
                <span class="val">3个省份</span>
              </div>
              <div class="summary-item">
                <span class="label">类2中西部平缓区:</span>
                <span class="val">11个省份</span>
              </div>
              <div class="summary-item">
                <span class="label">类3东南沿海肉食区:</span>
                <span class="val">10个省份</span>
              </div>
              <div class="summary-item">
                <span class="label">类4高原高消耗区:</span>
                <span class="val">1个省份</span>
              </div>
            </div>
          </div>

          <!-- Active Province Details -->
          <div v-else class="province-detail animate-fade-in">
            <div class="detail-header">
              <div>
                <h2>{{ selectedProvince.name }}</h2>
                <span class="province-code">行政区划代码: {{ selectedProvince.code }}</span>
              </div>
              <button class="btn-close" @click="selectedProvince = null">&times;</button>
            </div>

            <div class="detail-section">
              <h4 class="section-title">聚类分群标签</h4>
              <div class="badge-row">
                <span class="cluster-badge" :style="{ backgroundColor: getClusterColor(selectedProvince.cluster_m0) }">
                  类别 {{ selectedProvince.cluster_m0 }}
                </span>
                <span class="stability-badge" :class="getStabilityClass(selectedProvince.stability)">
                  稳定性: {{ selectedProvince.stability }}/6
                </span>
              </div>
              <p class="cluster-desc">{{ selectedProvince.cluster_label }}</p>
            </div>

            <div class="detail-section">
              <h4 class="section-title">核心指标对比 (最新年值)</h4>
              <div class="metric-comparison-list">
                <!-- Pop Density -->
                <div class="comparison-item">
                  <div class="comp-label-row">
                    <span>人口密度</span>
                    <span class="comp-val">{{ selectedProvince.metrics.pop_density.toFixed(1) }} <small>人/km²</small></span>
                  </div>
                  <div class="progress-container">
                    <div class="progress-bar" :style="{ width: getProgressPercent(selectedProvince.metrics.pop_density, maxPopDensity) + '%' }"></div>
                  </div>
                  <div class="comp-sub">全国均值: {{ averagePopDensity.toFixed(1) }} 人/km²</div>
                </div>

                <!-- Disposable Income -->
                <div class="comparison-item">
                  <div class="comp-label-row">
                    <span>可支配收入</span>
                    <span class="comp-val">{{ selectedProvince.metrics.disposable_income.toLocaleString() }} <small>元</small></span>
                  </div>
                  <div class="progress-container">
                    <div class="progress-bar income" :style="{ width: getProgressPercent(selectedProvince.metrics.disposable_income, maxIncome) + '%' }"></div>
                  </div>
                  <div class="comp-sub">全国均值: {{ averageIncome.toFixed(0) }} 元</div>
                </div>

                <!-- Food Grain -->
                <div class="comparison-item">
                  <div class="comp-label-row">
                    <span>人均口粮</span>
                    <span class="comp-val">{{ selectedProvince.metrics.food_grain.toFixed(1) }} <small>kg/人</small></span>
                  </div>
                  <div class="progress-container">
                    <div class="progress-bar food" :style="{ width: getProgressPercent(selectedProvince.metrics.food_grain, maxFoodGrain) + '%' }"></div>
                  </div>
                  <div class="comp-sub">全国均值: {{ averageFoodGrain.toFixed(1) }} kg/人</div>
                </div>

                <!-- Feed Grain -->
                <div class="comparison-item">
                  <div class="comp-label-row">
                    <span>人均饲料粮</span>
                    <span class="comp-val">{{ selectedProvince.metrics.feed_grain.toFixed(1) }} <small>kg/人</small></span>
                  </div>
                  <div class="progress-container">
                    <div class="progress-bar feed" :style="{ width: getProgressPercent(selectedProvince.metrics.feed_grain, maxFeedGrain) + '%' }"></div>
                  </div>
                  <div class="comp-sub">全国均值: {{ averageFeedGrain.toFixed(1) }} kg/人</div>
                </div>
              </div>
            </div>

            <div class="detail-section" v-if="stabilityDetail">
              <h4 class="section-title">实验稳定性分析</h4>
              <p class="stability-text">{{ stabilityDetail }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import MetricCard from '@/components/MetricCard.vue'
import ChinaMap from '@/components/ChinaMap.vue'

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
const selectedProvince = ref<ProvinceData | null>(null)
const stabilityList = ref<any[]>([])

const fetchOverviewData = async () => {
  try {
    const [provRes, stabRes] = await Promise.all([
      axios.get('/api/provinces'),
      axios.get('/api/stability')
    ])
    provinces.value = provRes.data
    stabilityList.value = stabRes.data
  } catch (err) {
    console.error('Failed to fetch overview metrics:', err)
  }
}

onMounted(() => {
  fetchOverviewData()
})

const handleSelectProvince = (params: any) => {
  if (params && params.provData) {
    selectedProvince.value = params.provData
  }
}

// Averages computation
const averageFoodGrain = computed(() => {
  if (provinces.value.length === 0) return 0
  const sum = provinces.value.reduce((acc, p) => acc + p.metrics.food_grain, 0)
  return sum / provinces.value.length
})

const averageFeedGrain = computed(() => {
  if (provinces.value.length === 0) return 0
  const sum = provinces.value.reduce((acc, p) => acc + p.metrics.feed_grain, 0)
  return sum / provinces.value.length
})

const averageIncome = computed(() => {
  if (provinces.value.length === 0) return 0
  const sum = provinces.value.reduce((acc, p) => acc + p.metrics.disposable_income, 0)
  return sum / provinces.value.length
})

const averagePopDensity = computed(() => {
  if (provinces.value.length === 0) return 0
  const sum = provinces.value.reduce((acc, p) => acc + p.metrics.pop_density, 0)
  return sum / provinces.value.length
})

// Maximums for progress bars
const maxPopDensity = computed(() => {
  if (provinces.value.length === 0) return 1000
  return Math.max(...provinces.value.map(p => p.metrics.pop_density))
})

const maxIncome = computed(() => {
  if (provinces.value.length === 0) return 100000
  return Math.max(...provinces.value.map(p => p.metrics.disposable_income))
})

const maxFoodGrain = computed(() => {
  if (provinces.value.length === 0) return 200
  return Math.max(...provinces.value.map(p => p.metrics.food_grain))
})

const maxFeedGrain = computed(() => {
  if (provinces.value.length === 0) return 300
  return Math.max(...provinces.value.map(p => p.metrics.feed_grain))
})

const getProgressPercent = (value: number, max: number) => {
  if (max === 0) return 0
  return Math.min(100, Math.max(5, (value / max) * 100))
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

const stabilityDetail = computed(() => {
  if (!selectedProvince.value) return ''
  const item = stabilityList.value.find(s => s.code === selectedProvince.value?.code)
  return item ? item.detail : ''
})
</script>

<style scoped>
.overview-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  height: 100%;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.25rem;
}

.workspace-grid {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 1.5rem;
  align-items: stretch;
  flex: 1;
}

.map-column {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.controls-bar {
  padding: 0.75rem 1.25rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.control-group label {
  font-size: 0.825rem;
  color: var(--text-secondary);
  font-weight: 500;
}

.btn-group {
  display: flex;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 6px;
  padding: 2px;
  border: 1px solid var(--border-color);
}

.btn-group button {
  background: transparent;
  border: none;
  padding: 0.45rem 1rem;
  color: var(--text-secondary);
  font-size: 0.825rem;
  font-weight: 500;
  border-radius: 4px;
  cursor: pointer;
  transition: var(--transition-smooth);
}

.btn-group button.active {
  background: var(--color-primary);
  color: #fff;
}

.map-card-wrapper {
  flex: 1;
  min-height: 520px;
}

.map-skeleton {
  width: 100%;
  height: 100%;
}

.detail-panel {
  padding: 1.5rem;
  height: 100%;
  min-height: 520px;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.empty-detail {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  text-align: center;
  color: var(--text-secondary);
  padding: 2rem 0;
}

.empty-icon {
  color: var(--text-muted);
  margin-bottom: 1.25rem;
}

.empty-detail h4 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.empty-detail p {
  font-size: 0.825rem;
  max-width: 260px;
  margin-bottom: 2rem;
}

.summary-list {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  border-top: 1px solid var(--border-color);
  padding-top: 1.25rem;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  font-size: 0.775rem;
}

.summary-item .label {
  color: var(--text-secondary);
}

.summary-item .val {
  color: var(--text-primary);
  font-weight: 600;
}

.province-detail {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.75rem;
}

.detail-header h2 {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--text-primary);
}

.province-code {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.btn-close {
  background: transparent;
  border: none;
  font-size: 1.5rem;
  color: var(--text-muted);
  cursor: pointer;
  transition: var(--transition-smooth);
}

.btn-close:hover {
  color: var(--text-primary);
}

.detail-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.section-title {
  font-size: 0.825rem;
  text-transform: uppercase;
  color: var(--text-muted);
  font-weight: 600;
  letter-spacing: 0.05em;
}

.badge-row {
  display: flex;
  gap: 0.5rem;
}

.cluster-badge {
  padding: 0.25rem 0.65rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  color: #fff;
}

.stability-badge {
  padding: 0.25rem 0.65rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}

.stab-high {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
}
.stab-mid {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
}
.stab-low {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}

.cluster-desc {
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.4;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-color);
}

.metric-comparison-list {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.comparison-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.comp-label-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.825rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.comp-val {
  color: var(--text-primary);
  font-weight: 600;
}

.comp-val small {
  color: var(--text-muted);
  font-size: 0.7rem;
}

.progress-container {
  height: 6px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 3px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  border-radius: 3px;
  background: var(--color-primary);
}

.progress-bar.income { background: var(--color-info); }
.progress-bar.food { background: var(--color-success); }
.progress-bar.feed { background: var(--color-warning); }

.comp-sub {
  font-size: 0.725rem;
  color: var(--text-muted);
  text-align: right;
}

.stability-text {
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.4;
  background: rgba(99, 102, 241, 0.05);
  border: 1px solid rgba(99, 102, 241, 0.15);
  padding: 0.65rem 0.75rem;
  border-radius: 6px;
}
</style>
