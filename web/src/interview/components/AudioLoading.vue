<template>
  <div class="audio-loading">
    <span v-for="item in 3" :key="item" />
  </div>
</template>

<style scoped lang="less">
.audio-loading {
  display: flex;
  align-items: center;
  gap: 3px;
  color: #1664ff;
}
.audio-loading span {
  width: 3px;
  height: 12px;
  border-radius: 2px;
  background: currentColor;
  animation: audio-wave 0.8s infinite ease-in-out;
}
.audio-loading span:nth-child(2) {
  animation-delay: 0.12s;
}
.audio-loading span:nth-child(3) {
  animation-delay: 0.24s;
}
@keyframes audio-wave {
  0%, 100% { transform: scaleY(0.5); }
  50% { transform: scaleY(1.2); }
}
</style>
