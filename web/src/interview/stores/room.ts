import { defineStore } from 'pinia';
import { NetworkQuality, type AudioPropertiesInfo, type LocalAudioStats, type RemoteAudioStats } from '@volcengine/rtc';
import RtcClient from '../services/RtcClient';

export interface IUser {
  username?: string;
  userId?: string;
  publishAudio?: boolean;
  publishVideo?: boolean;
  publishScreen?: boolean;
  audioStats?: RemoteAudioStats;
  audioPropertiesInfo?: AudioPropertiesInfo;
}

export type LocalUser = Omit<IUser, 'audioStats'> & {
  loginToken?: string;
  audioStats?: LocalAudioStats;
};

export interface Msg {
  value: string;
  time: string;
  user: string;
  paragraph?: boolean;
  definite?: boolean;
  isInterrupted?: boolean;
}

export interface SceneConfig {
  id: string;
  icon?: string;
  name?: string;
  questions?: string[];
  botName: string;
  isVision: boolean;
  isScreenMode: boolean;
  isInterruptMode: boolean;
  isAvatarScene?: boolean;
  avatarBgUrl?: string;
}

export interface RTCConfig {
  AppId: string;
  RoomId: string;
  UserId: string;
  Token: string;
}

export const useRoomStore = defineStore('room', {
  state: () => ({
    time: -1,
    roomId: undefined as string | undefined,
    localUser: {
      publishAudio: false,
      publishVideo: false,
      publishScreen: false,
    } as LocalUser,
    remoteUsers: [] as IUser[],
    autoPlayFailUser: [] as string[],
    isJoined: false,
    scene: '',
    sceneConfigMap: {} as Record<string, SceneConfig>,
    rtcConfigMap: {} as Record<string, RTCConfig>,
    isAIGCEnable: false,
    isAITalking: false,
    isAIThinking: false,
    isUserTalking: false,
    networkQuality: NetworkQuality.UNKNOWN,
    msgHistory: [] as Msg[],
    currentConversation: {} as Record<string, { msg: string; definite: boolean }>,
    isShowSubtitle: true,
    isFullScreen: false,
    customSceneName: '',
  }),
  getters: {
    currentSceneConfig: (state) => state.sceneConfigMap[state.scene] || ({} as SceneConfig),
    currentRTCConfig: (state) => state.rtcConfigMap[state.scene] || ({} as RTCConfig),
  },
  actions: {
    localJoinRoom(payload: { roomId: string; user: LocalUser }) {
      this.roomId = payload.roomId;
      this.localUser = { ...this.localUser, ...payload.user };
      this.isJoined = true;
    },
    localLeaveRoom() {
      this.roomId = undefined;
      this.time = -1;
      this.localUser = { publishAudio: false, publishVideo: false, publishScreen: false };
      this.remoteUsers = [];
      this.isJoined = false;
    },
    remoteUserJoin(payload: IUser) {
      if (!this.remoteUsers.some((user) => user.userId === payload.userId)) {
        this.remoteUsers.push(payload);
      }
    },
    remoteUserLeave(payload: IUser) {
      this.remoteUsers = this.remoteUsers.filter((user) => user.userId !== payload.userId);
    },
    updateRemoteUser(payload: IUser | IUser[]) {
      const users = Array.isArray(payload) ? payload : [payload];
      users.forEach((user) => {
        const index = this.remoteUsers.findIndex((item) => item.userId === user.userId);
        if (index >= 0) {
          this.remoteUsers[index] = { ...this.remoteUsers[index], ...user };
        } else {
          this.remoteUsers.push(user);
        }
      });
    },
    updateLocalUser(payload: Partial<LocalUser>) {
      this.localUser = { ...this.localUser, ...payload };
    },
    updateScene(scene: string) {
      this.scene = scene;
    },
    updateSceneConfig(payload: Record<string, SceneConfig>) {
      this.sceneConfigMap = payload;
    },
    updateRTCConfig(payload: Record<string, RTCConfig>) {
      this.rtcConfigMap = payload;
      const current = payload[this.scene];
      if (current) {
        RtcClient.basicInfo = {
          app_id: current.AppId,
          room_id: current.RoomId,
          user_id: current.UserId,
          token: current.Token,
        };
      }
    },
    updateAIGCState(isAIGCEnable: boolean) {
      this.isAIGCEnable = isAIGCEnable;
    },
    updateAITalkState(isAITalking: boolean) {
      this.isAIThinking = false;
      this.isUserTalking = false;
      this.isAITalking = isAITalking;
    },
    updateAIThinkState(isAIThinking: boolean) {
      this.isAIThinking = isAIThinking;
      this.isUserTalking = false;
    },
    updateNetworkQuality(networkQuality: NetworkQuality) {
      this.networkQuality = networkQuality;
    },
    clearHistoryMsg() {
      this.msgHistory = [];
    },
    clearCurrentMsg() {
      this.currentConversation = {};
      this.msgHistory = [];
      this.isAITalking = false;
      this.isUserTalking = false;
    },
    setHistoryMsg(payload: { text: string; user: string; paragraph?: boolean; definite?: boolean }) {
      const lastMsg = this.msgHistory.at(-1) || ({} as Msg);
      const sceneConfig = this.sceneConfigMap[this.scene] || ({} as SceneConfig);
      const fromBot = payload.user === sceneConfig.botName || payload.user.includes('voiceChat_');
      const currentSubtitleMode = sceneConfig.isAvatarScene ? 1 : 0;
      const lastMsgCompleted = !fromBot || currentSubtitleMode ? lastMsg.paragraph : lastMsg.definite;

      if (this.msgHistory.length) {
        if (lastMsgCompleted) {
          this.msgHistory.push({
            value: payload.text,
            time: new Date().toString(),
            user: payload.user,
            definite: payload.definite,
            paragraph: payload.paragraph,
          });
        } else {
          if (fromBot && currentSubtitleMode) {
            lastMsg.value += payload.text;
          } else {
            lastMsg.value = payload.text;
          }
          lastMsg.time = new Date().toString();
          lastMsg.paragraph = payload.paragraph;
          lastMsg.definite = payload.definite;
          lastMsg.user = payload.user;
        }
      } else {
        this.msgHistory.push({
          value: payload.text,
          time: new Date().toString(),
          user: payload.user,
          paragraph: payload.paragraph,
        });
      }
    },
    setInterruptMsg() {
      this.isAITalking = false;
      for (let id = this.msgHistory.length - 1; id >= 0; id -= 1) {
        const msg = this.msgHistory[id];
        if (msg.value) {
          if (!msg.definite) this.msgHistory[id].isInterrupted = true;
          break;
        }
      }
    },
    updateShowSubtitle(isShowSubtitle: boolean) {
      this.isShowSubtitle = isShowSubtitle;
    },
    updateFullScreen(isFullScreen: boolean) {
      this.isFullScreen = isFullScreen;
    },
    addAutoPlayFail(payload: { userId: string }) {
      if (!this.autoPlayFailUser.includes(payload.userId)) this.autoPlayFailUser.push(payload.userId);
    },
    removeAutoPlayFail(payload: { userId: string }) {
      this.autoPlayFailUser = this.autoPlayFailUser.filter((userId) => userId !== payload.userId);
    },
  },
});
