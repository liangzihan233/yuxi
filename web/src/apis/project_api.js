/**
 * 访谈调研项目管理 API
 */

import { apiGet, apiAdminGet, apiAdminPost, apiAdminPut, apiAdminDelete, apiRequest } from './base'

const BASE_URL = '/api/projects'

// =============================================================================
// === 项目管理 ===
// =============================================================================

export const projectApi = {
  /**
   * 获取项目列表
   * @returns {Promise<Array>} 项目列表
   */
  listProjects: () => {
    return apiAdminGet(BASE_URL)
  },

  /**
   * 获取项目统计
   * @returns {Promise<Object>} 统计信息
   */
  getStats: () => {
    return apiAdminGet(`${BASE_URL}/stats`)
  },

  /**
   * 创建项目
   * @param {Object} data - 项目数据
   * @param {string} data.name - 项目名称
   * @param {string} [data.description] - 项目描述
   * @param {string} [data.status] - 状态
   * @param {string} [data.cover_image] - 封面图
   * @param {string} [data.knowledge_base_id] - 关联知识库ID
   * @returns {Promise<Object>} 创建的项目
   */
  createProject: (data) => {
    return apiAdminPost(BASE_URL, data)
  },

  /**
   * 获取项目详情
   * @param {number} projectId - 项目ID
   * @returns {Promise<Object>} 项目详情
   */
  getProject: (projectId) => {
    return apiAdminGet(`${BASE_URL}/${projectId}`)
  },

  /**
   * 更新项目
   * @param {number} projectId - 项目ID
   * @param {Object} data - 更新数据
   * @returns {Promise<Object>} 更新结果
   */
  updateProject: (projectId, data) => {
    return apiAdminPut(`${BASE_URL}/${projectId}`, data)
  },

  /**
   * 删除项目
   * @param {number} projectId - 项目ID
   * @returns {Promise<Object>} 删除结果
   */
  deleteProject: (projectId) => {
    return apiAdminDelete(`${BASE_URL}/${projectId}`)
  },

  /**
   * 上传项目文档
   * @param {number} projectId - 项目ID
   * @param {File} file - 文件对象
   * @returns {Promise<Object>} 上传结果
   */
  uploadDocument: (projectId, file) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiAdminPost(`${BASE_URL}/${projectId}/upload-document`, formData)
  },

  /**
   * AI 自动完善项目信息
   * @param {number} projectId - 项目ID
   * @returns {Promise<Object>} 完善结果
   */
  enrichProject: (projectId) => {
    return apiAdminPost(`${BASE_URL}/${projectId}/enrich`)
  },

  /**
   * 删除项目文档
   * @param {number} projectId - 项目ID
   * @returns {Promise<Object>} 删除结果
   */
  deleteDocument: (projectId) => {
    return apiAdminDelete(`${BASE_URL}/${projectId}/document`)
  }
}

// =============================================================================
// === 访谈流程 ===
// =============================================================================

export const flowApi = {
  /**
   * 获取项目的访谈流程列表
   * @param {number} projectId - 项目ID
   * @returns {Promise<Array>} 流程列表
   */
  listFlows: (projectId) => {
    return apiAdminGet(`${BASE_URL}/${projectId}/flows`)
  },

  /**
   * 创建访谈流程
   * @param {number} projectId - 项目ID
   * @param {Object} data - 流程数据
   * @returns {Promise<Object>} 创建的流程
   */
  createFlow: (projectId, data) => {
    return apiAdminPost(`${BASE_URL}/${projectId}/flows`, data)
  },

  /**
   * AI 根据文档生成访谈流程
   * @param {number} projectId - 项目ID
   * @param {Object} data - 生成参数
   * @param {string} data.name - 流程名称
   * @param {number} [data.estimated_duration] - 预计时长（分钟）
   * @param {string} [data.flow_type] - 流程类型: chat/questionnaire/test
   * @param {string} [data.remark] - 备注
   * @returns {Promise<Object>} 生成的流程
   */
  generateFlow: (projectId, data) => {
    return apiAdminPost(`${BASE_URL}/${projectId}/flows/generate`, data)
  },

  /**
   * 获取访谈流程详情
   * @param {number} projectId - 项目ID
   * @param {number} flowId - 流程ID
   * @returns {Promise<Object>} 流程详情
   */
  getFlow: (projectId, flowId) => {
    return apiAdminGet(`${BASE_URL}/${projectId}/flows/${flowId}`)
  },

  /**
   * 更新访谈流程
   * @param {number} projectId - 项目ID
   * @param {number} flowId - 流程ID
   * @param {Object} data - 更新数据
   * @returns {Promise<Object>} 更新结果
   */
  updateFlow: (projectId, flowId, data) => {
    return apiAdminPut(`${BASE_URL}/${projectId}/flows/${flowId}`, data)
  },

  /**
   * 确认访谈流程（draft -> confirmed）
   * @param {number} projectId - 项目ID
   * @param {number} flowId - 流程ID
   * @returns {Promise<Object>} 确认结果
   */
  confirmFlow: (projectId, flowId) => {
    return apiAdminPost(`${BASE_URL}/${projectId}/flows/${flowId}/confirm`)
  },

  /**
   * 删除访谈流程
   * @param {number} projectId - 项目ID
   * @param {number} flowId - 流程ID
   * @returns {Promise<Object>} 删除结果
   */
  deleteFlow: (projectId, flowId) => {
    return apiAdminDelete(`${BASE_URL}/${projectId}/flows/${flowId}`)
  }
}

// =============================================================================
// === 访谈记录 ===
// =============================================================================

export const interviewApi = {
  /**
   * 校验项目是否满足创建访谈的条件
   * @param {number} projectId - 项目ID
   * @returns {Promise<Object>} { ready: boolean, missing: string[], confirmed_flows: Array }
   */
  validateReady: (projectId) => {
    return apiAdminGet(`${BASE_URL}/${projectId}/interviews/validate`)
  },

  /**
   * 创建访谈记录
   * @param {number} projectId - 项目ID
   * @param {Object} data - 访谈数据
   * @returns {Promise<Object>} 创建的访谈记录
   */
  createInterview: (projectId, data) => {
    return apiAdminPost(`${BASE_URL}/${projectId}/interviews`, data)
  },

  /**
   * 获取项目的访谈记录列表（分页+筛选）
   * @param {number} projectId - 项目ID
   * @param {Object} params - 查询参数
   * @param {string} [params.status] - 状态筛选
   * @param {number} [params.page=1] - 页码
   * @param {number} [params.pageSize=10] - 每页数量
   * @returns {Promise<Object>} { items: Array, total: number }
   */
  listInterviewsPaginated: (projectId, { status, page = 1, pageSize = 10, interviewId } = {}) => {
    const params = new URLSearchParams()
    if (status) params.set('status', status)
    if (interviewId) params.set('parent_interview_id', interviewId)
    params.set('page', page)
    params.set('page_size', pageSize)
    return apiAdminGet(`${BASE_URL}/${projectId}/interviews?${params.toString()}`)
  },

  /**
   * 获取项目的访谈记录列表（不分页，兼容旧接口）
   * @param {number} projectId - 项目ID
   * @returns {Promise<Array>} 访谈记录列表
   */
  listInterviews: (projectId) => {
    return apiAdminGet(`${BASE_URL}/${projectId}/interviews?page_size=1000`).then(res => {
      // 兼容：后端返回 {items, total}，旧接口期望数组
      if (Array.isArray(res)) return res
      return res.items || []
    })
  },

  /**
   * 获取项目访谈统计数据
   * @param {number} projectId - 项目ID
   * @returns {Promise<Object>} { total, pending, in_progress, completed, analyzing, archived, remaining_seconds }
   */
  getInterviewStats: (projectId) => {
    return apiAdminGet(`${BASE_URL}/${projectId}/interviews/stats`)
  },

  /**
   * 获取访谈记录详情
   * @param {number} projectId - 项目ID
   * @param {number} interviewId - 访谈ID
   * @returns {Promise<Object>} 访谈记录详情
   */
  getInterview: (projectId, interviewId) => {
    return apiAdminGet(`${BASE_URL}/${projectId}/interviews/${interviewId}`)
  },

  /**
   * 更新访谈状态
   * @param {number} projectId - 项目ID
   * @param {number} interviewId - 访谈ID
   * @param {string} status - 新状态
   * @returns {Promise<Object>} 更新结果
   */
  updateInterviewStatus: (projectId, interviewId, status) => {
    return apiAdminPut(`${BASE_URL}/${projectId}/interviews/${interviewId}/status`, { status })
  },

  /**
   * 访谈记录入库
   * @param {number} projectId - 项目ID
   * @param {number} interviewId - 访谈ID
   * @returns {Promise<Object>} 入库结果
   */
  archiveInterview: (projectId, interviewId) => {
    return apiAdminPost(`${BASE_URL}/${projectId}/interviews/${interviewId}/archive`)
  },

  /**
   * 分析访谈记录
   * @param {number} projectId - 项目ID
   * @param {number} interviewId - 访谈ID
   * @returns {Promise<Object>} 分析后的访谈记录
   */
  analyzeInterview: (projectId, interviewId) => {
    return apiAdminPost(`${BASE_URL}/${projectId}/interviews/${interviewId}/analyze`)
  },

  /**
   * 删除访谈记录
   * @param {number} projectId - 项目ID
   * @param {number} interviewId - 访谈ID
   * @returns {Promise<Object>} 删除结果
   */
  deleteInterview: (projectId, interviewId) => {
    return apiAdminDelete(`${BASE_URL}/${projectId}/interviews/${interviewId}`)
  },

  /**
   * 导出访谈记录文本
   * @param {number} projectId - 项目ID
   * @param {number} interviewId - 访谈ID
   * @returns {Promise<Blob>} 文本文件
   */
  exportInterviewTranscript: async (projectId, interviewId) => {
    const response = await apiAdminGet(`${BASE_URL}/${projectId}/interviews/${interviewId}/export`, {}, 'blob')
    return response
  },

  /**
   * 受访者端：根据 token 获取访谈信息
   */
  getByToken: (token) => apiGet(`/api/interviews/by-token/${token}`, {}, false),

  /**
   * 受访者端：获取 RTC 配置并启动访谈
   */
  getRtcConfig: (interviewId) => apiPost(`/api/interviews/${interviewId}/rtc-config`, {}, {}, false),

  /**
   * 受访者端：结束访谈并保存实时记录
   */
  stopInterview: (interviewId, transcript = [], sessionUuid = '') => apiPost(`/api/interviews/${interviewId}/stop`, {
    transcript,
    session_uuid: sessionUuid || undefined
  }, {}, false)
}
