<template>
  <section class="border-t border-gray-800/60 py-20">
    <UContainer>
      <div class="mb-12 text-center">
        <h2 class="text-3xl font-bold tracking-tight">{{ $t('features.title') }}</h2>
      </div>
      <div class="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <UCard
          v-for="(item, key) in items"
          :key="key"
          class="group border-gray-800 bg-gray-900/40 backdrop-blur transition-all duration-300 hover:border-indigo-500/40 hover:bg-gray-800/60"
          :ui="{ body: { base: 'p-6' } }"
        >
          <div class="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-400 ring-1 ring-indigo-500/20 group-hover:ring-indigo-500/40">
            <UIcon :name="item.icon" class="h-5 w-5" />
          </div>
          <h3 class="mb-2 text-lg font-semibold">{{ item.title }}</h3>
          <p class="text-sm leading-relaxed text-gray-400">{{ item.desc }}</p>
        </UCard>
      </div>
    </UContainer>
  </section>
</template>

<script setup>
const { t } = useI18n()
const items = computed(() => [
  { icon: 'i-heroicons-banknotes', title: t('features.free.title'), desc: t('features.free.desc') },
  { icon: 'i-heroicons-link', title: t('features.citations.title'), desc: t('features.citations.desc') },
  { icon: 'i-heroicons-rectangle-group', title: t('features.multi.title'), desc: t('features.multi.desc') },
  { icon: 'i-heroicons-bars-arrow-up', title: t('features.ranking.title'), desc: t('features.ranking.desc') },
  { icon: 'i-heroicons-command-line', title: t('features.code.title'), desc: t('features.code.desc') },
])
</script>
