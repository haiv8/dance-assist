<template>
  <div class="records-list dense-list">
    <IssueRow
      v-for="item in issues"
      :key="item.id"
      :item="item"
      :active="selectedIssueId === item.id"
      :selected="selectedPipelineIds.has(item.pipelineId)"
      :can-delete="canDeletePipelineId(item.pipelineId)"
      :bulk-deleting="bulkDeleting"
      :deleting="deletingId === item.pipelineId"
      @toggle-issue="$emit('toggleIssue', $event)"
      @toggle-selection="$emit('toggleSelection', $event)"
      @open-record="$emit('openRecord', $event)"
      @jump-compare="$emit('jumpCompare', $event)"
      @delete-pipeline="$emit('deletePipeline', $event)"
    />
  </div>
</template>

<script setup lang="ts">
import IssueRow from "./IssueRow.vue";
import type { IssueReplayItem } from "../../types/video";

defineProps<{
  issues: IssueReplayItem[];
  selectedIssueId: string;
  selectedPipelineIds: Set<string>;
  bulkDeleting: boolean;
  deletingId: string;
  canDeletePipelineId: (pipelineId: string) => boolean;
}>();

defineEmits<{
  toggleIssue: [issueId: string];
  toggleSelection: [pipelineId: string];
  openRecord: [issue: IssueReplayItem];
  jumpCompare: [issue: IssueReplayItem];
  deletePipeline: [pipelineId: string];
}>();
</script>
