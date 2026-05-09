<template>
  <button class="invoke-btn" :disabled="loading" @click="$emit('click')">
    <span v-if="loading" class="spinner" />
    {{ loading ? '进入中...' : '开始通话' }}
  </button>
</template>

<script setup lang="ts">
defineProps<{ loading?: boolean }>();
defineEmits<{ click: [] }>();
</script>

<style scoped lang="less">
.invoke-btn {
  min-width: 160px;
  height: 48px;
  border: none;
  border-radius: 999px;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  background: linear-gradient(56.59deg, #3c73ff 15.53%, #6e41ee 62.28%, #d641ee 90.32%);
  box-shadow: 0 12px 28px rgba(60, 115, 255, 0.24);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.invoke-btn:disabled {
  opacity: 0.75;
  cursor: not-allowed;
}
.spinner {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.5);
  border-top-color: #fff;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
