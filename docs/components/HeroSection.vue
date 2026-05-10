<template>
  <section class="relative overflow-hidden pb-20 pt-16">
    <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-900/20 via-gray-950 to-gray-950" />
    <UContainer class="relative">
      <div class="mx-auto max-w-3xl text-center">
        <UBadge color="indigo" variant="subtle" size="lg" class="mb-6">
          MCP Server
        </UBadge>
        <h1 class="mb-6 text-4xl font-extrabold tracking-tight sm:text-6xl">
          <span class="bg-gradient-to-r from-indigo-400 via-violet-400 to-fuchsia-400 bg-clip-text text-transparent">
            {{ $t('hero.title') }}
          </span>
        </h1>
        <p class="mb-10 text-lg text-gray-400 sm:text-xl">
          {{ $t('hero.subtitle') }}
        </p>

        <div class="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
          <div class="flex w-full max-w-md items-center gap-2 rounded-lg border border-gray-700 bg-gray-900/80 px-4 py-3 font-mono text-sm backdrop-blur">
            <span class="text-gray-500">$</span>
            <span class="text-gray-200">pip install maru-search</span>
            <UButton
              :icon="copied ? 'i-heroicons-check' : 'i-heroicons-document-duplicate'"
              color="gray"
              variant="ghost"
              size="xs"
              class="ml-auto"
              @click="copyInstall"
            />
          </div>
        </div>

        <div class="mt-8 flex justify-center gap-3">
          <UButton
            :label="$t('hero.github')"
            icon="i-heroicons-code-bracket-square"
            to="https://github.com/claudianus/maru-search"
            target="_blank"
            color="gray"
            variant="solid"
          />
          <UButton
            :label="$t('hero.pypi')"
            icon="i-heroicons-cube"
            to="https://pypi.org/project/maru-search/"
            target="_blank"
            color="indigo"
            variant="solid"
          />
        </div>
      </div>
    </UContainer>
  </section>
</template>

<script setup>
const copied = ref(false)
function copyInstall() {
  navigator.clipboard.writeText('pip install maru-search')
  copied.value = true
  setTimeout(() => copied.value = false, 2000)
}
</script>
