<template>
  <div class="profiles-container animate-fade-in">
    <!-- Header -->
    <div class="page-header glass-panel">
      <h1>五大类别画像描述</h1>
      <p>基于“人口 - 经济 - 口粮 - 饲料粮”四域的联合聚类结果，全国31个省份被划分成五个具有鲜明特征的协同画像类别。</p>
    </div>

    <!-- Cluster Cards Navigation Tabs -->
    <div class="tabs-row">
      <button 
        v-for="(profile, index) in profilesData" 
        :key="index"
        class="tab-btn glass-panel"
        :class="{ active: activeTab === index }"
        :style="activeTab === index ? { borderLeft: `4px solid ${profile.color}` } : {}"
        @click="activeTab = index"
      >
        <span class="tab-color-dot" :style="{ backgroundColor: profile.color }"></span>
        <span class="tab-title">类别 {{ index }}</span>
        <span class="tab-name">{{ profile.shortName }}</span>
      </button>
    </div>

    <div class="category-map-grid">
      <div
        v-for="(profile, index) in profilesData"
        :key="`map-${index}`"
        class="category-map-item"
        :class="{ active: activeTab === index }"
        @click="activeTab = index"
      >
        <ChinaMap
          v-if="provinces.length > 0"
          :provincesData="provinces"
          activeExperiment="M0"
          visualType="cluster"
          :focusedCluster="index"
          labelMode="none"
          compact
          :title="`类别 ${index}`"
          :subtitle="profile.shortName"
        />
        <div v-else class="profile-map-skeleton skeleton"></div>
      </div>
    </div>

    <!-- Active Profile Detail Display -->
    <div class="profile-detail-card glass-panel" :style="{ borderTop: `4px solid ${activeProfile.color}` }">
      <div class="card-header-row">
        <div class="title-sec">
          <span class="class-num" :style="{ color: activeProfile.color }">类别 {{ activeTab }}</span>
          <h2>{{ activeProfile.name }}</h2>
        </div>
        <div class="count-badge" :style="{ backgroundColor: activeProfile.color + '20', color: activeProfile.color, border: `1px solid ${activeProfile.color}` }">
          包含 {{ activeProfile.provinces.length }} 个省级行政区
        </div>
      </div>

      <div class="card-body-row">
        <!-- Text characteristics -->
        <div class="desc-section">
          <div class="text-block">
            <h3>👥 经济与社会特征</h3>
            <p>{{ activeProfile.socioEconomic }}</p>
          </div>
          <div class="text-block">
            <h3>🌾 粮食需求与消耗特征</h3>
            <p>{{ activeProfile.grainCharacteristics }}</p>
          </div>
        </div>

        <!-- Province pills -->
        <div class="provinces-section">
          <h3>📍 覆盖省份</h3>
          <div class="pills-grid">
            <span 
              v-for="prov in activeProfile.provinces" 
              :key="prov" 
              class="prov-pill"
              :style="{ backgroundColor: activeProfile.color + '10', borderColor: activeProfile.color + '30' }"
            >
              {{ prov }}
            </span>
          </div>
          <div class="metrics-summary-card">
            <h4>类别核心均值</h4>
            <div class="metrics-row">
              <div class="metric-item">
                <span class="lbl">人口密度</span>
                <span class="val">{{ activeProfile.averages.popDensity }} <small>人/km²</small></span>
              </div>
              <div class="metric-item">
                <span class="lbl">人均收入</span>
                <span class="val">{{ activeProfile.averages.income.toLocaleString() }} <small>元</small></span>
              </div>
              <div class="metric-item">
                <span class="lbl">人均口粮</span>
                <span class="val">{{ activeProfile.averages.foodGrain }} <small>kg/人</small></span>
              </div>
              <div class="metric-item">
                <span class="lbl">人均饲料粮</span>
                <span class="val">{{ activeProfile.averages.feedGrain }} <small>kg/人</small></span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import ChinaMap from '@/components/ChinaMap.vue'

const activeTab = ref(0)
const provinces = ref<any[]>([])

const fetchProfilesMapData = async () => {
  try {
    const response = await axios.get('/api/provinces')
    provinces.value = response.data
  } catch (err) {
    console.error('Failed to fetch profile map data:', err)
  }
}

onMounted(() => {
  fetchProfilesMapData()
})

const profilesData = [
  {
    shortName: '北方粮食增量区',
    name: '中密度 - 中收入 - 口粮高位上升 - 饲料粮高位上升',
    color: '#3b82f6',
    socioEconomic: '中等人口密度与中等收入水平，城镇化率处于中等水平，人口结构相对平稳。主要由北方及东北粮食主产区省份构成。',
    grainCharacteristics: '该类省份直接口粮需求基数较高，且由于传统饮食习惯，依然呈现微弱的上升趋势；与此同时，作为畜牧养殖核心地带，饲料粮人均折算值消费高，并呈现明显的持续上升趋势。双重特征决定了该区域是全国粮食保障与调运的核心支柱。',
    provinces: ['内蒙古', '吉林', '辽宁', '黑龙江', '河北', '河南'],
    averages: {
      popDensity: 243.6,
      income: 36295,
      foodGrain: 147.6,
      feedGrain: 159.6
    }
  },
  {
    shortName: '直辖市都市群',
    name: '高密度 - 高收入 - 口粮低位下降 - 饲料粮中位上升',
    color: '#8b5cf6',
    socioEconomic: '超高人口密度、超高城镇化率以及高居民可支配收入的典型超大型直辖市都市圈。老龄人口占比处于全国绝对高值，社会结构呈深度老龄化。',
    grainCharacteristics: '居民人均口粮消费水平处于全国最低档位，且由于多元化的健康膳食结构，口粮消费依然在持续下降；饲料粮消费处于中高水平，伴随高档肉蛋奶制品摄入比重增加，饲料粮间接需求呈现缓慢温和的上升态势。',
    provinces: ['北京', '上海', '天津'],
    averages: {
      popDensity: 1828.3,
      income: 75787,
      foodGrain: 90.6,
      feedGrain: 144.6
    }
  },
  {
    shortName: '中西部平缓追赶区',
    name: '低密度 - 低收入 - 口粮低位下降 - 饲料粮低位上升',
    color: '#10b981',
    socioEconomic: '多为中西部广大地区省份，人口密度低，人均可支配收入水平较低。少儿人口占比相对较高，老龄化进程较慢，人口红利或家庭规模保持在较好状态。',
    grainCharacteristics: '人均口粮需求处于较低水平且仍呈微弱萎缩态势；饲料粮消费同样较低，但展现出明显的追赶效应，人均肉类消费增加拉动饲料粮需求平稳地缓慢上升。',
    provinces: ['山西', '云南', '四川', '广西', '湖北', '贵州', '陕西', '甘肃', '青海', '宁夏', '新疆'],
    averages: {
      popDensity: 167.3,
      income: 31754,
      foodGrain: 114.3,
      feedGrain: 132.8
    }
  },
  {
    shortName: '东南沿海发达区',
    name: '高密度 - 高收入 - 口粮中位稳定 - 饲料粮高位上升',
    color: '#f59e0b',
    socioEconomic: '主要由东部沿海及南部经济高度发达的省份和直辖市（如粤、浙、苏、闽）构成。人口密度较大，城镇化率极高，可支配收入在全国处于领先梯队。',
    grainCharacteristics: '人均直接口粮消费量处于全国中等水平，且基本步入饱和状态，年度波动极小，呈平稳走势。但由于高水平的肉类、家禽与海鲜水产消费，人均饲料粮消费量位列全国最高档位，且仍保持极为强劲的上升增长势头。',
    provinces: ['山东', '江苏', '浙江', '安徽', '福建', '江西', '湖南', '广东', '海南', '重庆'],
    averages: {
      popDensity: 524.2,
      income: 45786,
      foodGrain: 124.9,
      feedGrain: 202.3
    }
  },
  {
    shortName: '高原边疆消耗区',
    name: '低密度 - 低收入 - 口粮高位下降 - 饲料粮低位稳定',
    color: '#ec4899',
    socioEconomic: '典型的高原高寒边疆地带，人口密度极低，城镇化率低，家庭规模显著偏大。',
    grainCharacteristics: '受地理环境和传统主食（青稞、糌粑、面粉）限制，居民直接口粮消费人均基数极大，但随着流通改善与食品多元化，正经历剧烈的下降；饲料粮折算值人均需求处于全国最低位，由于当地畜牧多为天然草场放牧，饲料转化率极低，饲料粮基本保持低位无增长状态。',
    provinces: ['西藏'],
    averages: {
      popDensity: 3.1,
      income: 31358,
      foodGrain: 124.0,
      feedGrain: 92.8
    }
  }
]

const activeProfile = computed(() => profilesData[activeTab.value])
</script>

<style scoped>
.profiles-container {
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

.tabs-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 1rem;
}

.tab-btn {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.35rem;
  cursor: pointer;
  border-left: 4px solid transparent;
  text-align: left;
  transition: var(--transition-smooth);
}

.tab-btn:hover {
  transform: translateY(-2px);
}

.tab-btn.active {
  background: rgba(255, 255, 255, 0.03);
}

.tab-color-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-bottom: 0.25rem;
}

.tab-title {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-weight: 600;
  text-transform: uppercase;
}

.tab-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
}

.category-map-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem;
}

.category-map-item {
  cursor: pointer;
  transition: var(--transition-smooth);
}

.category-map-item:hover,
.category-map-item.active {
  transform: translateY(-2px);
}

.category-map-item.active :deep(.map-wrapper) {
  border-color: rgba(255, 255, 255, 0.24);
}

.profile-detail-card {
  padding: 2rem;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 1.25rem;
}

.title-sec {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.class-num {
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.title-sec h2 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
}

.count-badge {
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.825rem;
  font-weight: 600;
}

.card-body-row {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 2.5rem;
  align-items: start;
}

.desc-section {
  display: flex;
  flex-direction: column;
  gap: 1.75rem;
}

.profile-map-skeleton {
  width: 100%;
  height: 320px;
  border-radius: 8px;
}

.text-block {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.text-block h3 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.text-block p {
  font-size: 0.925rem;
  color: var(--text-secondary);
  line-height: 1.6;
}

.provinces-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.provinces-section h3 {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary);
}

.pills-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.prov-pill {
  padding: 0.45rem 0.85rem;
  border-radius: 6px;
  font-size: 0.825rem;
  font-weight: 500;
  border: 1px solid transparent;
  color: var(--text-primary);
}

.metrics-summary-card {
  background: rgba(255, 255, 255, 0.015);
  border: 1px solid var(--border-color);
  padding: 1.25rem;
  border-radius: 8px;
}

.metrics-summary-card h4 {
  font-size: 0.825rem;
  color: var(--text-secondary);
  margin-bottom: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
}

.metrics-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.metric-item .lbl {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.metric-item .val {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--text-primary);
}

.metric-item .val small {
  font-size: 0.7rem;
  color: var(--text-muted);
  font-weight: 400;
}
</style>
