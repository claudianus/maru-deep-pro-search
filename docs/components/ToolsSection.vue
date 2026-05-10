<template>
  <section class="border-t border-gray-800/60 py-20">
    <UContainer>
      <div class="mb-12 text-center">
        <h2 class="text-3xl font-bold tracking-tight">{{ $t('tools.title') }}</h2>
        <p class="mt-2 text-gray-400">{{ $t('tools.desc') }}</p>
      </div>
      <div class="grid gap-4 sm:grid-cols-2">
        <div
          v-for="(tool, i) in tools"
          :key="i"
          class="flex items-start gap-4 rounded-xl border border-gray-800 bg-gray-900/30 p-5 transition-all hover:border-indigo-500/30 hover:bg-gray-800/40"
        >
          <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-gray-800 text-xs font-bold text-indigo-400 ring-1 ring-gray-700">
            {{ i + 1 }}
          </div>
          <div>
            <h3 class="mb-1 font-mono text-sm font-semibold text-indigo-300">{{ tool.name }}</h3>
            <p class="text-sm text-gray-400">{{ tool.desc }}</p>
          </div>
        </div>
      </div>
    </UContainer>
  </section>
</template>

<script setup>
const { t } = useI18n()
const tools = computed(() => [
  { name: 'answer', desc: t('tools.answer') },
  { name: 'web_search', desc: t('tools.web_search') },
  { name: 'search_with_citations', desc: t('tools.search_with_citations') },
  { name: 'fetch_page', desc: t('tools.fetch_page') },
  { name: 'fetch_bulk', desc: t('tools.fetch_bulk') },
  { name: 'deep_research', desc: t('tools.deep_research') },
  { name: 'stealthy_fetch', desc: t('tools.stealthy_fetch') },
  { name: 'parallel_search', desc: t('tools.parallel_search') },
])
</script>
