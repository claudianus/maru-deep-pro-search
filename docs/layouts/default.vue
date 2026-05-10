<template>
  <div class="min-h-screen bg-gray-950 text-gray-100">
    <nav class="sticky top-0 z-50 border-b border-gray-800/60 bg-gray-950/80 backdrop-blur-xl">
      <UContainer class="flex h-16 items-center justify-between">
        <NuxtLink :to="localePath('/')" class="flex items-center gap-2 text-lg font-bold tracking-tight">
          <span class="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">maru-deep-pro-search</span>
        </NuxtLink>

        <div class="flex items-center gap-3">
          <div class="hidden items-center gap-1 sm:flex">
            <UButton
              v-for="link in navLinks"
              :key="link.to"
              :to="link.to"
              variant="ghost"
              size="xs"
              color="gray"
              class="text-gray-400 hover:text-gray-200"
            >
              {{ link.label }}
            </UButton>
          </div>
          <UDivider orientation="vertical" class="h-5 hidden sm:block" />
          <UButton
            v-for="loc in locales"
            :key="loc.code"
            :to="switchLocalePath(loc.code)"
            variant="ghost"
            size="xs"
            :color="locale === loc.code ? 'primary' : 'gray'"
          >
            {{ loc.name }}
          </UButton>
          <UDivider orientation="vertical" class="h-5" />
          <UButton
            icon="i-simple-icons-github"
            to="https://github.com/claudianus/maru-deep-pro-search"
            target="_blank"
            variant="ghost"
            color="gray"
            size="sm"
          />
          <UButton
            icon="i-simple-icons-pypi"
            to="https://pypi.org/project/maru-deep-pro-search/"
            target="_blank"
            variant="ghost"
            color="gray"
            size="sm"
          />
        </div>
      </UContainer>
    </nav>

    <main>
      <slot />
    </main>

    <footer class="border-t border-gray-800/60 py-10">
      <UContainer class="flex flex-col items-center justify-between gap-4 sm:flex-row">
        <p class="text-sm text-gray-500">
          {{ $t('footer.built') }} &middot; <NuxtLink to="https://github.com/claudianus/maru-deep-pro-search" class="text-gray-400 hover:text-gray-200">claudianus/maru-deep-pro-search</NuxtLink>
        </p>
        <div class="flex gap-4 text-sm text-gray-500">
          <NuxtLink :to="localePath('/')" class="hover:text-gray-200">{{ $t('nav.home') }}</NuxtLink>
          <NuxtLink :to="localePath('/','ko')" class="hover:text-gray-200">{{ $t('nav.ko') }}</NuxtLink>
          <NuxtLink to="https://github.com/claudianus/maru-deep-pro-search/blob/main/CHANGELOG.md" target="_blank" class="hover:text-gray-200">{{ $t('footer.changelog') }}</NuxtLink>
        </div>
      </UContainer>
    </footer>
  </div>
</template>

<script setup>
const { locale, locales, t } = useI18n()
const switchLocalePath = useSwitchLocalePath()
const localePath = useLocalePath()

const navLinks = computed(() => [
  { to: '#features', label: t('features.title').replace('?', '') },
  { to: '#tools', label: t('tools.title') },
  { to: '#install', label: t('install.title') },
])
</script>
