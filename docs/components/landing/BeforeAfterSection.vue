<template>
  <section class="border-t border-gray-800/60 py-16">
    <UContainer>
      <SectionTitle>{{ title }}</SectionTitle>
      <DarkTable :columns="columns" :rows="rows">
        <template #after="{ value }">
          <span class="text-gray-200">{{ value }}</span>
        </template>
      </DarkTable>
    </UContainer>
  </section>
</template>

<script setup lang="ts">
import type { BeforeAfterRow } from '~/types';
import SectionTitle from '~/components/ui/SectionTitle.vue'
import DarkTable from '~/components/ui/DarkTable.vue'

const columns = [
  { key: 'before', label: 'Before' },
  { key: 'after', label: 'After', class: 'text-indigo-300' },
];

defineProps<{
  title: string;
  rows: BeforeAfterRow[];
}>();
</script>
