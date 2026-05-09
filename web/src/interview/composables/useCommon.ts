import { computed, ref } from 'vue';
import VERTC, { MediaType } from '@volcengine/rtc';
import { Modal } from 'ant-design-vue';
import RtcClient from '../services/RtcClient';
import { createRtcListeners } from '../services/listeners';
import { useDeviceStore } from '../stores/device';
import { useRoomStore } from '../stores/room';
import logger from '../utils/logger';

export const ABORT_VISIBILITY_CHANGE = 'abortVisibilityChange';

export const useScene = () => {
  const room = useRoomStore();
  return computed(() => room.sceneConfigMap[room.scene] || {});
};

export const useRTC = () => {
  const room = useRoomStore();
  return computed(() => room.rtcConfigMap[room.scene] || {});
};

export const useDeviceState = () => {
  const room = useRoomStore();
  const device = useDeviceStore();

  const isAudioPublished = computed(() => room.localUser.publishAudio);
  const isVideoPublished = computed(() => room.localUser.publishVideo);
  const isScreenPublished = computed(() => room.localUser.publishScreen);

  const queryDevices = async (type: MediaType) => {
    const mediaDevices = await RtcClient.getDevices({ audio: type === MediaType.AUDIO, video: type === MediaType.VIDEO });
    if (type === MediaType.AUDIO) {
      device.updateMediaInputs({ audioInputs: mediaDevices.audioInputs, audioOutputs: mediaDevices.audioOutputs });
      device.updateSelectedDevice({ selectedMicrophone: mediaDevices.audioInputs[0]?.deviceId });
    } else {
      device.updateMediaInputs({ videoInputs: mediaDevices.videoInputs });
      device.updateSelectedDevice({ selectedCamera: mediaDevices.videoInputs[0]?.deviceId });
    }
    return mediaDevices;
  };

  const switchMic = async (controlPublish = true) => {
    if (controlPublish) {
      await (!isAudioPublished.value ? RtcClient.publishStream(MediaType.AUDIO) : RtcClient.unpublishStream(MediaType.AUDIO));
    }
    await queryDevices(MediaType.AUDIO);
    await (!isAudioPublished.value ? RtcClient.startAudioCapture() : RtcClient.stopAudioCapture());
    room.updateLocalUser({ publishAudio: !isAudioPublished.value });
  };

  const switchCamera = async (controlPublish = true) => {
    if (controlPublish) {
      await (!isVideoPublished.value ? RtcClient.publishStream(MediaType.VIDEO) : RtcClient.unpublishStream(MediaType.VIDEO));
    }
    await queryDevices(MediaType.VIDEO);
    await (!isVideoPublished.value ? RtcClient.startVideoCapture() : RtcClient.stopVideoCapture());
    room.updateLocalUser({ publishVideo: !isVideoPublished.value });
  };

  const switchScreenCapture = async (controlPublish = true) => {
    try {
      !isScreenPublished.value ? sessionStorage.setItem(ABORT_VISIBILITY_CHANGE, 'true') : sessionStorage.removeItem(ABORT_VISIBILITY_CHANGE);
      if (controlPublish) {
        await (!isScreenPublished.value ? RtcClient.publishScreenStream(MediaType.VIDEO) : RtcClient.unpublishScreenStream(MediaType.VIDEO));
      }
      await (!isScreenPublished.value ? RtcClient.startScreenCapture() : RtcClient.stopScreenCapture());
      room.updateLocalUser({ publishScreen: !isScreenPublished.value });
    } catch {
      console.warn('Not Authorized.');
    }
    sessionStorage.removeItem(ABORT_VISIBILITY_CHANGE);
  };

  return { isAudioPublished, isVideoPublished, isScreenPublished, switchMic, switchCamera, switchScreenCapture, queryDevices };
};

export const useJoin = () => {
  const room = useRoomStore();
  const device = useDeviceStore();
  const joining = ref(false);
  const { switchMic } = useDeviceState();

  const handleAIGCModeStart = async () => {
    const id = room.currentSceneConfig.id;
    if (room.isAIGCEnable) {
      await RtcClient.stopAgent(id);
      room.clearCurrentMsg();
      await RtcClient.startAgent(id);
    } else {
      await RtcClient.startAgent(id);
    }
    room.updateAIGCState(true);
  };

  const dispatchJoin = async () => {
    if (joining.value) return;
    const isSupported = await VERTC.isSupported();
    if (!isSupported) {
      Modal.error({ title: '不支持 RTC', content: '您的浏览器可能不支持 RTC 功能，请尝试更换浏览器或升级浏览器后再重试。' });
      return;
    }
    joining.value = true;
    await RtcClient.createEngine();
    RtcClient.addEventListeners(createRtcListeners());
    await RtcClient.joinRoom();
    const mediaDevices = await RtcClient.getDevices({ audio: true, video: false });
    room.localJoinRoom({
      roomId: RtcClient.basicInfo.room_id,
      user: { username: RtcClient.basicInfo.user_id, userId: RtcClient.basicInfo.user_id },
    });
    device.updateSelectedDevice({ selectedMicrophone: mediaDevices.audioInputs[0]?.deviceId, selectedCamera: mediaDevices.videoInputs[0]?.deviceId });
    device.updateMediaInputs(mediaDevices);
    joining.value = false;
    if (device.devicePermissions.audio) {
      try {
        await switchMic();
      } catch {
        logger.debug('No permission for mic');
      }
    }
    await handleAIGCModeStart();
  };

  return { joining, dispatchJoin };
};

export const useLeave = () => {
  const room = useRoomStore();
  return async () => {
    await Promise.allSettled([RtcClient.stopAudioCapture(), RtcClient.stopScreenCapture(), RtcClient.stopVideoCapture()]);
    await RtcClient.stopAgent(room.currentSceneConfig.id);
    await RtcClient.leaveRoom();
    room.clearHistoryMsg();
    room.clearCurrentMsg();
    room.localLeaveRoom();
    room.updateAIGCState(false);
  };
};
