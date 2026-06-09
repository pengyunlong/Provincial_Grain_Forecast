<template>
  <div class="map-wrapper glass-panel" :class="{ compact: props.compact }">
    <div class="map-header">
      <div class="map-title-section">
        <h3>{{ props.title }}</h3>
        <p class="map-subtitle">
          {{ props.subtitle || defaultSubtitle }}
        </p>
      </div>
      <div class="map-legend">
        <!-- Cluster Legend -->
        <template v-if="props.visualType === 'cluster' && props.focusedCluster === null">
          <div class="legend-item" v-for="(color, index) in clusterColors" :key="index">
            <span class="legend-color" :style="{ backgroundColor: color }"></span>
            <span class="legend-label">类别 {{ index }}</span>
          </div>
          <div class="legend-item" v-if="props.emphasizeStable">
            <span class="legend-color stable-swatch"></span>
            <span class="legend-label">深色为稳定省份</span>
          </div>
        </template>
        <template v-else-if="props.visualType === 'cluster' && props.focusedCluster !== null">
          <div class="legend-item">
            <span class="legend-color" :style="{ backgroundColor: clusterColors[props.focusedCluster] }"></span>
            <span class="legend-label">类别 {{ props.focusedCluster }}</span>
          </div>
          <div class="legend-item">
            <span class="legend-color muted-swatch"></span>
            <span class="legend-label">其他类别</span>
          </div>
        </template>
        <!-- Stability Legend -->
        <template v-else>
          <div class="legend-item" v-for="(color, score) in stabilityColors" :key="score">
            <span class="legend-color" :style="{ backgroundColor: color }"></span>
            <span class="legend-label">稳定性 {{ score }}</span>
          </div>
        </template>
      </div>
    </div>
    
    <div v-if="loading" class="map-loading skeleton">
      <div class="loading-spinner"></div>
      <p>地图数据加载中...</p>
    </div>
    <div v-else-if="error" class="map-error">
      <p>{{ error }}</p>
      <button @click="loadMap" class="btn-retry">重试</button>
    </div>
    <div ref="mapContainer" class="map-container" v-show="!loading && !error"></div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import type { PropType } from 'vue'
import * as echarts from 'echarts'
import axios from 'axios'

const props = defineProps({
  provincesData: {
    type: Array as () => any[],
    required: true
  },
  activeExperiment: {
    type: String,
    default: 'M0'
  },
  visualType: {
    type: String as () => 'cluster' | 'stability',
    default: 'cluster'
  },
  focusedCluster: {
    type: Number as PropType<number | null>,
    default: null
  },
  emphasizeStable: {
    type: Boolean,
    default: false
  },
  labelMode: {
    type: String as () => 'none' | 'province' | 'cluster' | 'focused',
    default: 'none'
  },
  title: {
    type: String,
    default: '地理空间分布图'
  },
  subtitle: {
    type: String,
    default: ''
  },
  compact: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['select-province'])

const mapContainer = ref<HTMLDivElement | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
let chartInstance: echarts.ECharts | null = null
let geoJsonData: any = null
let geoJsonCache: any = null
let geoJsonRequest: Promise<any> | null = null

// Color schemes
const clusterColors = [
  '#3b82f6', // Cluster 0: Blue
  '#8b5cf6', // Cluster 1: Purple
  '#10b981', // Cluster 2: Emerald
  '#f59e0b', // Cluster 3: Amber
  '#ec4899'  // Cluster 4: Pink
]

const stableClusterColors = [
  '#1d4ed8',
  '#6d28d9',
  '#047857',
  '#b45309',
  '#be185d'
]

const stabilityColors: Record<number, string> = {
  6: '#10b981', // Emerald (Perfect stability)
  5: '#34d399', // Light Emerald
  4: '#60a5fa', // Blue
  3: '#fbbf24', // Amber
  2: '#f87171', // Light Red
  1: '#ef4444'  // Red (Low stability)
}

const getExperimentName = (expId: string) => {
  const names: Record<string, string> = {
    'M0': '四域等权主实验',
    'C1': '所有特征直接等权',
    'C2': '消融: 移除人口域',
    'C3': '消融: 移除经济域',
    'C4': '消融: 移除口粮域',
    'C5': '消融: 移除饲料粮域'
  }
  return names[expId] || expId
}

const defaultSubtitle = computed(() => {
  if (props.visualType === 'stability') return '各省份聚类分组稳定性评估'
  if (props.focusedCluster !== null) return `类别 ${props.focusedCluster} 在全国31省中的空间位置`
  return `当前方案: ${getExperimentName(props.activeExperiment)}`
})

const getShortProvinceName = (name: string) => {
  return name.replace(/省|市|自治区|特别行政区|壮族|回族|维吾尔/g, '')
}

const getGeoJson = async () => {
  if (geoJsonCache) return geoJsonCache
  if (!geoJsonRequest) {
    geoJsonRequest = axios.get('/api/geojson').then((response) => response.data)
  }
  geoJsonCache = await geoJsonRequest
  return geoJsonCache
}

// Fetch map GeoJSON and init
const loadMap = async () => {
  loading.value = true
  error.value = null
  try {
    geoJsonData = await getGeoJson()
    
    // Hainan province correction if needed (usually 460000)
    if (geoJsonData && geoJsonData.features) {
      geoJsonData.features.forEach((feature: any) => {
        if (feature.properties && feature.properties.name === '海南省') {
          feature.properties.adcode = 460000
        }
      })
    }

    echarts.registerMap('china', geoJsonData)
    loading.value = false
    
    // Initialize chart on next tick
    await nextTick()
    initChart()
  } catch (err: any) {
    console.error('Failed to load map GeoJSON:', err)
    error.value = '地图数据载入失败，请确认后端服务已启动'
    loading.value = false
  }
}

const initChart = () => {
  if (!mapContainer.value) return
  
  if (chartInstance) {
    chartInstance.dispose()
  }

  chartInstance = echarts.init(mapContainer.value, 'dark', {
    renderer: 'canvas'
  })

  updateChartOptions()

  chartInstance.on('click', (params: any) => {
    if (params.data) {
      emit('select-province', params.data)
    }
  })

  window.addEventListener('resize', handleResize)
}

const handleResize = () => {
  chartInstance?.resize()
}

const updateChartOptions = () => {
  if (!chartInstance) return

  // Prepare map data
  const seriesData = geoJsonData.features.map((feature: any) => {
    const adcode = feature.properties.adcode.toString()
    const name = feature.properties.name

    // Find matching province data from backend
    const provData = props.provincesData.find(p => p.code === adcode || p.name === getShortProvinceName(name))
    
    if (provData) {
      let value = 0
      let color = '#4b5563' // Default gray
      let labelText = '未包含在实验中'
      let borderColor = 'rgba(255, 255, 255, 0.3)'
      let borderWidth = 1
      let opacity = 1

      if (props.visualType === 'cluster') {
        const clusterVal = provData.labels[props.activeExperiment]
        value = clusterVal !== undefined ? clusterVal : provData.cluster_m0
        const stable = props.emphasizeStable && provData.stability === 6
        color = stable ? (stableClusterColors[value] || '#334155') : (clusterColors[value] || '#4b5563')
        labelText = `类别: ${value}`

        if (props.focusedCluster !== null && value !== props.focusedCluster) {
          color = '#253247'
          borderColor = 'rgba(148, 163, 184, 0.12)'
          borderWidth = 0.6
          opacity = 0.55
        } else if (props.focusedCluster !== null && value === props.focusedCluster) {
          borderColor = 'rgba(255, 255, 255, 0.75)'
          borderWidth = 1.4
        } else if (stable) {
          borderColor = 'rgba(255, 255, 255, 0.78)'
          borderWidth = 1.25
        }
      } else {
        const stabilityVal = provData.stability
        value = stabilityVal
        color = stabilityColors[value] || '#4b5563'
        labelText = `稳定性: ${value}/6`
      }

      return {
        name: feature.properties.name,
        code: adcode,
        value: value,
        itemStyle: {
          areaColor: color,
          borderColor,
          borderWidth,
          opacity
        },
        // Store backend data in the data item
        provData: provData,
        labelText: labelText
      }
    } else {
      // HK, Macau, Taiwan, or out of range
      return {
        name: feature.properties.name,
        code: adcode,
        value: -1,
        itemStyle: {
          areaColor: '#1e293b',
          borderColor: 'rgba(255, 255, 255, 0.1)',
          borderWidth: 0.5
        },
        labelText: '未建模区域',
        tooltip: { show: false } // Disable tooltip for non-modeled regions
      }
    }
  })

  const coloredRegions = seriesData.map((item: any) => ({
    name: item.name,
    itemStyle: item.itemStyle
  }))

  const option: echarts.EChartsOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(15, 23, 42, 0.9)',
      borderColor: 'rgba(255, 255, 255, 0.15)',
      textStyle: {
        color: '#f3f4f6',
        fontSize: 13,
        fontFamily: 'system-ui'
      },
      formatter: (params: any) => {
        if (!params.data || params.data.value === -1) {
          return `${params.name}: 未参与本次聚类建模`
        }
        const data = params.data
        const prov = data.provData
        if (!prov) return params.name

        let html = `<div style="padding: 4px 8px;">
          <h4 style="margin: 0 0 6px 0; color: #fff; font-size: 14px; font-weight: 600;">${prov.name}</h4>`
        
        if (props.visualType === 'cluster') {
          const stableNote = props.emphasizeStable && prov.stability === 6 ? ' · 稳定省份' : ''
          html += `<p style="margin: 0 0 4px 0; color: var(--text-secondary);">分群类别: <strong style="color: ${clusterColors[data.value]}">${data.value}</strong>${stableNote}</p>
                   <p style="margin: 0 0 6px 0; font-size: 11px; color: #9ca3af;">${prov.cluster_label}</p>`
        } else {
          html += `<p style="margin: 0 0 6px 0; color: var(--text-secondary);">稳定性评分: <strong style="color: ${stabilityColors[prov.stability]}">${prov.stability} / 6</strong></p>`
        }

        html += `<div style="border-top: 1px solid rgba(255,255,255,0.1); padding-top: 6px; margin-top: 6px; font-size: 12px;">
          <div style="display:flex; justify-content:space-between; margin-bottom: 2px;">
            <span style="color:#9ca3af; margin-right: 12px;">人口密度:</span>
            <span style="color:#fff; font-weight:500;">${prov.metrics.pop_density.toFixed(1)} 人/km²</span>
          </div>
          <div style="display:flex; justify-content:space-between; margin-bottom: 2px;">
            <span style="color:#9ca3af; margin-right: 12px;">人均收入:</span>
            <span style="color:#fff; font-weight:500;">${prov.metrics.disposable_income.toLocaleString()} 元</span>
          </div>
          <div style="display:flex; justify-content:space-between; margin-bottom: 2px;">
            <span style="color:#9ca3af; margin-right: 12px;">年人均口粮:</span>
            <span style="color:#fff; font-weight:500;">${prov.metrics.food_grain.toFixed(1)} kg</span>
          </div>
          <div style="display:flex; justify-content:space-between;">
            <span style="color:#9ca3af; margin-right: 12px;">年人均饲料粮:</span>
            <span style="color:#fff; font-weight:500;">${prov.metrics.feed_grain.toFixed(1)} kg</span>
          </div>
        </div>
        </div>`
        return html
      }
    },
    geo: {
      map: 'china',
      roam: true,
      zoom: 1.2,
      center: [104.2, 35.8], // Approximate center of China
      label: {
        show: props.labelMode !== 'none',
        color: '#e2e8f0',
        fontSize: props.compact ? 8 : 10,
        formatter: (params: any) => {
          // Only show labels for modeled provinces
          const adcode = params.adcode ? params.adcode.toString() : ''
          const matched = props.provincesData.find(p => p.code === adcode || params.name.includes(p.name))
          if (!matched) return ''

          const clusterVal = matched.labels?.[props.activeExperiment] ?? matched.cluster_m0
          if (props.labelMode === 'cluster') return `${getShortProvinceName(params.name)}\n类${clusterVal}`
          if (props.labelMode === 'focused') return props.focusedCluster === clusterVal ? getShortProvinceName(params.name) : ''
          return getShortProvinceName(params.name)
        }
      },
      itemStyle: {
        areaColor: '#1e293b',
        borderColor: 'rgba(255, 255, 255, 0.1)',
        borderWidth: 0.8
      },
      emphasis: {
        label: {
          show: true,
          color: '#ffffff',
          fontWeight: 'bold'
        },
        itemStyle: {
          areaColor: '#4f46e5',
          shadowColor: 'rgba(99, 102, 241, 0.5)',
          shadowBlur: 10
        }
      },
      regions: [
        ...coloredRegions,
        // Gray out Hong Kong, Macau, Taiwan, and South Sea Islands
        { name: '南海诸岛', itemStyle: { areaColor: '#1e293b', opacity: 0.6 } },
        { name: '台湾省', itemStyle: { areaColor: '#1e293b', opacity: 0.6 } },
        { name: '香港特别行政区', itemStyle: { areaColor: '#1e293b', opacity: 0.6 } },
        { name: '澳门特别行政区', itemStyle: { areaColor: '#1e293b', opacity: 0.6 } }
      ]
    },
    series: [
      {
        type: 'map',
        geoIndex: 0,
        data: seriesData
      }
    ]
  }

  chartInstance.setOption(option)
}

watch([
  () => props.provincesData,
  () => props.activeExperiment,
  () => props.visualType,
  () => props.focusedCluster,
  () => props.emphasizeStable,
  () => props.labelMode
], () => {
  if (chartInstance && geoJsonData) {
    updateChartOptions()
  }
}, { deep: true })

onMounted(() => {
  loadMap()
})

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose()
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.map-wrapper {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative;
}

.map-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  z-index: 10;
}

.map-title-section h3 {
  font-size: 1.15rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.map-subtitle {
  font-size: 0.825rem;
  color: var(--text-secondary);
}

.map-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  max-width: 50%;
  justify-content: flex-end;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  display: inline-block;
}

.stable-swatch {
  background: linear-gradient(135deg, #1d4ed8, #047857);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.28);
}

.muted-swatch {
  background: #253247;
}

.legend-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  font-weight: 500;
}

.map-container {
  flex: 1;
  width: 100%;
  min-height: 480px;
}

.map-wrapper.compact {
  padding: 1rem;
}

.map-wrapper.compact .map-header {
  margin-bottom: 0.5rem;
}

.map-wrapper.compact .map-container,
.map-wrapper.compact .map-loading,
.map-wrapper.compact .map-error {
  min-height: 260px;
}

.map-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  min-height: 480px;
  border-radius: 8px;
}

.loading-spinner {
  border: 3px solid rgba(255, 255, 255, 0.1);
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border-left-color: var(--color-primary);
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.map-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  min-height: 480px;
  text-align: center;
  color: var(--color-danger);
}

.btn-retry {
  margin-top: 1rem;
  padding: 0.5rem 1.25rem;
  background: var(--color-primary);
  border: none;
  border-radius: 6px;
  color: #fff;
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition-smooth);
}

.btn-retry:hover {
  background: var(--color-primary-hover);
}
</style>
