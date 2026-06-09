import { createApp } from 'vue'
import './assets/main.css'
import App from './App.vue'
import router from './router'
import axios from 'axios'

// Global interceptor to rewrite /api/ endpoints to local static JSON files
axios.interceptors.request.use((config) => {
  if (config.url && config.url.startsWith('/api/')) {
    const path = config.url.substring(1) // Remove leading slash -> "api/..."
    const suffix = path.endsWith('.json') ? '' : '.json'
    // Combine with Vite's BASE_URL
    const baseUrl = import.meta.env.BASE_URL === './' ? '' : import.meta.env.BASE_URL
    config.url = `${baseUrl}${path}${suffix}`
  }
  return config
})

const app = createApp(App)
app.use(router)
app.mount('#app')

