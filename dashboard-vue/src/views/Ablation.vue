<template>
  <div class="ablation-container animate-fade-in">
    <!-- Header -->
    <div class="page-header glass-panel">
      <h1>消融实验与鲁棒性分析</h1>
      <p>通过逐一移除“人口、经济、口粮、饲料粮”单域指标并重新等权聚类（对照组实验 C1-C5），评估主实验模型 (M0) 的鲁棒性与各特征域的敏感度贡献。</p>
    </div>

    <!-- Layout Grid -->
    <div class="ablation-grid">
      <!-- Quality Metrics Table & Scheme Details -->
      <div class="table-card glass-panel">
        <div class="card-header">
          <h3>实验方案及质量评估对比</h3>
        </div>
        
        <div class="table-wrapper">
          <table class="metrics-table">
            <thead>
              <tr>
                <th>方案</th>
                <th>保留指标域</th>
                <th>轮廓系数</th>
                <th>CH 得分</th>
                <th>ARI 一致性</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="item in ablationData.metrics" 
                :key="item.id"
                :class="{ active: selectedScheme === item.id }"
                @click="selectedScheme = item.id"
              >
                <td>
                  <div class="scheme-name-cell">
                    <span class="scheme-id" :class="item.id.toLowerCase()">{{ item.id }}</span>
                    <span class="scheme-name">{{ item.name }}</span>
                  </div>
                </td>
                <td class="domains-cell">{{ item.domains }}</td>
                <td class="num-cell">{{ item.silhouette.toFixed(3) }}</td>
                <td class="num-cell">{{ item.ch_score.toFixed(1) }}</td>
                <td class="num-cell">
                  <span :class="getAriClass(item.ari)">{{ item.ari.toFixed(3) }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Selected Scheme Info -->
        <div class="scheme-info-box animate-fade-in" v-if="activeMetric">
          <div class="info-header">
            <h4>{{ activeMetric.id }} - {{ activeMetric.name }}</h4>
            <span class="info-domains">指标构成: {{ activeMetric.domains }}</span>
          </div>
          
          <div class="sizes-summary">
            <h5>各类别省份分布数量</h5>
            <div class="sizes-bar-row">
              <div 
                v-for="(size, idx) in activeMetric.sizes" 
                :key="idx" 
                class="size-bar-segment"
                :style="{ 
                  width: getSegmentPercent(size) + '%',
                  backgroundColor: clusterColors[idx]
                }"
                :title="`类别 ${idx}: ${size}个省份`"
              >
                <span class="seg-label" v-if="size > 0">C{{ idx }}: {{ size }}</span>
              </div>
            </div>
            <div class="sizes-legend">
              <div class="legend-dot-item" v-for="(size, idx) in activeMetric.sizes" :key="idx">
                <span class="dot" :style="{ backgroundColor: clusterColors[idx] }"></span>
                <span>类{{ idx }}: <strong>{{ size }}</strong> 个省份</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Live Map Comparison Visualizer -->
      <div class="map-card glass-panel">
        <div class="map-card-header">
          <h3>空间漂移实时视察地图</h3>
          <p>当前地图着色方案对应: <strong>{{ activeMetric?.name }}</strong></p>
        </div>
        <div class="map-render-area">
          <ChinaMap 
            v-if="provinces.length > 0"
            :provincesData="provinces"
            :activeExperiment="selectedScheme"
            visualType="cluster"
            labelMode="none"
            emphasizeStable
            title="消融方案空间分布"
            subtitle="深色省份表示六组实验分类完全稳定"
          />
          <div v-else class="map-skeleton skeleton"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import ChinaMap from '@/components/ChinaMap.vue'

interface AblationMetric {
  id: string
  name: string
  domains: string
  silhouette: number
  ch_score: number
  ari: number
  sizes: number[]
}

interface AblationResponse {
  metrics: AblationMetric[]
  provinces_labels: Record<string, Record<string, number>>
}

const selectedScheme = ref('M0')
const ablationData = ref<AblationResponse>({ metrics: [], provinces_labels: {} })
const provinces = ref<any[]>([])

const fetchAblationData = async () => {
  try {
    const [abRes, provRes] = await Promise.all([
      axios.get('/api/ablation'),
      axios.get('/api/provinces')
    ])
    ablationData.value = abRes.data
    provinces.value = provRes.data
  } catch (err) {
    console.error('Failed to fetch ablation data:', err)
  }
}

onMounted(() => {
  fetchAblationData()
})

const activeMetric = computed(() => {
  return ablationData.value.metrics.find(m => m.id === selectedScheme.value) || null
})

const clusterColors = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ec4899']

const getAriClass = (ari: number) => {
  if (ari === 1.0) return 'ari-perfect'
  if (ari >= 0.8) return 'ari-high'
  if (ari >= 0.4) return 'ari-mid'
  return 'ari-low'
}

const getSegmentPercent = (size: number) => {
  if (!activeMetric.value) return 0
  const total = activeMetric.value.sizes.reduce((a, b) => a + b, 0)
  return total > 0 ? (size / total) * 100 : 0
}
</script>

<style scoped>
.ablation-container {
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

.ablation-grid {
  display: grid;
  grid-template-columns: 560px 1fr;
  gap: 1.5rem;
  align-items: stretch;
  flex: 1;
}

.table-card {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.card-header h3 {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.table-wrapper {
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background: rgba(255, 255, 255, 0.01);
}

.metrics-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 0.85rem;
}

.metrics-table th {
  background: rgba(255, 255, 255, 0.03);
  padding: 0.75rem 1rem;
  color: var(--text-secondary);
  font-weight: 600;
  border-bottom: 1px solid var(--border-color);
}

.metrics-table td {
  padding: 0.85rem 1rem;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.metrics-table tbody tr {
  cursor: pointer;
  transition: var(--transition-smooth);
}

.metrics-table tbody tr:hover {
  background: rgba(255, 255, 255, 0.02);
}

.metrics-table tbody tr.active {
  background: rgba(99, 102, 241, 0.08);
}

.metrics-table tbody tr.active td {
  color: var(--text-primary);
}

.scheme-name-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.scheme-id {
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  font-size: 0.725rem;
  font-weight: 700;
  color: #fff;
}

.scheme-id.m0 { background: var(--color-primary); }
.scheme-id.c1 { background: var(--cluster-1); }
.scheme-id.c2 { background: var(--cluster-2); }
.scheme-id.c3 { background: var(--cluster-3); }
.scheme-id.c4 { background: var(--cluster-4); }
.scheme-id.c5 { background: #6b7280; }

.scheme-name {
  font-weight: 600;
}

.domains-cell {
  font-size: 0.8rem;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.num-cell {
  font-family: monospace;
  font-size: 0.9rem;
}

.ari-perfect { color: #34d399; font-weight: 600; }
.ari-high { color: #60a5fa; font-weight: 600; }
.ari-mid { color: #fbbf24; }
.ari-low { color: #f87171; }

.scheme-info-box {
  background: rgba(255, 255, 255, 0.015);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  margin-top: auto;
}

.info-header {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.75rem;
}

.info-header h4 {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary);
}

.info-domains {
  font-size: 0.775rem;
  color: var(--text-muted);
}

.sizes-summary {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.sizes-summary h5 {
  font-size: 0.8rem;
  color: var(--text-secondary);
  font-weight: 600;
}

.sizes-bar-row {
  height: 24px;
  border-radius: 6px;
  display: flex;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.05);
}

.size-bar-segment {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition-smooth);
}

.seg-label {
  font-size: 0.7rem;
  font-weight: 700;
  color: #fff;
}

.sizes-legend {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem 1rem;
  margin-top: 0.5rem;
}

.legend-dot-item {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.legend-dot-item .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.map-card {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
}

.map-card-header h3 {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.map-card-header p {
  font-size: 0.825rem;
  color: var(--text-secondary);
}

.map-render-area {
  flex: 1;
  margin-top: 1rem;
  position: relative;
  min-height: 480px;
}

.map-skeleton {
  width: 100%;
  height: 100%;
  border-radius: 8px;
}
</style>
