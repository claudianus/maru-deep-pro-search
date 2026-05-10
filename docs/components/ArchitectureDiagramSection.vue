<template>
  <section class="border-t border-gray-800/60 py-20">
    <UContainer>
      <div class="mb-4 text-center">
        <UBadge color="indigo" variant="subtle" size="lg" class="mb-4">Architecture</UBadge>
        <h2 class="text-3xl font-bold tracking-tight sm:text-4xl">{{ $t('arch.title') }}</h2>
        <p class="mt-3 text-gray-400">{{ $t('arch.desc') }}</p>
      </div>

      <div class="mt-12">
        <div class="rounded-2xl border border-gray-800 bg-gray-950 p-4 md:p-8">
          <ClientOnly>
            <MermaidDiagram :definition="diagram" />
            <template #fallback>
              <div class="flex items-center justify-center py-12 text-sm text-gray-500">Loading diagram...</div>
            </template>
          </ClientOnly>
        </div>
      </div>
    </UContainer>
  </section>
</template>

<script setup>
const diagram = `
flowchart TD
    A[User Query] --> B[Query Expander]
    B --> C[SearchEngineRegistry]
    C --> D[DuckDuckGo Lite]
    C --> E[DuckDuckGo HTML]
    C --> F[Future Engine...]
    D & E & F --> G[Result Deduplicator]
    G --> H[BM25 Ranker]
    H --> I{"Authority Boost?<br/>+2.0"}
    H --> J{"Freshness?<br/>+1.5"}
    H --> K{"Code Density?<br/>+1.0"}
    I & J & K --> L[Ranked Results]
    L --> M[Content Extractor]
    M --> N[trafilatura]
    M --> O[htmldate]
    M --> P[Code Analyzer]
    N & O & P --> Q[Smart Synthesizer]
    Q --> R["Cited Answer<br/>with [1], [2], [3]"]

    style A fill:#1e1b4b,stroke:#6366f1,color:#e2e2ea
    style R fill:#1e1b4b,stroke:#6366f1,color:#e2e2ea
    style H fill:#312e81,stroke:#8b5cf6,color:#e2e2ea
    style Q fill:#312e81,stroke:#8b5cf6,color:#e2e2ea
    style D fill:#0f172a,stroke:#475569,color:#94a3b8
    style E fill:#0f172a,stroke:#475569,color:#94a3b8
    style F fill:#0f172a,stroke:#475569,color:#94a3b8
    style N fill:#0f172a,stroke:#475569,color:#94a3b8
    style O fill:#0f172a,stroke:#475569,color:#94a3b8
    style P fill:#0f172a,stroke:#475569,color:#94a3b8
    style B fill:#1e293b,stroke:#64748b,color:#cbd5e1
    style C fill:#1e293b,stroke:#64748b,color:#cbd5e1
    style G fill:#1e293b,stroke:#64748b,color:#cbd5e1
    style I fill:#1e293b,stroke:#64748b,color:#cbd5e1
    style J fill:#1e293b,stroke:#64748b,color:#cbd5e1
    style K fill:#1e293b,stroke:#64748b,color:#cbd5e1
    style L fill:#1e293b,stroke:#64748b,color:#cbd5e1
    style M fill:#1e293b,stroke:#64748b,color:#cbd5e1
`
</script>
