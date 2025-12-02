// https://nuxt.com/docs/api/configuration/nuxt-config

import tailwindcss from '@tailwindcss/vite'

const appName = process.env.APP_NAME || 'RiceBall'

export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: false },
  ssr: false,
  css: [
    '~/assets/css/tailwind.css',
    'katex/dist/katex.min.css'
  ],
  vite: {
    plugins: [
      tailwindcss(),
    ],
  },

  app: {
    head: {
      title: appName
    },
  },

  runtimeConfig: {
    public: {
      appName: appName,
    }
  },

  modules: [
    'shadcn-nuxt',
    '@pinia/nuxt',
    '@nuxtjs/i18n',
    '@nuxtjs/color-mode',
    '@nuxt/scripts',
    '@nuxt/content'
  ],

  content: {
    experimental: { sqliteConnector: 'native' },
  },
  
  colorMode: {
    classSuffix: ''
  },

  shadcn: {
    /**
     * Prefix for all the imported component
     */
    prefix: '',
    /**
     * Directory that the component lives in.
     * @default "./components/ui"
     */
    componentDir: './app/components/ui'
  },

  nitro: {
    devProxy: {
      '/api': { 
        target: process.env.API_BASE_URL || 'http://localhost:8000/api',
        changeOrigin: true
      },
    }
  },

  i18n: {
    defaultLocale: 'en',
    detectBrowserLanguage: {
      useCookie: true,
      cookieKey: 'i18n_redirected',
      redirectOn: 'root' // recommended
    },
    strategy: 'no_prefix',
    locales: [
      { code: 'en', name: 'English', language: 'en-US', file: 'en.ts' },
      { code: 'zh-Hans', name: '简体中文', language: 'zh-Hans', file: 'zh-Hans.ts' }
    ]
  }
})