<template>
  <div class="loader">
    <span v-for="item in 3" :key="item" class="dot" />
  </div>
</template>

<style scoped lang="less">
.loader {
  display: flex;
  gap: 3px;
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: currentColor;
  animation: glow 0.9s infinite;
}
.dot:nth-child(2) {
  animation-delay: 0.2s;
}
.dot:nth-child(3) {
  animation-delay: 0.4s;
}
</style>
