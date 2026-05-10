<template>
  <section class="border-t border-gray-800/60 py-20">
    <UContainer>
      <div class="mb-12 text-center">
        <h2 class="text-3xl font-bold tracking-tight">{{ $t('arch.title') }}</h2>
        <p class="mt-2 text-gray-400">{{ $t('arch.desc') }}</p>
      </div>
      <div class="mx-auto max-w-2xl">
        <div class="rounded-xl border border-gray-800 bg-gray-950 p-6 font-mono text-sm leading-relaxed text-gray-300">
          <div class="text-gray-500">src/maru_search/</div>
          <div class="pl-4"><span class="text-indigo-400">├──</span> server.py <span class="text-gray-600"># MCP server</span></div>
          <div class="pl-4"><span class="text-indigo-400">├──</span> config.py <span class="text-gray-600"># Runtime config</span></div>
          <div class="pl-4"><span class="text-indigo-400">├──</span> tools.py <span class="text-gray-600"># Tool registry</span></div>
          <div class="pl-4"><span class="text-indigo-400">├──</span> engines/</div>
          <div class="pl-8"><span class="text-indigo-400">├──</span> registry.py <span class="text-gray-600"># Engine factory</span></div>
          <div class="pl-8"><span class="text-indigo-400">├──</span> base.py <span class="text-gray-600"># ABC</span></div>
          <div class="pl-8"><span class="text-indigo-400">└──</span> duckduckgo.py</div>
          <div class="pl-4"><span class="text-indigo-400">├──</span> research/</div>
          <div class="pl-8"><span class="text-indigo-400">├──</span> deep.py <span class="text-gray-600"># Pipeline</span></div>
          <div class="pl-8"><span class="text-indigo-400">├──</span> ranker.py <span class="text-gray-600"># BM25</span></div>
          <div class="pl-8"><span class="text-indigo-400">└──</span> expander.py</div>
          <div class="pl-4"><span class="text-indigo-400">├──</span> extraction/</div>
          <div class="pl-8"><span class="text-indigo-400">├──</span> code.py <span class="text-gray-600"># 21 langs</span></div>
          <div class="pl-8"><span class="text-indigo-400">└──</span> content.py</div>
          <div class="pl-4"><span class="text-indigo-400">└──</span> utils/</div>
          <div class="pl-8"><span class="text-indigo-400">├──</span> url.py</div>
          <div class="pl-8"><span class="text-indigo-400">└──</span> retry.py</div>
        </div>
      </div>
    </UContainer>
  </section>
</template>
