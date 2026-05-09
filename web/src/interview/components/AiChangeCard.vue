<template>
  <div class="wrapper">
    <div class="scene-card">
      <img :src="DoubaoAvatar" alt="scene" />
      <div>
        <div class="title">{{ '访谈助手' }}</div>
        <div class="desc">点击开始通话，进入实时对话</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import DoubaoAvatar from './assets/doubao.png';
</script>

<style scoped lang="less">
.wrapper {
  width: 100%;
}
.scene-card {
  width: 320px;
  min-height: 96px;
  border-radius: 24px;
  background: #fff;
  border: 1px solid #eaedf1;
  box-shadow: 0 12px 40px rgba(22, 100, 255, 0.08);
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  margin: 0 auto;
}
.scene-card img {
  width: 56px;
  height: 56px;
  border-radius: 50%;
}
.title {
  color: #0c0d0e;
  font-weight: 600;
  font-size: 18px;
  line-height: 26px;
}
.desc {
  margin-top: 4px;
  color: #737a87;
  font-size: 13px;
}
</style>
