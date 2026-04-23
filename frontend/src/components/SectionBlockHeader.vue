<script setup lang="ts">
defineProps<{
  title: string;
  description?: string;
}>();
</script>

<template>
  <div class="panel-head compact-head">
    <div>
      <h2>{{ title }}</h2>
      <p v-if="description" class="helper-text">{{ description }}</p>
    </div>
    <slot />
  </div>
</template>
