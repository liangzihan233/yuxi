import RtcClient from '../services/RtcClient';
import { string2tlv, tlv2String } from './utils';
import { useRoomStore } from '../stores/room';
import logger from './logger';

export type AnyRecord = Record<string, any>;

export enum MESSAGE_TYPE {
  BRIEF = 'conv',
  SUBTITLE = 'subv',
  FUNCTION_CALL = 'tool',
}

export enum AGENT_BRIEF {
  UNKNOWN,
  LISTENING,
  THINKING,
  SPEAKING,
  INTERRUPTED,
  FINISHED,
}

export enum COMMAND {
  INTERRUPT = 'interrupt',
  EXTERNAL_TEXT_TO_SPEECH = 'ExternalTextToSpeech',
  EXTERNAL_TEXT_TO_LLM = 'ExternalTextToLLM',
}

export enum INTERRUPT_PRIORITY {
  NONE,
  HIGH,
  MEDIUM,
  LOW,
}

export const useMessageHandler = () => {
  const room = useRoomStore();

  const maps = {
    [MESSAGE_TYPE.BRIEF]: (parsed: AnyRecord) => {
      const { Stage } = parsed || {};
      const { Code, Description } = Stage || {};
      logger.debug('[MESSAGE_TYPE.BRIEF]: ', Code, Description);
      switch (Code) {
        case AGENT_BRIEF.THINKING:
          room.updateAIThinkState(true);
          break;
        case AGENT_BRIEF.SPEAKING:
          room.updateAITalkState(true);
          break;
        case AGENT_BRIEF.FINISHED:
          room.updateAITalkState(false);
          break;
        case AGENT_BRIEF.INTERRUPTED:
          room.setInterruptMsg();
          break;
        default:
          break;
      }
    },
    [MESSAGE_TYPE.SUBTITLE]: (parsed: AnyRecord) => {
      const data = parsed.data?.[0] || {};
      if (data) {
        const { text, definite, userId, paragraph } = data;
        if ((window as any)._debug_mode) logger.debug('handleRoomBinaryMessageReceived', data);
        if (RtcClient.getAgentEnabled()) {
          room.setHistoryMsg({ text, user: userId, paragraph, definite });
        }
      }
    },
    [MESSAGE_TYPE.FUNCTION_CALL]: (parsed: AnyRecord) => {
      const name: string = parsed?.tool_calls?.[0]?.function?.name;
      const map: Record<string, string> = {
        getcurrentweather: '今天下雪， 最低气温零下10度',
      };
      RtcClient.engine.sendUserBinaryMessage(
        'RobotMan_',
        string2tlv(
          JSON.stringify({
            ToolCallID: parsed?.tool_calls?.[0]?.id,
            Content: map[name.toLocaleLowerCase().replace(/_/g, '')],
          }),
          'func'
        )
      );
    },
  };

  return {
    parser: (buffer: ArrayBuffer) => {
      try {
        const { type, value } = tlv2String(buffer);
        maps[type as MESSAGE_TYPE]?.(JSON.parse(value));
      } catch (e) {
        logger.debug('parse error', e);
      }
    },
  };
};
