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
   * @param {string} data.name - 访谈名称
   * @param {string} [data.valid_from] - 有效开始时间
   * @param {string} [data.valid_until] - 有效结束时间
   * @param {number} [data.max_participants] - 最大参与人数
   * @param {number[]} data.linked_flows - 关联的流程ID列表
   * @returns {Promise<Object>} 创建的访谈记录
   */
  createInterview: (projectId, data) => {
    return apiAdminPost(`${BASE_URL}/${projectId}/interviews`, data)
  },

  /**
   * 获取项目的访谈记录列表
   * @param {number} projectId - 项目ID
   * @returns {Promise<Array>} 访谈记录列表
   */
  listInterviews: (projectId) => {
    return apiAdminGet(`${BASE_URL}/${projectId}/interviews`)
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
   * 删除访谈记录
   * @param {number} projectId - 项目ID
   * @param {number} interviewId - 访谈ID
   * @returns {Promise<Object>} 删除结果
   */
  deleteInterview: (projectId, interviewId) => {
    return apiAdminDelete(`${BASE_URL}/${projectId}/interviews/${interviewId}`)
  }
}
