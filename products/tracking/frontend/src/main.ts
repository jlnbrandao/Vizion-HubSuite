import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { Quasar, Notify, Dialog } from 'quasar'
import iconSet from 'quasar/icon-set/material-icons'
import '@quasar/extras/material-icons/material-icons.css'
import 'quasar/src/css/index.sass'
import 'leaflet/dist/leaflet.css'
import App from '@/App.vue'
import { createTrackingRouter } from '@/router'
import { loadRuntimeConfig } from '@openvizion/web-runtime'

async function boot() {
  const config = await loadRuntimeConfig()
  const app = createApp(App)
  app.use(createPinia())
  app.use(createTrackingRouter())
  app.use(Quasar, {
    plugins: { Notify, Dialog },
    iconSet,
    config: { brand: { primary: '#0f766e' } },
  })
  app.provide('runtimeConfig', config)
  app.mount('#app')
}

void boot()
