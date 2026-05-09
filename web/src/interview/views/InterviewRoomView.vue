<template>
  <div class="interview-room">
    <!-- 加载中 -->
    <div v-if="loading" class="center-state">
      <a-spin size="large" />
      <p class="loading-text">正在加载访谈信息...</p>
    </div>

    <!-- 错误 -->
    <div v-else-if="error" class="center-state">
      <a-result status="error" :title="error" />
    </div>

    <!-- 准备开始 -->
    <div v-else-if="!isJoined" class="center-state prepare">
      <AiChangeCard />
      <div class="info">
        <h2>{{ interview?.name || '语音访谈' }}</h2>
        <p class="project">项目编号：{{ interview?.project_id || '-' }}</p>
        <p v-if="interview?.valid_from && interview?.valid_until" class="validity">
          有效期：{{ formatDate(interview.valid_from) }} 至 {{ formatDate(interview.valid_until) }}
        </p>
        <p class="hint">本次访谈为语音对话形式，请确保麦克风设备正常</p>
      </div>
      <InvokeButton :loading="joining" @click="handleStart" />
    </div>

    <!-- 访谈中：保持与 rtc-aigc-demo/web-vue 房间页一致 -->
    <div v-else class="rtc-demo-room" :class="{ mobile: isMobileView }">
      <div v-if="isMobileView" id="mobile-local-player" class="mobilePlayer" />

      <AiAvatarCard v-if="!(isMobileView && room.isShowSubtitle)" :show-user-tag="!room.isShowSubtitle" :show-status="!room.isShowSubtitle" />

      <div v-if="!isMobileView" class="desktop-room-layout">
        <div class="stage-layout">
          <div class="main-stage" :class="{ 'show-ai-stage': isAiPrimary }" @click="swapStagePanels">
            <template v-if="isAiPrimary">
              <div class="ai-stage">
                <AiAvatarCard :show-user-tag="false" show-status />
              </div>
            </template>
            <template v-else>
              <div class="camera-wrapper camera-wrapper-main">
                <UserTag name="我" />
                <div v-if="isVideoPublished || isScreenPublished" class="local-player-set">本地画面</div>
                <div id="local-video-player" class="camera-player" :class="{ hidden: !isVideoPublished }" />
                <div id="local-screen-player" class="camera-player" :class="{ hidden: !isScreenPublished }" />
              </div>
            </template>
          </div>

          <div class="floating-panel" @click.stop="swapStagePanels">
            <div v-if="isAiPrimary" class="camera-wrapper camera-wrapper-float">
              <UserTag name="我" />
              <div v-if="isVideoPublished || isScreenPublished" class="local-player-set">本地画面</div>
              <div id="floating-video-player" class="camera-player" :class="{ hidden: !isVideoPublished }" />
              <div id="local-screen-player" class="camera-player" :class="{ hidden: !isScreenPublished }" />
            </div>
            <div v-else class="ai-mini-stage">
              <AiAvatarCard :show-user-tag="false" show-status />
            </div>
            <div class="floating-panel-mask">
              <span class="mask-badge">点击切换主画面</span>
              <span class="mask-text">{{ isAiPrimary ? '切换为用户主画面' : '切换为 AI 主画面' }}</span>
            </div>
          </div>

          <div class="toolbar-btns audio-controller" :class="{ column: isMobileView }">
            <img :src="isAudioPublished ? MicOpenSVG : MicCloseSVG" class="toolbar-btn" alt="mic" @click="switchMic(true)" />
            <img :src="isVideoPublished ? CameraOpenSVG : CameraCloseSVG" class="toolbar-btn" alt="camera" @click="switchCamera(true)" />
            <img :src="LeaveRoomSVG" class="toolbar-btn" alt="leave" @click="handleEnd" />
          </div>

          <div class=" audio-controller-stage">
            <AudioLoading v-if="room.isAITalking" />
            <span v-else-if="room.isAIThinking">AI 思考中</span>
            <span v-else>AI 在线</span>
            <button v-if="room.currentSceneConfig.isInterruptMode && isAudioPublished && room.isAITalking" @click="interruptAgent">打断</button>
          </div>
        </div>

        <div ref="conversationRef" class="conversation live-conversation-panel">
          <div class="conversation-header">
            <div class="live-header-row">
              <div class="live-status-badge">
                <span class="live-dot" />
                LIVE
              </div>
              <div class="live-header-tags">
                <span class="header-tag">实时记录</span>
                <span class="header-tag" :class="networkClass">{{ networkText }}</span>
                <span class="header-tag ai-tag">{{ room.isAITalking ? 'AI 说话中' : room.isAIThinking ? 'AI 思考中' : 'AI 在线' }}</span>
              </div>
            </div>
            <div class="conversation-title">实时对话</div>
            <div class="conversation-subtitle">访谈内容记录面板</div>
          </div>
          <div v-if="!isAIReady" class="aiReadying">
            <HorizonLoading />
            AI 准备中, 请稍侯
          </div>
          <template v-if="room.isShowSubtitle">
            <div
              v-for="(msg, index) in room.msgHistory"
              :key="`msg-container-${index}`"
              class="mobileLine"
              :style="{ justifyContent: msg.user === room.localUser.userId && isMobileView ? 'flex-end' : '' }"
            >
              <div v-if="!isMobileView" class="msgName">
                <div class="avatar" :class="{ user: msg.user === room.localUser.userId }">
                  {{ msg.user === room.localUser.userId ? '我' : 'AI' }}
                </div>
              </div>
              <div class="sentence" :class="msg.user === room.localUser.userId ? 'user' : 'robot'">
                <div class="content">
                  {{ msg.value }}
                  <div class="loading-wrapper">
                    <HorizonLoading v-if="isAIReady && isLoadingMsg(msg.user) && index === room.msgHistory.length - 1" />
                  </div>
                </div>
                <a-tag v-if="msg.user !== room.localUser.userId && msg.isInterrupted" class="interruptTag">已打断</a-tag>
              </div>
            </div>
          </template>
        </div>
      </div>

      <div v-else ref="conversationRef" class="conversation" :class="{ fullScreen: room.isFullScreen, mobileConversation: isMobileView }">
        <div v-if="!isAIReady" class="aiReadying">
          <HorizonLoading />
          AI 准备中, 请稍侯
        </div>
        <template v-if="room.isShowSubtitle">
          <div
            v-for="(msg, index) in room.msgHistory"
            :key="`msg-container-${index}`"
            class="mobileLine"
            :style="{ justifyContent: msg.user === room.localUser.userId && isMobileView ? 'flex-end' : '' }"
          >
            <div v-if="!isMobileView" class="msgName">
              <div class="avatar" :class="{ user: msg.user === room.localUser.userId }">
                {{ msg.user === room.localUser.userId ? '我' : 'AI' }}
              </div>
            </div>
            <div class="sentence" :class="msg.user === room.localUser.userId ? 'user' : 'robot'">
              <div class="content">
                {{ msg.value }}
                <div class="loading-wrapper">
                  <HorizonLoading v-if="isAIReady && isLoadingMsg(msg.user) && index === room.msgHistory.length - 1" />
                </div>
              </div>
              <a-tag v-if="msg.user !== room.localUser.userId && msg.isInterrupted" class="interruptTag">已打断</a-tag>
            </div>
          </div>
        </template>
      </div>

    </div>

    <!-- 已结束 -->
    <div v-if="ended" class="modal-overlay">
      <div class="ended-card">
        <h2>访谈已结束</h2>
        <p>感谢您的参与，您的回答对我们非常重要。</p>
        <a-button type="primary" size="large" @click="goHome">返回首页</a-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import VERTC, { MediaType, VideoRenderMode } from '@volcengine/rtc'
import { message } from 'ant-design-vue'

import { interviewApi } from '@/apis/interview_api'
import RtcClient from '../services/RtcClient'
import { useRoomStore } from '../stores/room'
import { useDeviceStore } from '../stores/device'
import { createRtcListeners } from '../services/listeners'
import { useMessageHandler, COMMAND, INTERRUPT_PRIORITY } from '../utils/handler'
import { isMobile } from '../utils/utils'

import AiAvatarCard from '../components/AiAvatarCard.vue'
import AiChangeCard from '../components/AiChangeCard.vue'
import InvokeButton from '../components/InvokeButton.vue'
import AudioLoading from '../components/AudioLoading.vue'
import HorizonLoading from '../components/HorizonLoading.vue'
import UserTag from '../components/UserTag.vue'
import CameraOpenSVG from '../components/assets/CameraOpen.svg'
import CameraCloseSVG from '../components/assets/CameraClose.svg'
import MicCloseSVG from '../components/assets/MicClose.svg'
import MicOpenSVG from '../components/assets/MicOpen.svg'
import LeaveRoomSVG from '../components/assets/LeaveRoom.svg'

const route = useRoute()
const router = useRouter()
const room = useRoomStore()
const device = useDeviceStore()
const { parser } = useMessageHandler()

const token = route.params.token as string
const loading = ref(true)
const error = ref('')
const interview = ref<any>(null)
const joining = ref(false)
const isJoined = ref(false)
const ended = ref(false)
const conversationRef = ref<HTMLDivElement>()
const isAiPrimary = ref(false)

const isMobileView = computed(() => isMobile())
const sceneName = computed(() => room.currentSceneConfig.name || interview.value?.name || '语音访谈')
const isAIReady = computed(() => room.msgHistory.length > 0)
const isAudioPublished = computed(() => !!room.localUser.publishAudio)
const isVideoPublished = computed(() => !!room.localUser.publishVideo)
const isScreenPublished = computed(() => !!room.localUser.publishScreen)

// 网络质量
const networkClass = computed(() => {
  const q = room.networkQuality
  if (q <= 1) return 'good'
  if (q <= 3) return 'normal'
  return 'bad'
})
const networkText = computed(() => {
  const q = room.networkQuality
  if (q <= 1) return '网络优秀'
  if (q <= 3) return '网络良好'
  return '网络较差'
})

function isBotMsg(msg: any) {
  const botName = room.currentSceneConfig.botName || 'InterviewBot'
  return msg.user === botName || msg.user?.includes('voiceChat_')
}

function isLoadingMsg(owner: string) {
  const botName = room.currentSceneConfig.botName || 'InterviewBot'
  return (owner === room.localUser.userId && room.isUserTalking) || ((owner === botName || owner?.includes('voiceChat_')) && room.isAITalking)
}

async function switchMic(controlPublish = true) {
  if (controlPublish) {
    await (!isAudioPublished.value ? RtcClient.publishStream(MediaType.AUDIO) : RtcClient.unpublishStream(MediaType.AUDIO))
  }
  const mediaDevices = await RtcClient.getDevices({ audio: true, video: false })
  device.updateMediaInputs({ audioInputs: mediaDevices.audioInputs, audioOutputs: mediaDevices.audioOutputs })
  device.updateSelectedDevice({ selectedMicrophone: mediaDevices.audioInputs[0]?.deviceId })
  await (!isAudioPublished.value ? RtcClient.startAudioCapture() : RtcClient.stopAudioCapture())
  room.updateLocalUser({ publishAudio: !isAudioPublished.value })
}

async function switchCamera(controlPublish = true) {
  if (controlPublish) {
    await (!isVideoPublished.value ? RtcClient.publishStream(MediaType.VIDEO) : RtcClient.unpublishStream(MediaType.VIDEO))
  }
  const mediaDevices = await RtcClient.getDevices({ audio: false, video: true })
  device.updateMediaInputs({ videoInputs: mediaDevices.videoInputs })
  device.updateSelectedDevice({ selectedCamera: mediaDevices.videoInputs[0]?.deviceId })
  await (!isVideoPublished.value ? RtcClient.startVideoCapture() : RtcClient.stopVideoCapture())
  room.updateLocalUser({ publishVideo: !isVideoPublished.value })
}

function interruptAgent() {
  RtcClient.commandAgent({
    command: COMMAND.INTERRUPT,
    agentName: room.currentSceneConfig.botName || 'InterviewBot',
    interruptMode: INTERRUPT_PRIORITY.HIGH,
  })
  room.setInterruptMsg()
}

function setVideoPlayer() {
  if (!room.localUser.username || !RtcClient.engine) return
  const targetPlayerId = isAiPrimary.value ? 'floating-video-player' : 'local-video-player'
  RtcClient.removeLocalVideoPlayer(room.localUser.username)
  if (isVideoPublished.value) {
    RtcClient.setLocalVideoPlayer(room.localUser.username, targetPlayerId, false, VideoRenderMode.RENDER_MODE_HIDDEN)
  }
}

function swapStagePanels() {
  isAiPrimary.value = !isAiPrimary.value
  nextTick(() => {
    setVideoPlayer()
  })
}

function formatDate(dateStr: string) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

async function loadInterview() {
  try {
    loading.value = true
    const data = await interviewApi.getByToken(token)
    interview.value = data
    RtcClient.interviewId = data.id
  } catch (e: any) {
    error.value = e.message || '访谈不存在或已过期'
  } finally {
    loading.value = false
  }
}

async function handleStart() {
  if (joining.value || !interview.value) return
  joining.value = true

  try {
    // 检查浏览器支持
    const supported = await VERTC.isSupported()
    if (!supported) {
      message.error('您的浏览器不支持 RTC 功能，请尝试更换浏览器')
      return
    }

    // 获取 RTC 配置（后端同时启动 VoiceChat）
    const rtcConfig = await interviewApi.getRtcConfig(interview.value.id)

    // 设置 RTC 基本信息
    RtcClient.basicInfo = {
      app_id: rtcConfig.AppId,
      room_id: rtcConfig.RoomId,
      user_id: rtcConfig.UserId,
      token: rtcConfig.Token,
    }

    // 创建引擎
    await RtcClient.createEngine()

    // 注册事件监听
    RtcClient.addEventListeners({
      ...createRtcListeners(),
      handleRoomBinaryMessageReceived: (event: any) => parser(event.message),
    })

    // 加入房间
    await RtcClient.joinRoom()

    // 获取设备
    const mediaDevices = await RtcClient.getDevices({ audio: true, video: false })
    device.updateSelectedDevice({
      selectedMicrophone: mediaDevices.audioInputs[0]?.deviceId,
    })
    device.updateMediaInputs(mediaDevices)

    // 设置场景配置
    room.updateScene('interview')
    room.updateSceneConfig({
      interview: {
        id: 'interview',
        name: interview.value.name || '语音访谈',
        botName: 'InterviewBot',
        isVision: false,
        isScreenMode: false,
        isInterruptMode: true,
      },
    })
    room.updateRTCConfig({
      interview: {
        AppId: rtcConfig.AppId,
        RoomId: rtcConfig.RoomId,
        UserId: rtcConfig.UserId,
        Token: rtcConfig.Token,
      },
    })

    room.localJoinRoom({
      roomId: rtcConfig.RoomId,
      user: { username: rtcConfig.UserId, userId: rtcConfig.UserId },
    })

    // 发布音频，与 demo 的进入房间后默认开麦一致
    if (mediaDevices.audioInputs.length) {
      await RtcClient.publishStream(MediaType.AUDIO)
      await RtcClient.startAudioCapture()
      room.updateLocalUser({ publishAudio: true })
    }

    isJoined.value = true

    // 设置 AIGC 状态
    await RtcClient.startAgent()
    room.updateAIGCState(true)

    message.success('已成功进入访谈房间')
  } catch (e: any) {
    console.error('加入房间失败:', e)
    message.error(e.message || '加入房间失败，请重试')
    RtcClient.leaveRoom()
  } finally {
    joining.value = false
  }
}

async function handleEnd() {
  try {
    await Promise.allSettled([
      RtcClient.stopAudioCapture(),
      RtcClient.stopScreenCapture(),
      RtcClient.stopVideoCapture(),
    ])
    await RtcClient.stopAgent()
    await RtcClient.leaveRoom()

    // 保存对话记录
    const transcript = room.msgHistory.map((msg) => ({
      role: isBotMsg(msg) ? 'assistant' : 'user',
      content: msg.value,
      time: msg.time,
    }))
    await interviewApi.stopInterview(interview.value.id, transcript)

    room.clearHistoryMsg()
    room.clearCurrentMsg()
    room.localLeaveRoom()
    room.updateAIGCState(false)

    ended.value = true
  } catch (e: any) {
    console.error('结束访谈失败:', e)
    message.error('结束访谈时出错')
    ended.value = true
  }
}

function goHome() {
  router.push('/')
}

onMounted(() => {
  if (!token) {
    error.value = '缺少访谈令牌'
    loading.value = false
    return
  }
  loadInterview()
})

onBeforeUnmount(() => {
  if (isJoined.value) {
    RtcClient.leaveRoom()
  }
})

watch(
  () => room.msgHistory.length,
  async () => {
    await nextTick()
    if (conversationRef.value) {
      conversationRef.value.scrollTop = conversationRef.value.scrollHeight - conversationRef.value.clientHeight
    }
  }
)

watch([isVideoPublished, () => room.isFullScreen], setVideoPlayer)
</script>

<style scoped lang="less">
.interview-room {
  width: 100vw;
  height: 100vh;
  background: linear-gradient(180deg, #f5f7fa 0%, #e8ecf1 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.center-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
  padding: 32px;
}

.loading-text {
  color: #666;
  font-size: 14px;
}

.prepare {
  .info {
    text-align: center;
    h2 {
      font-size: 22px;
      font-weight: 600;
      color: #1a1a1a;
      margin: 0 0 8px;
    }
    .project {
      font-size: 14px;
      color: #666;
      margin: 0 0 16px;
    }
    .validity {
      font-size: 13px;
      color: #666;
      margin: 0 0 8px;
    }
    .hint {
      font-size: 13px;
      color: #999;
      margin: 0;
    }
  }
}

.rtc-demo-room {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: linear-gradient(180deg, #f7f9fc 0%, #eef2f7 100%);
}

.desktop-room-layout {
  position: absolute;
  inset: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 24px;
  padding: 24px;
  box-sizing: border-box;
}

.stage-layout {
  position: relative;
  min-width: 0;
  min-height: 0;
  border-radius: 24px;
  overflow: hidden;
  background: #ffffff;
  box-shadow: 0 18px 48px rgba(31, 35, 41, 0.08);
}

.main-stage {
  position: absolute;
  inset: 0;
  cursor: pointer;
}

.main-stage.show-ai-stage {
  background: linear-gradient(180deg, #f6f9ff 0%, #eef3fb 100%);
}

.floating-panel {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 252px;
  height: 168px;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid #eaedf1;
  box-shadow: 0 12px 32px rgba(31, 35, 41, 0.16);
  background: #f6f8fb;
  z-index: 8;
  cursor: pointer;
}

.floating-panel-mask {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: linear-gradient(180deg, rgba(10, 18, 35, 0.08), rgba(10, 18, 35, 0.58));
  opacity: 0;
  transition: opacity 0.2s ease;
  pointer-events: none;
}

.floating-panel:hover .floating-panel-mask {
  opacity: 1;
}

.mask-badge {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  backdrop-filter: blur(6px);
}

.mask-text {
  color: #eef2ff;
  font-size: 13px;
  text-align: center;
}

.mobilePlayer {
  position: absolute;
  inset: 0;
}

.subTitleUserTag {
  top: 24px;
  left: 24px;
}

.declare {
  position: absolute;
  right: 24px;
  bottom: 28px;
  color: #c0c4cc;
  font-size: 12px;
}

.mobile {
  border-radius: 0;
}

.camera-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #f6f8fb;
}

.camera-wrapper-main {
  position: absolute;
  inset: 0;
  border-radius: 0;
  border: none;
}

.camera-wrapper-float {
  border-radius: 16px;
}

.ai-stage,
.ai-mini-stage {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: linear-gradient(180deg, #f7f9fc 0%, #edf2f8 100%);
}

.ai-stage :deep(.card),
.ai-mini-stage :deep(.card) {
  inset: 0;
}

.ai-mini-stage :deep(.card) {
  padding: 12px;
}

.camera-player {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.hidden {
  display: none;
}

.local-player-set {
  position: absolute;
  right: 10px;
  bottom: 10px;
  z-index: 3;
  color: #fff;
  font-size: 12px;
}

.conversation {
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  color: #0c0d0e;
}

.live-conversation-panel {
  min-height: 0;
  padding: 0px 18px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 18px 48px rgba(31, 35, 41, 0.08);
  border: 1px solid #edf1f5;
}

.conversation-header {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px 0;
  margin-bottom: 6px;
  background: rgba(255, 255, 255);
}

.live-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.live-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(245, 63, 63, 0.1);
  color: #f53f3f;
  font-size: 12px;
  font-weight: 700;
}

.live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f53f3f;
  box-shadow: 0 0 0 4px rgba(245, 63, 63, 0.12);
}

.live-header-tags {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
}

.header-tag {
  display: inline-flex;
  align-items: center;
  padding: 5px 10px;
  border-radius: 999px;
  background: #f2f3f5;
  color: #4e5969;
  font-size: 12px;
}

.header-tag.good {
  background: rgba(0, 180, 42, 0.12);
  color: #00b42a;
}

.header-tag.normal {
  background: rgba(255, 125, 0, 0.12);
  color: #ff7d00;
}

.header-tag.bad {
  background: rgba(245, 63, 63, 0.12);
  color: #f53f3f;
}

.header-tag.ai-tag {
  background: rgba(22, 100, 255, 0.1);
  color: #1664ff;
}

.conversation-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2329;
}

.conversation-subtitle {
  font-size: 12px;
  color: #86909c;
}

.aiReadying {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #737a87;
}

.mobileLine {
  display: flex;
  gap: 12px;
}

.msgName {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #737a87;
  font-size: 12px;
}

.avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #7c6cff, #4e8cff);
  color: #fff;
  font-size: 11px;
  font-weight: 600;

  &.user {
    background: linear-gradient(135deg, #20c997, #12b886);
  }
}

.sentence {
  max-width: 70%;
  padding: 8px 10px;
  border-radius: 5px;
  font-size: 12px;
  line-height: 1.4;
}

.robot {
  background: rgba(244, 247, 255, 0.5);
}

.user {
  background: rgba(22, 100, 255, 0.5);
  color: #fff;
}

.loading-wrapper {
  display: inline-flex;
  margin-left: 8px;
}

.interruptTag {
  margin-top: 6px;
}

.mobileConversation {
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 92px;
  height: 45%;
}

@media (max-width: 900px) {
  .mobileConversation {
    position: absolute;
    left: 12px;
    right: 12px;
    bottom: 92px;
    height: 45%;
  }
}

.toolbar-btns {
  position: absolute;
  left: 50%;
  bottom: 32px;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 18px;
  padding: 10px 18px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
  z-index: 20;
}

.toolbar-btn {
  width: 36px;
  height: 36px;
  cursor: pointer;
}

.column {
  flex-direction: column;
}

.audio-controller {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #737a87;
  font-size: 13px;

  button {
    border: none;
    background: #1664ff;
    color: #fff;
    border-radius: 999px;
    padding: 6px 12px;
    cursor: pointer;
  }
}

.audio-controller-stage {
  position: absolute;
  left: 20px;
  bottom: 20px;
  z-index: 9;
  padding: 5px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 10px 28px rgba(31, 35, 41, 0.12);
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;

  .ended-card {
    background: #fff;
    border-radius: 16px;
    padding: 40px 48px;
    text-align: center;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.12);

    h2 {
      font-size: 22px;
      font-weight: 600;
      margin: 0 0 12px;
      color: #1a1a1a;
    }
    p {
      font-size: 14px;
      color: #666;
      margin: 0 0 24px;
    }
  }
}
</style>
