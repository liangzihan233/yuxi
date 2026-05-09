<template>
  <div class="card" :class="{ fullScreen: room.isFullScreen }">
    <UserTag v-if="showUserTag" :name="scene.name || scene.id" />
    <div class="avatar">
      <div v-if="showStatus" class="aiStatus">
        <div class="barContainer">
          <span v-for="item in 3" :key="item" class="bar" />
        </div>
        {{ room.isAITalking ? '说话中' : '聆听中' }}
      </div>
      <img :src="DoubaoAvatar || userAvatar" alt="avatar" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoomStore } from '../stores/room';
import UserTag from './UserTag.vue';
import DoubaoAvatar from './assets/doubao.png';
import userAvatar from './assets/userAvatar.png';

withDefaults(defineProps<{ showStatus?: boolean; showUserTag?: boolean }>(), {
  showStatus: false,
  showUserTag: false,
});

const room = useRoomStore();
const scene = computed(() => room.currentSceneConfig);
</script>

<style scoped lang="less">
.card {
  position: absolute;
  inset: 0;
  text-align: center;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 18px;
  padding: 16px;
  box-sizing: border-box;

  .avatar {
    position: relative;
    border-radius: 50%;
    width: 118px;
    height: 118px;
    display: flex;
    align-items: center;
    justify-content: center;

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      border-radius: 50%;
    }
  }

  .aiStatus {
    position: absolute;
    top: 6px;
    left: calc(100% - 25px);
    transform: none;
    box-shadow: 0 2px 16px 0 #00000014;
    min-width: 74px;
    height: 32px;
    padding: 0 10px;
    border-radius: 999px;
    color: #635bff;
    font-weight: 500;
    font-size: 12px;
    white-space: nowrap;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 6px;
    background: #ffffff;
    z-index: 9
  }

  .barContainer {
    display: flex;
    gap: 2px;
  }

  .bar {
    width: 4px;
    height: 9px;
    border-radius: 6px;
    animation: shake 1s ease infinite;
    background-color: #4f4fff;
  }

  .bar:nth-child(1) { animation-delay: -0.4s; }
  .bar:nth-child(2) { animation-delay: -0.2s; }
}

.fullScreen {
  .avatar {
    width: 96px;
    height: 96px;
  }

  .aiStatus {
    min-width: 68px;
    height: 28px;
    left: calc(100% - 8px);
    top: 4px;
    font-size: 11px;
    padding: 0 8px;
  }

  .bar {
    width: 4px;
    height: 8px;
  }
}

@keyframes shake {
  0%, 100% { transform: scaleY(1); }
  50% { transform: scaleY(0.5); }
}
</style>
