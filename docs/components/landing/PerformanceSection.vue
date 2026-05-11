<template>
  <section class="border-t border-gray-800/60 py-16">
    <UContainer>
      <SectionTitle>{{ title }}</SectionTitle>
      <DarkTable :columns="columns" :rows="metrics">
        <template #target="{ value }">
          <span class="text-emerald-400">{{ value }}</span>
        </template>
      </DarkTable>
    </UContainer>
  </section>
</template>

<script setup lang="ts">
import type { PerformanceMetric } from '~/types';
import SectionTitle from '~/components/ui/SectionTitle.vue'
import DarkTable from '~/components/ui/DarkTable.vue'

const columns = [
  { key: 'metric', label: 'Metric' },
  { key: 'target', label: 'Target', class: 'text-emerald-400' },
  { key: 'implementation', label: 'Implementation' },
];

defineProps<{
  title: string;
  metrics: PerformanceMetric[];
}>();
</script>
