/**
 * 语音访谈房间 API（无需登录认证）
 */

import { apiGet, apiPost } from './base'

const BASE_URL = '/api/interviews'

export const interviewApi = {
  /**
   * 通过 token 获取访谈基本信息
   * @param {string} token - 访谈 token
   * @returns {Promise<Object>} 访谈信息
   */
  getByToken: (token) => {
    return apiGet(`${BASE_URL}/by-token/${token}`, {}, false)
  },

  /**
   * 获取访谈房间的 RTC 配置，同时后端启动 AIGC Agent
   * @param {number} interviewId - 访谈ID
   * @returns {Promise<Object>} RTC 配置
   */
  getRtcConfig: (interviewId) => {
    return apiPost(`${BASE_URL}/${interviewId}/rtc-config`, {}, {}, false)
  },

  /**
   * 结束访谈
   * @param {number} interviewId - 访谈ID
   * @param {Array} [transcript] - 对话记录
   * @returns {Promise<Object>} 结束结果
   */
  stopInterview: (interviewId, transcript = []) => {
    return apiPost(`${BASE_URL}/${interviewId}/stop`, { transcript }, {}, false)
  },
}
