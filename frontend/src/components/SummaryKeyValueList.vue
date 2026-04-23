<script setup lang="ts">
export type SummaryItem = {
  label: string;
  value: string | number;
};

defineProps<{
  items: SummaryItem[];
}>();
</script>

<template>
  <div class="summary-stack">
    <div v-for="item in items" :key="item.label" class="summary-row">
      <span>{{ item.label }}</span>
      <strong>{{ item.value }}</strong>
    </div>
  </div>
</template>
