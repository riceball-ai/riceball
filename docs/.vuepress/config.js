import { viteBundler } from '@vuepress/bundler-vite'
import { defaultTheme } from '@vuepress/theme-default'
import { markdownChartPlugin } from '@vuepress/plugin-markdown-chart'
import { defineUserConfig } from 'vuepress'

export default defineUserConfig({
  base: '/riceball/', // GitHub Pages base URL, change this if you use a custom domain
  locales: {
    '/': {
      lang: 'en-US',
      title: 'RiceBall',
      description: 'Open Source Full-Stack AI Agent & Knowledge Base Platform',
    },
    '/zh/': {
      lang: 'zh-CN',
      title: 'RiceBall',
      description: '开源全栈 AI Agent & 知识库平台',
    },
  },

  bundler: viteBundler(),

  plugins: [
    markdownChartPlugin({
      mermaid: true,
    })
  ],

  theme: defaultTheme({
    logo: '/logo.png',
    repo: 'riceball-ai/riceball',
    docsDir: 'docs',
    
    locales: {
      '/': {
        selectLanguageName: 'English',
        navbar: [
          {
            text: 'Guide',
            link: '/guide/intro.html',
          },
          {
            text: 'Deployment',
            link: '/deployment/docker.html',
          },
        ],
        sidebar: {
          '/guide/': [
            {
              text: 'Guide',
              children: [
                '/guide/intro.md',
                '/guide/getting-started.md',
                '/guide/architecture.md',
                '/guide/configuration.md',
              ],
            },
          ],
          '/deployment/': [
            {
              text: 'Deployment',
              children: [
                '/deployment/docker.md',
              ],
            },
          ],
        },
      },
      '/zh/': {
        selectLanguageName: '简体中文',
        navbar: [
          {
            text: '指南',
            link: '/zh/guide/intro.html',
          },
          {
            text: '部署',
            link: '/zh/deployment/docker.html',
          },
        ],
        sidebar: {
          '/zh/guide/': [
            {
              text: '指南',
              children: [
                '/zh/guide/intro.md',
                '/zh/guide/getting-started.md',
                '/zh/guide/architecture.md',
                '/zh/guide/configuration.md',
              ],
            },
          ],
          '/zh/deployment/': [
            {
              text: '部署指南',
              children: [
                '/zh/deployment/docker.md',
              ],
            },
          ],
        },
      },
    },
  }),
})
