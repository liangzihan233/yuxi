import { MediaType, StreamIndex, NetworkQuality } from '@volcengine/rtc';
import RtcClient from './RtcClient';
import { useRoomStore, type IUser } from '../stores/room';
import { useDeviceStore } from '../stores/device';
import { useMessageHandler } from '../utils/handler';

export const createRtcListeners = () => {
  const room = useRoomStore();
  const deviceStore = useDeviceStore();
  const { parser } = useMessageHandler();
  const playStatus: Record<string, { audio?: boolean; video?: boolean }> = {};

  const handleTrackEnded = async (event: { kind: string; isScreen: boolean }) => {
    if (event.isScreen && event.kind === 'video') {
      await RtcClient.stopScreenCapture();
      await RtcClient.unpublishScreenStream(MediaType.VIDEO);
      room.updateLocalUser({ publishScreen: false });
    }
  };

  const handleUserJoin = (e: any) => {
    const extraInfo = JSON.parse(e.userInfo.extraInfo || '{}');
    room.remoteUserJoin({
      userId: extraInfo.user_id || e.userInfo.userId,
      username: extraInfo.user_name || e.userInfo.userId,
    });
  };

  const handleError = (e: { errorCode: any }) => {
    console.log('[RTC Error]', e);
  };

  const handleUserLeave = (e: any) => {
    room.remoteUserLeave(e.userInfo);
    room.removeAutoPlayFail(e.userInfo);
  };

  const handleUserPublishStream = (e: { userId: string; mediaType: MediaType }) => {
    const payload: IUser = { userId: e.userId };
    if (e.mediaType === MediaType.AUDIO) payload.publishAudio = true;
    if (e.mediaType === MediaType.VIDEO) payload.publishVideo = true;
    if (e.mediaType === MediaType.AUDIO_AND_VIDEO) {
      payload.publishAudio = true;
      payload.publishVideo = true;
    }
    RtcClient.setRemoteVideoPlayer(e.userId, room.isFullScreen ? 'remote-video-player' : 'remote-full-player');
    room.updateRemoteUser(payload);
  };

  const handleUserUnpublishStream = (e: { userId: string; mediaType: MediaType }) => {
    const payload: IUser = { userId: e.userId };
    if (e.mediaType === MediaType.AUDIO || e.mediaType === MediaType.AUDIO_AND_VIDEO) payload.publishAudio = false;
    RtcClient.setRemoteVideoPlayer(e.userId);
    room.updateRemoteUser(payload);
  };

  const handleRemoteStreamStats = (e: any) => room.updateRemoteUser({ userId: e.userId, audioStats: e.audioStats });
  const handleLocalStreamStats = (e: any) => room.updateLocalUser({ audioStats: e.audioStats });

  const handleLocalAudioPropertiesReport = (e: any[]) => {
    const localAudioInfo = e.find((item) => item.streamIndex === StreamIndex.STREAM_INDEX_MAIN);
    if (localAudioInfo) room.updateLocalUser({ audioPropertiesInfo: localAudioInfo.audioPropertiesInfo });
  };

  const handleRemoteAudioPropertiesReport = (e: any[]) => {
    const remoteAudioInfo = e
      .filter((item) => item.streamKey.streamIndex === StreamIndex.STREAM_INDEX_MAIN)
      .map((item) => ({ userId: item.streamKey.userId, audioPropertiesInfo: item.audioPropertiesInfo }));
    if (remoteAudioInfo.length) room.updateRemoteUser(remoteAudioInfo);
  };

  const handleAudioDeviceStateChanged = async (device: any) => {
    const devices = await RtcClient.getDevices();
    if (device.mediaDeviceInfo.kind === 'audioinput') {
      const deviceId = device.deviceState === 'inactive' ? devices.audioInputs?.[0]?.deviceId || '' : device.mediaDeviceInfo.deviceId;
      RtcClient.switchDevice(MediaType.AUDIO, deviceId);
      deviceStore.setMicrophoneList(devices.audioInputs);
      deviceStore.updateSelectedDevice({ selectedMicrophone: deviceId });
    }
  };

  const handleAutoPlayFail = (event: any) => {
    const userId = event.userId;
    playStatus[userId] = { ...(playStatus[userId] || {}), [event.kind]: false };
    room.addAutoPlayFail({ userId });
  };

  const handlePlayerEvent = (event: any) => {
    const { userId, rawEvent, type } = event;
    const current = playStatus[userId] || {};
    if (rawEvent.type === 'playing') {
      playStatus[userId] = { ...current, [type]: true };
      if (playStatus[userId].audio !== false && playStatus[userId].video !== false) room.removeAutoPlayFail({ userId });
    } else if (rawEvent.type === 'pause') {
      playStatus[userId] = { ...current, [type]: false };
      room.addAutoPlayFail({ userId });
    }
  };

  const handleNetworkQuality = (uplink: NetworkQuality, downlink: NetworkQuality) => {
    room.updateNetworkQuality(Math.floor((uplink + downlink) / 2) as NetworkQuality);
  };

  const handleRoomBinaryMessageReceived = (event: { message: ArrayBuffer }) => parser(event.message);

  return {
    handleError,
    handleUserJoin,
    handleUserLeave,
    handleTrackEnded,
    handleUserPublishStream,
    handleUserUnpublishStream,
    handleRemoteStreamStats,
    handleLocalStreamStats,
    handleLocalAudioPropertiesReport,
    handleRemoteAudioPropertiesReport,
    handleAudioDeviceStateChanged,
    handleAutoPlayFail,
    handlePlayerEvent,
    handleRoomBinaryMessageReceived,
    handleNetworkQuality,
  };
};
