import { defineStore } from 'pinia';

export const useDeviceStore = defineStore('device', {
  state: () => ({
    audioInputs: [] as MediaDeviceInfo[],
    audioOutputs: [] as MediaDeviceInfo[],
    videoInputs: [] as MediaDeviceInfo[],
    selectedMicrophone: '' as string | undefined,
    selectedCamera: '' as string | undefined,
    devicePermissions: {
      audio: false,
      video: false,
    },
  }),
  actions: {
    updateMediaInputs(payload: {
      audioInputs?: MediaDeviceInfo[];
      audioOutputs?: MediaDeviceInfo[];
      videoInputs?: MediaDeviceInfo[];
    }) {
      if (payload.audioInputs) this.audioInputs = payload.audioInputs;
      if (payload.audioOutputs) this.audioOutputs = payload.audioOutputs;
      if (payload.videoInputs) this.videoInputs = payload.videoInputs;
    },
    setMicrophoneList(audioInputs: MediaDeviceInfo[]) {
      this.audioInputs = audioInputs;
    },
    updateSelectedDevice(payload: { selectedMicrophone?: string; selectedCamera?: string }) {
      if ('selectedMicrophone' in payload) this.selectedMicrophone = payload.selectedMicrophone;
      if ('selectedCamera' in payload) this.selectedCamera = payload.selectedCamera;
    },
    setDevicePermissions(payload: { audio: boolean; video: boolean }) {
      this.devicePermissions = payload;
    },
  },
});
