<template>
  <div class="app-layout">
    <!-- Sidebar Navigation -->
    <aside class="sidebar glass-panel">
      <div class="sidebar-header">
        <div class="logo-icon">🌾</div>
        <div class="logo-text">
          <h2>省份聚类</h2>
          <span>多域联合聚类系统</span>
        </div>
      </div>

      <nav class="nav-menu">
        <router-link to="/" class="nav-item" active-class="active">
          <span class="icon">🗺️</span>
          <span class="label">空间聚类概览</span>
        </router-link>
        
        <router-link to="/profiles" class="nav-item" active-class="active">
          <span class="icon">👥</span>
          <span class="label">五大类别画像</span>
        </router-link>
        
        <router-link to="/ablation" class="nav-item" active-class="active">
          <span class="icon">🧪</span>
          <span class="label">消融实验对比</span>
        </router-link>
        
        <router-link to="/explorer" class="nav-item" active-class="active">
          <span class="icon">📁</span>
          <span class="label">原始数据浏览</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="status-indicator">
          <span class="dot pulse-green"></span>
          <span>后端 API 连接正常</span>
        </div>
        <div class="footer-meta">
          <p>设计规范: 2026-06-08</p>
          <p>状态: 已批准 (Approved)</p>
        </div>
      </div>
    </aside>

    <!-- Main Workspace Contents -->
    <main class="main-content">
      <header class="top-bar glass-panel animate-fade-in">
        <div class="route-title">
          <h1>{{ currentRouteTitle }}</h1>
        </div>
      </header>

      <div class="workspace-viewport">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const currentRouteTitle = computed(() => {
  if (route.path === '/') return '空间聚类概览看板'
  if (route.path === '/profiles') return '类别画像特征描述'
  if (route.path === '/ablation') return '模型消融实验与稳定性'
  if (route.path === '/explorer') return '明细数据过滤器'
  return '省级粮食预测看板'
})
</script>

<style>
/* Global Layout Styling */
.app-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  background-color: var(--bg-primary);
  overflow: hidden;
  padding: 1rem;
  gap: 1rem;
}

.sidebar {
  width: 260px;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 1.5rem 1rem;
  border-radius: 12px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 2.5rem;
  padding: 0 0.5rem;
}

.logo-icon {
  font-size: 1.75rem;
}

.logo-text h2 {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 0.05em;
}

.logo-text span {
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.nav-menu {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 1;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  transition: var(--transition-smooth);
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-primary);
  transform: translateX(4px);
}

.nav-item.active {
  background: var(--color-primary);
  color: #fff;
  box-shadow: var(--shadow-glow);
}

.sidebar-footer {
  margin-top: auto;
  border-top: 1px solid var(--border-color);
  padding-top: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: var(--text-secondary);
  font-weight: 500;
}

.status-indicator .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
}

.pulse-green {
  background-color: var(--color-success);
  box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
  animation: pulse 1.6s infinite;
}

@keyframes pulse {
  0% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
  }
  70% {
    transform: scale(1);
    box-shadow: 0 0 0 6px rgba(16, 185, 129, 0);
  }
  100% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
  }
}

.footer-meta {
  font-size: 0.7rem;
  color: var(--text-muted);
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

/* Right Content Area Styling */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  height: 100%;
  overflow: hidden;
}

.top-bar {
  padding: 0.75rem 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-radius: 12px;
}

.route-title h1 {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--text-primary);
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.user-profile .badge {
  font-size: 0.725rem;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.05);
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}

.user-profile .avatar {
  font-size: 1.25rem;
}

.workspace-viewport {
  flex: 1;
  overflow-y: auto;
  padding-right: 2px; /* Prevent layout shift when scrollbar appears */
}
</style>
