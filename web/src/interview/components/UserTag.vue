<template>
  <div class="tag" :class="className">{{ name }}</div>
</template>

<script setup lang="ts">
defineProps<{ name?: string; className?: string }>();
</script>

<style scoped lang="less">
.tag {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 9;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.45);
  color: #fff;
  font-size: 12px;
  line-height: 20px;
}
</style>
