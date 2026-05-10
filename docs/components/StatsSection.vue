<template>
  <section class="relative overflow-hidden border-t border-gray-800/60 py-20">
    <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-indigo-900/10 via-gray-950 to-gray-950" />
    <UContainer class="relative">
      <div class="mb-12 text-center">
        <p class="text-sm font-medium tracking-wider text-indigo-400 uppercase">{{ $t('stats.subtitle') }}</p>
      </div>
      <div class="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <div
          v-for="(stat, i) in stats"
          :key="i"
          class="group relative rounded-2xl border border-gray-800 bg-gray-900/40 p-6 text-center backdrop-blur transition-all duration-500 hover:border-indigo-500/30 hover:bg-gray-800/60"
        >
          <div class="absolute inset-0 rounded-2xl bg-gradient-to-br from-indigo-500/5 to-violet-500/5 opacity-0 transition-opacity group-hover:opacity-100" />
          <div class="relative">
            <div class="mb-2 text-4xl font-black tracking-tight text-white sm:text-5xl">
              <span class="bg-gradient-to-r from-indigo-400 via-violet-400 to-fuchsia-400 bg-clip-text text-transparent">{{ stat.value }}</span>
            </div>
            <div class="text-sm font-medium text-gray-400">{{ stat.label }}</div>
          </div>
        </div>
      </div>
    </UContainer>
  </section>
</template>

<script setup>
const { t } = useI18n()
const stats = computed(() => [
  { value: '0', label: t('stats.apiKeys') },
  { value: '8', label: t('stats.tools') },
  { value: '21', label: t('stats.languages') },
  { value: '174', label: t('stats.tests') },
])
</script>
