import { createRouter, createWebHashHistory } from 'vue-router'
import Overview from '@/views/Overview.vue'

const routes = [
  {
    path: '/',
    name: 'Overview',
    component: Overview,
    meta: { title: '空间聚类概览 - 省级粮食预测' }
  },
  {
    path: '/profiles',
    name: 'Profiles',
    component: () => import('@/views/Profiles.vue'),
    meta: { title: '五大类别画像 - 省级粮食预测' }
  },
  {
    path: '/ablation',
    name: 'Ablation',
    component: () => import('@/views/Ablation.vue'),
    meta: { title: '消融实验与稳定性 - 省级粮食预测' }
  },
  {
    path: '/explorer',
    name: 'Explorer',
    component: () => import('@/views/Explorer.vue'),
    meta: { title: '数据明细浏览器 - 省级粮食预测' }
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

router.beforeEach((to) => {
  if (to.meta.title) {
    document.title = to.meta.title as string
  }
  return true
})

export default router
