import VERTC, {
  MirrorType,
  StreamIndex,
  type IRTCEngine,
  RoomProfileType,
  MediaType,
  AudioProfileType,
  VideoRenderMode,
  type ScreenEncoderConfig,
} from '@volcengine/rtc';
import RTCAIAnsExtension from '@volcengine/rtc/extension-ainr';
import { message } from 'ant-design-vue';
import { string2tlv } from '../utils/utils';
import { COMMAND, INTERRUPT_PRIORITY } from '../utils/handler';

export interface BasicBody {
  app_id: string;
  room_id: string;
  user_id: string;
  token?: string;
}

class RTCClient {
  engine!: IRTCEngine;

  basicInfo!: BasicBody;

  private audioCaptureDevice?: string;

  private videoCaptureDevice?: string;

  audioBotEnabled = false;

  audioBotStartTime = 0;

  interviewId: number | undefined = undefined;

  createEngine = async () => {
    this.engine = VERTC.createEngine(this.basicInfo.app_id);
    try {
      const AIAnsExtension = new RTCAIAnsExtension();
      await this.engine.registerExtension(AIAnsExtension);
      AIAnsExtension.enable();
    } catch (error) {
      console.warn(`当前环境不支持 AI 降噪, 此错误可忽略, 不影响实际使用, e: ${(error as Error).message}`);
    }
  };

  addEventListeners = (listeners: Record<string, (...args: any[]) => void>) => {
    this.engine.on(VERTC.events.onError, listeners.handleError);
    this.engine.on(VERTC.events.onUserJoined, listeners.handleUserJoin);
    this.engine.on(VERTC.events.onUserLeave, listeners.handleUserLeave);
    this.engine.on(VERTC.events.onTrackEnded, listeners.handleTrackEnded);
    this.engine.on(VERTC.events.onUserPublishStream, listeners.handleUserPublishStream);
    this.engine.on(VERTC.events.onUserUnpublishStream, listeners.handleUserUnpublishStream);
    this.engine.on(VERTC.events.onRemoteStreamStats, listeners.handleRemoteStreamStats);
    this.engine.on(VERTC.events.onLocalStreamStats, listeners.handleLocalStreamStats);
    this.engine.on(VERTC.events.onAudioDeviceStateChanged, listeners.handleAudioDeviceStateChanged);
    this.engine.on(VERTC.events.onLocalAudioPropertiesReport, listeners.handleLocalAudioPropertiesReport);
    this.engine.on(VERTC.events.onRemoteAudioPropertiesReport, listeners.handleRemoteAudioPropertiesReport);
    this.engine.on(VERTC.events.onAutoplayFailed, listeners.handleAutoPlayFail);
    this.engine.on(VERTC.events.onPlayerEvent, listeners.handlePlayerEvent);
    this.engine.on(VERTC.events.onRoomBinaryMessageReceived, listeners.handleRoomBinaryMessageReceived);
    this.engine.on(VERTC.events.onNetworkQuality, listeners.handleNetworkQuality);
  };

  joinRoom = () => {
    console.log(' ------ userJoinRoom\n', `roomId: ${this.basicInfo.room_id}\n`, `uid: ${this.basicInfo.user_id}`);
    return this.engine.joinRoom(
      this.basicInfo.token!,
      `${this.basicInfo.room_id}`,
      {
        userId: this.basicInfo.user_id,
        extraInfo: JSON.stringify({
          call_scene: 'RTC-AIGC',
          user_name: this.basicInfo.user_id,
          user_id: this.basicInfo.user_id,
        }),
      },
      {
        isAutoPublish: true,
        isAutoSubscribeAudio: true,
        roomProfileType: RoomProfileType.chat,
      }
    );
  };

  leaveRoom = () => {
    this.audioBotEnabled = false;
    this.engine?.leaveRoom().catch(() => undefined);
    if (this.engine) VERTC.destroyEngine(this.engine);
    this.audioCaptureDevice = undefined;
  };

  checkPermission() {
    return VERTC.enableDevices({ video: false, audio: true });
  }

  async getDevices(props?: { video?: boolean; audio?: boolean }) {
    const { video = false, audio = true } = props || {};
    let audioInputs: MediaDeviceInfo[] = [];
    let audioOutputs: MediaDeviceInfo[] = [];
    let videoInputs: MediaDeviceInfo[] = [];
    const permission = await VERTC.enableDevices({ video, audio });

    if (audio) {
      const inputs = await VERTC.enumerateAudioCaptureDevices();
      const outputs = await VERTC.enumerateAudioPlaybackDevices();
      audioInputs = inputs.filter((item) => item.deviceId && item.kind === 'audioinput');
      audioOutputs = outputs.filter((item) => item.deviceId && item.kind === 'audiooutput');
      this.audioCaptureDevice = audioInputs[0]?.deviceId;
      if (permission.audio) {
        if (!audioInputs.length) message.error('无麦克风设备, 请先确认设备情况。');
        if (!audioOutputs.length) message.error('无扬声器设备, 请先确认设备情况。');
      } else {
        message.error('暂无麦克风设备权限, 请先确认设备权限授予情况。');
      }
    }

    if (video) {
      videoInputs = await VERTC.enumerateVideoCaptureDevices();
      videoInputs = videoInputs.filter((item) => item.deviceId && item.kind === 'videoinput');
      this.videoCaptureDevice = videoInputs[0]?.deviceId;
      if (permission.video) {
        if (!videoInputs.length) message.error('无摄像头设备, 请先确认设备情况。');
      } else {
        message.error('暂无摄像头设备权限, 请先确认设备权限授予情况。');
      }
    }

    return { audioInputs, audioOutputs, videoInputs };
  }

  startVideoCapture = (camera?: string) => this.engine.startVideoCapture(camera || this.videoCaptureDevice);

  stopVideoCapture = async () => {
    this.engine.setLocalVideoMirrorType(MirrorType.MIRROR_TYPE_RENDER);
    await this.engine.stopVideoCapture();
  };

  startScreenCapture = (enableAudio = false) => this.engine.startScreenCapture({ enableAudio });

  stopScreenCapture = () => this.engine.stopScreenCapture();

  startAudioCapture = (mic?: string) => this.engine.startAudioCapture(mic || this.audioCaptureDevice);

  stopAudioCapture = () => this.engine.stopAudioCapture();

  publishStream = (mediaType: MediaType) => this.engine.publishStream(mediaType);

  unpublishStream = (mediaType: MediaType) => this.engine.unpublishStream(mediaType);

  publishScreenStream = (mediaType: MediaType) => this.engine.publishScreen(mediaType);

  unpublishScreenStream = (mediaType: MediaType) => this.engine.unpublishScreen(mediaType);

  setScreenEncoderConfig = (description: ScreenEncoderConfig) => this.engine.setScreenEncoderConfig(description);

  setBusinessId = (businessId: string) => this.engine.setBusinessId(businessId);

  setAudioVolume = (volume: number) => {
    this.engine.setCaptureVolume(StreamIndex.STREAM_INDEX_MAIN, volume);
    this.engine.setCaptureVolume(StreamIndex.STREAM_INDEX_SCREEN, volume);
  };

  setAudioProfile = (profile: AudioProfileType) => this.engine.setAudioProfile(profile);

  switchDevice = (deviceType: MediaType, deviceId: string) => {
    if (deviceType === MediaType.AUDIO) {
      this.audioCaptureDevice = deviceId;
      this.engine.setAudioCaptureDevice(deviceId);
    }
    if (deviceType === MediaType.VIDEO) {
      this.videoCaptureDevice = deviceId;
      this.engine.setVideoCaptureDevice(deviceId);
    }
  };

  setLocalVideoMirrorType = (type: MirrorType) => this.engine.setLocalVideoMirrorType(type);

  setLocalVideoPlayer = (
    userId: string,
    renderDom?: string | HTMLElement,
    isScreenShare = false,
    renderMode = VideoRenderMode.RENDER_MODE_FILL
  ) =>
    this.engine.setLocalVideoPlayer(isScreenShare ? StreamIndex.STREAM_INDEX_SCREEN : StreamIndex.STREAM_INDEX_MAIN, {
      renderDom,
      userId,
      renderMode,
    });

  setRemoteVideoPlayer = (userId: string, renderDom?: string | HTMLElement, renderMode = VideoRenderMode.RENDER_MODE_HIDDEN) =>
    this.engine.setRemoteVideoPlayer(StreamIndex.STREAM_INDEX_MAIN, { renderDom, userId, renderMode });

  removeLocalVideoPlayer = (userId: string, scope: StreamIndex | 'Both' = 'Both') => {
    if (scope === StreamIndex.STREAM_INDEX_SCREEN || scope === 'Both') {
      this.engine.setLocalVideoPlayer(StreamIndex.STREAM_INDEX_SCREEN, { userId });
    }
    if (scope === StreamIndex.STREAM_INDEX_MAIN || scope === 'Both') {
      this.engine.setLocalVideoPlayer(StreamIndex.STREAM_INDEX_MAIN, { userId });
    }
  };

  startAgent = async () => {
    // 后端 get_rtc_config 已自动启动 VoiceChat，前端只需设置标志
    this.audioBotEnabled = true;
    this.audioBotStartTime = Date.now();
  };

  stopAgent = async () => {
    if (this.audioBotEnabled && this.interviewId) {
      try {
        await fetch(`/api/interviews/${this.interviewId}/stop`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ transcript: [] }),
        });
      } catch (e) {
        console.warn('停止访谈失败:', e);
      }
      this.audioBotStartTime = 0;
    }
    this.audioBotEnabled = false;
  };

  commandAgent = ({
    command,
    agentName,
    interruptMode = INTERRUPT_PRIORITY.NONE,
    message: commandMessage = '',
  }: {
    command: COMMAND;
    agentName: string;
    interruptMode?: INTERRUPT_PRIORITY;
    message?: string;
  }) => {
    if (!this.audioBotEnabled) {
      console.warn('Interrupt failed, bot not enabled.');
      return;
    }
    this.engine.sendUserBinaryMessage(
      agentName,
      string2tlv(JSON.stringify({ Command: command, InterruptMode: interruptMode, Message: commandMessage }), 'ctrl')
    );
  };

  getAgentEnabled = () => this.audioBotEnabled;
}

export default new RTCClient();
