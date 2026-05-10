<template>
  <section class="border-t border-gray-800/60 py-20">
    <UContainer>
      <div class="mb-4 text-center">
        <UBadge color="emerald" variant="subtle" size="lg" class="mb-4">Zero API Cost</UBadge>
        <h2 class="text-3xl font-bold tracking-tight sm:text-4xl">{{ $t('codeShowcase.title') }}</h2>
        <p class="mt-3 text-gray-400">{{ $t('codeShowcase.subtitle') }}</p>
      </div>

      <div class="mt-12 mx-auto max-w-3xl">
        <!-- Tabs -->
        <div class="flex gap-2 rounded-t-xl border border-gray-800 bg-gray-900/60 p-2">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="rounded-lg px-4 py-2 text-sm font-medium transition-colors"
            :class="activeTab === tab.key ? 'bg-indigo-500/10 text-indigo-400' : 'text-gray-500 hover:text-gray-300'"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>

        <!-- Code block -->
        <div class="border border-t-0 border-gray-800 bg-gray-950">
          <div class="flex items-center justify-between px-4 pt-4">
            <div class="flex gap-1.5">
              <div class="h-3 w-3 rounded-full bg-red-500/20" />
              <div class="h-3 w-3 rounded-full bg-amber-500/20" />
              <div class="h-3 w-3 rounded-full bg-emerald-500/20" />
            </div>
            <UButton
              :icon="copiedCode ? 'i-heroicons-check' : 'i-heroicons-document-duplicate'"
              color="gray"
              variant="ghost"
              size="xs"
              @click="copyCode"
            />
          </div>
          <div class="overflow-x-auto p-4">
            <div class="shiki-wrapper" v-html="highlightedCode" />
          </div>
        </div>

        <!-- Output block -->
        <div class="mt-4 rounded-xl border border-gray-800 bg-gray-950">
          <div class="flex items-center justify-between border-b border-gray-800 px-4 py-2">
            <span class="text-xs font-bold tracking-wider text-emerald-400 uppercase">Output</span>
            <UButton
              :icon="copiedOutput ? 'i-heroicons-check' : 'i-heroicons-document-duplicate'"
              color="gray"
              variant="ghost"
              size="xs"
              @click="copyOutput"
            />
          </div>
          <pre class="overflow-x-auto p-4 text-sm leading-relaxed text-gray-300 whitespace-pre-wrap">{{ currentOutput }}</pre>
        </div>
      </div>
    </UContainer>
  </section>
</template>

<script setup>
const { t } = useI18n()
const activeTab = ref('quick')
const copiedCode = ref(false)
const copiedOutput = ref(false)
const highlightedCode = ref('')

const tabs = computed(() => [
  { key: 'quick', label: t('codeShowcase.tab1') },
  { key: 'deep', label: t('codeShowcase.tab2') },
  { key: 'cited', label: t('codeShowcase.tab3') },
])

const codeMap = computed(() => ({
  quick: t('codeShowcase.code1'),
  deep: t('codeShowcase.code2'),
  cited: t('codeShowcase.code3'),
}))

const outputMap = computed(() => ({
  quick: t('codeShowcase.output1'),
  deep: t('codeShowcase.output2'),
  cited: t('codeShowcase.output3'),
}))

const currentCode = computed(() => codeMap.value[activeTab.value])
const currentOutput = computed(() => outputMap.value[activeTab.value])

async function highlight() {
  const { codeToHtml } = await import('shiki')
  highlightedCode.value = await codeToHtml(currentCode.value, {
    lang: 'python',
    theme: 'github-dark'
  })
}

watch(activeTab, highlight, { immediate: true })

function copyCode() {
  navigator.clipboard.writeText(currentCode.value)
  copiedCode.value = true
  setTimeout(() => copiedCode.value = false, 2000)
}

function copyOutput() {
  navigator.clipboard.writeText(currentOutput.value)
  copiedOutput.value = true
  setTimeout(() => copiedOutput.value = false, 2000)
}
</script>

<style>
.shiki-wrapper pre {
  margin: 0;
  background: transparent !important;
}
</style>
