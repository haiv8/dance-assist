<template>
  <div class="feedback-state empty-state-guide" data-tone="empty">
    <strong class="feedback-state-title">{{ title }}</strong>
    <span class="feedback-state-copy">{{ copy }}</span>
    <div v-if="$slots.actions" class="empty-state-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
  copy: string;
}>();
</script>

<style scoped>
.empty-state-guide {
  justify-items: center;
  text-align: center;
}

.empty-state-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
  margin-top: 4px;
}
</style>
