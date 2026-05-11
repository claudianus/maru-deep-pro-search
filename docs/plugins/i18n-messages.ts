import en from '../i18n/en.json'
import ko from '../i18n/ko.json'

export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.hook('app:created', () => {
    const i18n = nuxtApp.$i18n as any
    i18n.setLocaleMessage('en', en)
    i18n.setLocaleMessage('ko', ko)
  })
})
