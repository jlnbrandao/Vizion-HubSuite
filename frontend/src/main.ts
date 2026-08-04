import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { Quasar, Notify, Dialog } from 'quasar'
import quasarLang from 'quasar/lang/pt-BR'
import iconSet from 'quasar/icon-set/material-icons'

import '@quasar/extras/material-icons/material-icons.css'
import 'quasar/src/css/index.sass'
import '@/css/app.scss'

import App from '@/App.vue'
import router from '@/router'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(Quasar, {
  plugins: { Notify, Dialog },
  lang: quasarLang,
  iconSet,
  config: {
    brand: {
      primary: '#0f766e',
      secondary: '#134e4a',
      accent: '#f59e0b',
      dark: '#0b1f1c',
      positive: '#059669',
      negative: '#dc2626',
      info: '#0ea5e9',
      warning: '#d97706',
    },
  },
})

app.mount('#app')
