export default defineNuxtConfig({
  devtools: { enabled: false },
  modules: ['@nuxt/ui', '@nuxtjs/i18n'],
  colorMode: {
    preference: 'dark',
    fallback: 'dark',
  },
  app: {
    baseURL: '/maru-search/',
    head: {
      title: 'maru-search',
      meta: [
        { name: 'description', content: 'Universal AI search MCP server. Zero API keys.' },
        { name: 'theme-color', content: '#0a0a0f' },
      ],
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/maru-search/favicon.svg' },
      ],
    },
  },
  nitro: {
    preset: 'github_pages',
    prerender: {
      routes: ['/','/ko'],
    },
  },
  i18n: {
    locales: [
      { code: 'en', language: 'en-US', file: 'en.json', name: 'English' },
      { code: 'ko', language: 'ko-KR', file: 'ko.json', name: '한국어' },
    ],
    defaultLocale: 'en',
    strategy: 'prefix_except_default',
    langDir: 'locales/',
    compilation: {
      strictMessage: false,
    },
  },
})
