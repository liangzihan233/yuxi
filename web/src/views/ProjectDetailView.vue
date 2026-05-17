<template>
  <div class="project-detail-container">
    <!-- 顶部导航 -->
    <HeaderComponent :title="project?.name || '项目详情'">
      <template #left>
        <a-button type="text" @click="goBack" class="back-btn">
          <template #icon><ArrowLeft :size="18" /></template>
        </a-button>
      </template>
      <template #actions>
        <a-dropdown v-if="project">
          <a-button>
            更多操作 <DownOutlined />
          </a-button>
          <template #overlay>
            <a-menu @click="handleMenuClick">
              <a-menu-item key="enrich" :disabled="enriching || !project.document_url">
                <ThunderboltOutlined /> AI 自动完善
              </a-menu-item>
              <a-menu-item key="delete" danger>
                <DeleteOutlined /> 删除项目
              </a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </template>
    </HeaderComponent>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <a-spin size="large" />
      <p>正在加载项目...</p>
    </div>

    <template v-else-if="project">
      <div class="project-content layout-container">
        <!-- 项目信息卡片 -->
        <div class="section-card">
          <div class="section-header">
            <h3><Info :size="16" /> 项目信息</h3>
            <a-button type="text" size="small" @click="editProjectVisible = true">
              <EditOutlined /> 编辑
            </a-button>
          </div>
          <div class="section-body">
            <a-descriptions :column="2" size="small" :labelStyle="{ color: 'var(--gray-600)' }">
              <a-descriptions-item label="项目名称">{{ project.name }}</a-descriptions-item>
              <a-descriptions-item label="状态">
                <a-tag :color="statusColorMap[project.status] || 'default'" :bordered="false">
                  {{ statusLabelMap[project.status] || project.status }}
                </a-tag>
              </a-descriptions-item>
              <a-descriptions-item label="描述" :span="2">
                {{ project.description || '暂无描述' }}
              </a-descriptions-item>
              <a-descriptions-item label="创建时间" v-if="project.created_at">
                {{ formatTime(project.created_at) }}
              </a-descriptions-item>
              <a-descriptions-item label="更新时间" v-if="project.updated_at">
                {{ formatTime(project.updated_at) }}
              </a-descriptions-item>
            </a-descriptions>

            <!-- AI 摘要 -->
            <div v-if="project.ai_summary" class="ai-summary-section">
              <div class="summary-header">
                <ThunderboltOutlined style="color: var(--main-color)" />
                <span>AI 分析摘要</span>
              </div>
              <div class="summary-content">
                <div v-if="project.ai_summary.background" class="summary-item">
                  <strong>背景：</strong>{{ project.ai_summary.background }}
                </div>
                <div v-if="project.ai_summary.objectives" class="summary-item">
                  <strong>目标：</strong>
                  <ul>
                    <li v-for="(obj, idx) in project.ai_summary.objectives" :key="idx">{{ obj }}</li>
                  </ul>
                </div>
                <div v-if="project.ai_summary.target_audience" class="summary-item">
                  <strong>目标人群：</strong>{{ project.ai_summary.target_audience }}
                </div>
                <div v-if="project.ai_summary.key_topics" class="summary-item">
                  <strong>关键主题：</strong>
                  <a-tag v-for="(topic, idx) in project.ai_summary.key_topics" :key="idx" :bordered="false" size="small">
                    {{ topic }}
                  </a-tag>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 文档上传卡片 -->
        <div class="section-card">
          <div class="section-header">
            <h3><FileText :size="16" /> 项目文档</h3>
          </div>
          <div class="section-body">
            <div v-if="project.document_url" class="document-info">
              <div class="document-item">
                <FileIcon :size="20" />
                <div class="document-meta">
                  <span class="document-name">{{ getDocumentName(project.document_url) }}</span>
                  <span class="document-status success">已上传</span>
                </div>
              </div>
              <div class="document-actions">
                <a-button
                  type="primary"
                  ghost
                  size="small"
                  :loading="enriching"
                  :disabled="enriching"
                  @click="handleEnrich"
                >
                  <ThunderboltOutlined /> AI 完善
                </a-button>
                <a-popconfirm
                  title="确定删除此文档？删除后需重新上传"
                  @confirm="handleDeleteDocument"
                  ok-text="确定"
                  cancel-text="取消"
                >
                  <a-button size="small" danger>
                    <DeleteOutlined /> 删除
                  </a-button>
                </a-popconfirm>
              </div>
            </div>
            <div v-else class="upload-area">
              <a-upload
                :before-upload="handleUpload"
                :show-upload-list="false"
                accept=".pdf,.doc,.docx,.txt,.md,.pptx,.xls,.xlsx"
              >
                <div class="upload-trigger">
                  <Upload :size="32" style="color: var(--gray-400)" />
                  <p class="upload-text">点击或拖拽上传项目文档</p>
                  <p class="upload-hint">支持 PDF、Word、Excel、TXT、Markdown、PPT 格式</p>
                </div>
              </a-upload>
            </div>
            <a-progress
              v-if="uploading"
              :percent="uploadPercent"
              status="active"
              size="small"
              style="margin-top: 12px"
            />
          </div>
        </div>

        <!-- 访谈流程卡片 -->
        <div class="section-card">
          <div class="section-header">
            <h3><GitBranch :size="16" /> 访谈流程</h3>
            <div class="section-actions">
              <a-button
                type="primary"
                ghost
                size="small"
                :disabled="!project.document_url"
                @click="openGenerateFlowModal"
              >
                <ThunderboltOutlined /> AI 生成流程
              </a-button>
              <a-button size="small" @click="openCreateFlowModal">
                <PlusOutlined /> 手动创建
              </a-button>
            </div>
          </div>
          <div class="section-body">
            <div v-if="flows.length === 0" class="empty-section">
              <p v-if="!project.document_url">请先上传项目文档，AI 可自动生成访谈流程</p>
              <p v-else>暂无访谈流程，点击 AI 生成或手动创建</p>
            </div>
            <div v-else class="flow-list">
              <div
                v-for="flow in flows"
                :key="flow.id"
                class="flow-item"
                @click="openFlowDetail(flow)"
              >
                <div class="flow-info">
                  <div class="flow-name">
                    <GitBranch :size="16" style="color: var(--main-color)" />
                    <span>{{ flow.name }}</span>
                    <a-tag v-if="flow.flow_type" :color="flowTypeColor[flow.flow_type] || 'default'" :bordered="false" size="small" class="flow-type-tag">
                      {{ flowTypeLabel[flow.flow_type] || flow.flow_type }}
                    </a-tag>
                  </div>
                  <div class="flow-meta">
                    <a-tag :color="flowStatusColor[flow.status] || 'default'" :bordered="false" size="small">
                      {{ flowStatusLabel[flow.status] || flow.status }}
                    </a-tag>
                    <span v-if="flow.estimated_duration" class="flow-duration">
                      预计 {{ flow.estimated_duration }} 分钟
                    </span>
                    <span class="flow-source">{{ flow.source_type === 'ai' ? 'AI 生成' : '手动创建' }}</span>
                  </div>
                </div>
                <div class="flow-actions">
                  <a-button
                    v-if="flow.status === 'draft'"
                    type="link"
                    size="small"
                    @click.stop="handleConfirmFlow(flow)"
                  >
                    确认
                  </a-button>
                  <a-popconfirm
                    title="确定删除此流程？"
                    @confirm="handleDeleteFlow(flow)"
                    ok-text="确定"
                    cancel-text="取消"
                  >
                    <a-button type="link" size="small" danger @click.stop>删除</a-button>
                  </a-popconfirm>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 访谈记录卡片 -->
        <div class="section-card">
          <div class="section-header">
            <h3><MessageSquare :size="16" /> 访谈列表</h3>
            <div class="section-actions">
              <a-button type="primary" ghost size="small" @click="handleGenerateInterviewLink">
                <LinkOutlined /> 生成访谈链接
              </a-button>
            </div>
          </div>
          <div class="section-body">
            <div v-if="interviews.length === 0" class="empty-section">
              <p>暂无访谈记录，点击「生成访谈链接」创建</p>
            </div>
            <div v-else class="interview-list">
              <div v-for="interview in displayedInterviews" :key="interview.id" class="interview-item">
                <div class="interview-info" @click="goToInterviewList(interview)">
                  <div class="interview-name-row">
                    <span class="interview-name">{{ interview.name || '访谈 #' + interview.id }}</span>
                    <a-tag :color="interviewStatusColor[interview.status] || 'default'" :bordered="false" size="small">
                      {{ interviewStatusLabel[interview.status] || interview.status }}
                    </a-tag>
                  </div>
                  <div class="interview-detail">
                    <span v-if="interview.valid_from">有效：{{ formatTime(interview.valid_from) }} ~ {{ formatTime(interview.valid_until) }}</span>
                    <span class="interview-participants">上限 {{ interview.max_participants }} 人</span>
                  </div>
                  <!-- 关联流程标签 -->
                  <div v-if="interview.linked_flows && interview.linked_flows.length > 0" class="interview-flows">
                    <a-tag
                      v-for="flowId in interview.linked_flows"
                      :key="flowId"
                      color="success"
                      :bordered="false"
                      size="small"
                    >
                      {{ getFlowName(flowId) }}
                    </a-tag>
                  </div>
                </div>
                <div class="interview-actions">
                  <a-button
                    type="text"
                    size="small"
                    :loading="archivingInterviewId === interview.id"
                    @click.stop="handleArchiveInterview(interview)"
                  >
                    入库
                  </a-button>
                  <a-tooltip title="复制链接">
                    <a-button type="text" size="small" @click="handleCopyLink(interview)">
                      <CopyOutlined />
                    </a-button>
                  </a-tooltip>
                  <a-tooltip title="生成二维码">
                    <a-button type="text" size="small" @click="handleShowQrCode(interview)">
                      <QrcodeOutlined />
                    </a-button>
                  </a-tooltip>
                  <a-popconfirm
                    title="确定删除此访谈记录？"
                    @confirm="handleDeleteInterview(interview)"
                    ok-text="确定"
                    cancel-text="取消"
                  >
                    <a-tooltip title="删除">
                      <a-button type="text" size="small" danger @click.stop>
                        <DeleteOutlined />
                      </a-button>
                    </a-tooltip>
                  </a-popconfirm>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 编辑项目弹窗 -->
    <a-modal
      v-model:open="editProjectVisible"
      title="编辑项目"
      @ok="handleUpdateProject"
      :confirm-loading="updating"
      width="600px"
      destroyOnClose
    >
      <h3>项目名称</h3>
      <a-input v-model:value="editForm.name" placeholder="项目名称" size="large" />
      <h3 style="margin-top: 20px">项目描述</h3>
      <a-textarea
        v-model:value="editForm.description"
        placeholder="项目描述"
        :auto-size="{ minRows: 3, maxRows: 6 }"
        size="large"
      />
      <h3 style="margin-top: 20px">项目状态</h3>
      <a-select v-model:value="editForm.status" style="width: 100%" size="large">
        <a-select-option value="draft">草稿</a-select-option>
        <a-select-option value="active">进行中</a-select-option>
        <a-select-option value="completed">已完成</a-select-option>
        <a-select-option value="archived">已归档</a-select-option>
      </a-select>
    </a-modal>

    <!-- 创建访谈流程弹窗 -->
    <a-modal
      v-model:open="createFlowVisible"
      title="创建访谈流程"
      @ok="handleCreateFlow"
      :confirm-loading="creatingFlow"
      width="500px"
      destroyOnClose
    >
      <h3>流程名称</h3>
      <a-input v-model:value="newFlow.name" placeholder="请输入流程名称" size="large" />
      <h3 style="margin-top: 20px">预计时长（分钟）</h3>
      <a-input-number v-model:value="newFlow.estimated_duration" :min="1" :max="480" style="width: 100%" size="large" />
    </a-modal>

    <!-- AI 生成流程弹窗 -->
    <a-modal
      v-model:open="generateFlowVisible"
      title="AI 生成访谈流程"
      @ok="handleGenerateFlow"
      :confirm-loading="generatingFlow"
      width="520px"
      destroyOnClose
      ok-text="开始生成"
    >
      <a-form layout="vertical" size="large">
        <a-form-item label="流程名称" required>
          <a-input
            v-model:value="generateForm.name"
            placeholder="请输入流程名称"
            :status="generateFormErrors.name ? 'error' : undefined"
          />
          <div v-if="generateFormErrors.name" class="form-error">{{ generateFormErrors.name }}</div>
        </a-form-item>
        <a-form-item label="预计时长（分钟）" required>
          <a-input-number
            v-model:value="generateForm.estimated_duration"
            :min="1"
            :max="480"
            style="width: 100%"
            placeholder="请输入预计时长"
          />
        </a-form-item>
        <a-form-item label="流程类型" required>
          <a-select v-model:value="generateForm.flow_type" placeholder="请选择流程类型">
            <a-select-option value="chat">杂谈</a-select-option>
            <a-select-option value="questionnaire">问卷</a-select-option>
            <a-select-option value="test">测试</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="备注">
          <a-textarea
            v-model:value="generateForm.remark"
            placeholder="可选，补充说明有助于 AI 更精准生成"
            :auto-size="{ minRows: 2, maxRows: 4 }"
          />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 流程详情弹窗 -->
    <a-modal
      v-model:open="flowDrawerVisible"
      :title="currentFlow?.name || '流程详情'"
      width="90%"
      :footer="null"
      :destroyOnClose="true"
      style="top: 20px"
    >
      <template v-if="currentFlow">
        <div class="flow-editor-header">
          <a-descriptions :column="4" size="small" :labelStyle="{ color: 'var(--gray-600)' }">
            <a-descriptions-item label="状态">
              <a-tag :color="flowStatusColor[currentFlow.status] || 'default'" :bordered="false">
                {{ flowStatusLabel[currentFlow.status] || currentFlow.status }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="来源">
              {{ currentFlow.source_type === 'ai' ? 'AI 生成' : '手动创建' }}
            </a-descriptions-item>
            <a-descriptions-item label="预计时长">
              {{ currentFlow.estimated_duration ? currentFlow.estimated_duration + ' 分钟' : '未设置' }}
            </a-descriptions-item>
            <a-descriptions-item label="类型">
              <a-tag v-if="currentFlow.flow_type" :color="flowTypeColor[currentFlow.flow_type] || 'default'" :bordered="false" size="small">
                {{ flowTypeLabel[currentFlow.flow_type] || currentFlow.flow_type }}
              </a-tag>
              <span v-else>未设置</span>
            </a-descriptions-item>
            <a-descriptions-item v-if="currentFlow.remark" label="备注" :span="4">
              {{ currentFlow.remark }}
            </a-descriptions-item>
            <a-descriptions-item label="创建时间">
              {{ formatTime(currentFlow.created_at) }}
            </a-descriptions-item>
          </a-descriptions>
        </div>

        <InterviewFlowEditor
          :flowName="currentFlow.name"
          :flowData="currentFlow.flow_data || { nodes: [], edges: [] }"
          :flowStatus="currentFlow.status"
          :saving="savingFlow"
          :readonly="currentFlow.status !== 'draft'"
          @save="handleSaveFlow"
          @confirm="handleConfirmFlow(currentFlow)"
          style="height: 60vh; margin-top: 16px"
        />
      </template>
    </a-modal>

    <!-- 创建访谈链接弹窗 -->
    <a-modal
      v-model:open="createInterviewVisible"
      title="生成访谈链接"
      @ok="handleCreateInterview"
      :confirm-loading="creatingInterview"
      width="560px"
      destroyOnClose
      ok-text="创建"
    >
      <a-form layout="vertical" size="large">
        <a-form-item label="访谈名称" required>
          <a-input
            v-model:value="interviewForm.name"
            placeholder="请输入访谈名称"
          >
            <template #suffix>
              <a-tooltip title="自动生成名称">
                <a-button type="text" size="small" @click="autoGenerateInterviewName">
                  <ThunderboltOutlined />
                </a-button>
              </a-tooltip>
            </template>
          </a-input>
        </a-form-item>
        <a-form-item label="有效时间" required>
          <a-range-picker
            v-model:value="interviewForm.dateRange"
            :show-time="{ format: 'HH:mm' }"
            format="YYYY-MM-DD HH:mm"
            :disabled-date="disabledDate"
            style="width: 100%"
          />
          <div class="form-hint">最大跨度一个月，结束时间不可选当前时间之前</div>
        </a-form-item>
        <div class="interview-selection-row">
          <a-form-item label="关联访谈流程" required class="interview-selection-item">
            <a-checkbox-group v-model:value="interviewForm.linked_flows" style="width: 100%">
              <div class="flow-checkbox-list">
                <a-checkbox
                  v-for="flow in confirmedFlows"
                  :key="flow.id"
                  :value="flow.id"
                  class="flow-checkbox-item"
                >
                  <div class="flow-checkbox-content">
                    <span class="flow-checkbox-name">{{ flow.name }}</span>
                    <span class="flow-checkbox-meta">
                      {{ flowTypeLabel[flow.flow_type] || '杂谈' }}
                      <template v-if="flow.estimated_duration"> · {{ flow.estimated_duration }}分钟</template>
                    </span>
                  </div>
                </a-checkbox>
              </div>
            </a-checkbox-group>
          </a-form-item>
          <a-form-item label="选择主持人" required class="interview-selection-item">
            <a-checkbox-group v-model:value="interviewForm.moderator_ids" style="width: 100%">
              <div class="flow-checkbox-list">
                <a-checkbox
                  v-for="moderator in moderatorOptions"
                  :key="moderator.id"
                  :value="moderator.id"
                  class="flow-checkbox-item"
                >
                  <div class="flow-checkbox-content">
                    <span class="flow-checkbox-name">{{ moderator.name }}</span>
                    <span class="flow-checkbox-meta">
                      {{ moderator.meta || '角色卡主持人' }}
                    </span>
                  </div>
                </a-checkbox>
              </div>
            </a-checkbox-group>
          </a-form-item>
        </div>
        <a-form-item label="最高参与人数">
          <a-input-number v-model:value="interviewForm.max_participants" :min="1" :max="100" style="width: 200px" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 二维码弹窗 -->
    <a-modal
      v-model:open="qrCodeVisible"
      :title="'访谈二维码 - ' + (currentInterview?.name || '')"
      :footer="null"
      width="360px"
      centered
    >
      <div class="qr-code-container">
        <div class="qr-code-image-wrapper">
          <img v-if="qrCodeDataUrl" :src="qrCodeDataUrl" alt="访谈二维码" class="qr-code-img" />
          <a-spin v-else />
        </div>
        <p class="qr-code-url">{{ currentInterview ? getInterviewLink(currentInterview) : '' }}</p>
        <p class="qr-code-hint">扫描上方二维码即可进入访谈页面</p>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, nextTick, computed } from 'vue'
import QRCode from 'qrcode'
import { useRoute, useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import {
  ArrowLeft,
  Info,
  FileText,
  File as FileIcon,
  Upload,
  GitBranch,
  MessageSquare,
  Link,
  Copy,
  QrCode
} from 'lucide-vue-next'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  DownOutlined,
  ThunderboltOutlined,
  LinkOutlined,
  CopyOutlined,
  QrcodeOutlined,
  EyeOutlined
} from '@ant-design/icons-vue'
import { projectApi, flowApi, interviewApi } from '@/apis/project_api'
import { roleCardApi } from '@/apis/rolecard_api'
import HeaderComponent from '@/components/HeaderComponent.vue'
import InterviewFlowEditor from '@/components/InterviewFlowEditor.vue'
import dayjs, { parseToShanghai } from '@/utils/time'

const route = useRoute()
const router = useRouter()

const projectId = ref(null)
const loading = ref(false)
const project = ref(null)
const flows = ref([])
const interviews = ref([])
const archivingInterviewId = ref(null)
const archivingAll = ref(false)

// 上传相关
const uploading = ref(false)
const uploadPercent = ref(0)

// AI 完善相关
const enriching = ref(false)

// 生成流程相关
const savingFlow = ref(false)

// 编辑项目弹窗
const editProjectVisible = ref(false)
const updating = ref(false)
const editForm = reactive({
  name: '',
  description: '',
  status: 'draft'
})

// 创建流程弹窗
const createFlowVisible = ref(false)
const creatingFlow = ref(false)
const newFlow = reactive({
  name: '',
  estimated_duration: 30
})

// AI 生成流程弹窗
const generateFlowVisible = ref(false)
const generatingFlow = ref(false)
const generateForm = reactive({
  name: '',
  estimated_duration: 30,
  flow_type: 'chat',
  remark: ''
})
const generateFormErrors = reactive({
  name: ''
})

// 流程详情抽屉
const flowDrawerVisible = ref(false)
const currentFlow = ref(null)

// 创建访谈链接弹窗
const createInterviewVisible = ref(false)
const creatingInterview = ref(false)
const interviewForm = reactive({
  name: '',
  dateRange: null,
  linked_flows: [],
  moderator_ids: [],
  max_participants: 10
})
const confirmedFlows = ref([])
const moderatorOptions = ref([])

// 二维码弹窗
const qrCodeVisible = ref(false)
const currentInterview = ref(null)
const qrCodeDataUrl = ref('')

// 状态映射
const statusLabelMap = { draft: '草稿', active: '进行中', completed: '已完成', archived: '已归档' }
const statusColorMap = { draft: 'default', active: 'green', completed: 'blue', archived: 'orange' }

const flowStatusLabel = { draft: '草稿', confirmed: '已确认', active: '进行中' }
const flowStatusColor = { draft: 'default', confirmed: 'green', active: 'blue' }

const interviewStatusLabel = { pending: '待开始', in_progress: '进行中', completed: '已完成', analyzing: '分析中', archived: '已入库' }
const interviewStatusColor = { pending: 'default', in_progress: 'processing', completed: 'green', analyzing: 'purple', archived: 'orange' }

const nowTick = ref(Date.now())
const displayedInterviews = computed(() => interviews.value.map(interview => ({
  ...interview,
  status: resolveInterviewStatus(interview)
})))

// 流程类型映射
const flowTypeLabel = { chat: '杂谈', questionnaire: '问卷', test: '测试' }
const flowTypeColor = { chat: 'blue', questionnaire: 'green', test: 'orange' }

const formatTime = (timeStr) => {
  if (!timeStr) return ''
  const parsed = parseToShanghai(timeStr)
  return parsed ? parsed.format('YYYY-MM-DD HH:mm') : ''
}

const resolveInterviewStatus = (interview) => {
  void nowTick.value
  if (!interview) return 'pending'

  const isParentInterview = !interview.parent_interview_id
  if (isParentInterview) {
    if ((interview.session_count || 0) >= Math.max(interview.max_participants || 1, 1)) return 'completed'
    if (interview.status === 'archived') return 'archived'
    if (interview.status === 'analyzing') return 'analyzing'
  } else if (interview.status === 'analyzing' || interview.status === 'archived') {
    return interview.status
  }

  const now = dayjs()
  const validFrom = interview.valid_from ? parseToShanghai(interview.valid_from) : null
  const validUntil = interview.valid_until ? parseToShanghai(interview.valid_until) : null

  if (validFrom && validFrom.isAfter(now)) return 'pending'
  if ((interview.session_count || 0) >= Math.max(interview.max_participants || 1, 1)) return 'completed'
  if (validUntil && !validUntil.isAfter(now)) return 'completed'
  return 'in_progress'
}

const getDocumentName = (url) => {
  if (!url) return ''
  const parts = url.split('/')
  return decodeURIComponent(parts[parts.length - 1])
}

const normalizeModeratorOption = (card) => ({
  id: card.name,
  name: card.name,
  meta: card.description || '角色卡主持人'
})

const loadModeratorOptions = async () => {
  const result = await roleCardApi.getRoleCards()
  const cards = result?.data || []
  moderatorOptions.value = cards
    .filter(card => card.enabled !== false)
    .map(normalizeModeratorOption)
}

const ensureDefaultModerator = () => {
  if (!interviewForm.moderator_ids.length && moderatorOptions.value.length > 0) {
    interviewForm.moderator_ids = [moderatorOptions.value[0].id]
  }
}

const goBack = () => {
  router.push('/project')
}

const goToInterviewList = (interview = null) => {
  const query = interview?.id ? { interview_id: String(interview.id) } : undefined
  router.push({ path: `/project/${projectId.value}/interviews`, query })
}

// 加载数据
const loadProject = async () => {
  loading.value = true
  try {
    const [projectData, flowsData, interviewsData] = await Promise.all([
      projectApi.getProject(projectId.value),
      flowApi.listFlows(projectId.value),
      interviewApi.listInterviews(projectId.value)
    ])
    project.value = projectData
    flows.value = flowsData
    interviews.value = interviewsData
  } catch (error) {
    message.error('加载项目详情失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 文档上传
const handleUpload = (file) => {
  uploading.value = true
  uploadPercent.value = 0
  const timer = setInterval(() => {
    if (uploadPercent.value < 90) {
      uploadPercent.value += 10
    }
  }, 300)

  projectApi.uploadDocument(projectId.value, file)
    .then(() => {
      uploadPercent.value = 100
      message.success('文档上传成功')
      loadProject()
    })
    .catch((error) => {
      message.error('文档上传失败: ' + (error.message || '未知错误'))
    })
    .finally(() => {
      clearInterval(timer)
      setTimeout(() => {
        uploading.value = false
        uploadPercent.value = 0
      }, 500)
    })

  return false // 阻止自动上传
}

// AI 完善
const handleEnrich = async () => {
  enriching.value = true
  try {
    await projectApi.enrichProject(projectId.value)
    message.success('AI 完善完成')
    await loadProject()
  } catch (error) {
    message.error('AI 完善失败: ' + (error.message || '未知错误'))
  } finally {
    enriching.value = false
  }
}

// 删除文档
const handleDeleteDocument = async () => {
  try {
    await projectApi.deleteDocument(projectId.value)
    message.success('文档已删除')
    await loadProject()
  } catch (error) {
    message.error('删除文档失败: ' + (error.message || '未知错误'))
  }
}

// 打开 AI 生成流程弹窗
const openGenerateFlowModal = () => {
  generateForm.name = ''
  generateForm.estimated_duration = 30
  generateForm.flow_type = 'chat'
  generateForm.remark = ''
  generateFormErrors.name = ''
  generateFlowVisible.value = true
}

// 生成访谈流程
const handleGenerateFlow = async () => {
  // 校验
  generateFormErrors.name = ''
  if (!generateForm.name.trim()) {
    generateFormErrors.name = '请输入流程名称'
    return
  }
  // 校验名称是否与现有流程重复
  const duplicate = flows.value.some(f => f.name === generateForm.name.trim())
  if (duplicate) {
    generateFormErrors.name = `流程名称「${generateForm.name.trim()}」已存在，请使用其他名称`
    return
  }

  generatingFlow.value = true
  try {
    await flowApi.generateFlow(projectId.value, {
      name: generateForm.name.trim(),
      estimated_duration: generateForm.estimated_duration,
      flow_type: generateForm.flow_type,
      remark: generateForm.remark?.trim() || ''
    })
    message.success('访谈流程生成成功')
    generateFlowVisible.value = false
    await loadProject()
  } catch (error) {
    message.error('生成流程失败: ' + (error.message || '未知错误'))
  } finally {
    generatingFlow.value = false
  }
}

// 保存流程（编辑器回调）
const handleSaveFlow = async (flowData) => {
  if (!currentFlow.value) return
  savingFlow.value = true
  try {
    await flowApi.updateFlow(projectId.value, currentFlow.value.id, {
      flow_data: flowData
    })
    message.success('流程已保存')
    await loadProject()
  } catch (error) {
    message.error('保存流程失败: ' + (error.message || '未知错误'))
  } finally {
    savingFlow.value = false
  }
}

// 确认流程
const handleConfirmFlow = async (flow) => {
  try {
    await flowApi.confirmFlow(projectId.value, flow.id)
    message.success('流程已确认')
    await loadProject()
  } catch (error) {
    message.error('确认流程失败: ' + (error.message || '未知错误'))
  }
}

// 删除流程
const handleDeleteFlow = async (flow) => {
  try {
    await flowApi.deleteFlow(projectId.value, flow.id)
    message.success('流程已删除')
    await loadProject()
  } catch (error) {
    message.error('删除流程失败')
  }
}

// 打开流程详情
const openFlowDetail = (flow) => {
  currentFlow.value = flow
  flowDrawerVisible.value = true
}

// 创建流程弹窗
const openCreateFlowModal = () => {
  newFlow.name = ''
  newFlow.estimated_duration = 30
  createFlowVisible.value = true
}

const handleCreateFlow = async () => {
  if (!newFlow.name.trim()) {
    message.error('请输入流程名称')
    return
  }
  creatingFlow.value = true
  try {
    await flowApi.createFlow(projectId.value, {
      name: newFlow.name.trim(),
      estimated_duration: newFlow.estimated_duration,
      source_type: 'manual'
    })
    message.success('流程创建成功')
    createFlowVisible.value = false
    await loadProject()
  } catch (error) {
    message.error('创建流程失败: ' + (error.message || '未知错误'))
  } finally {
    creatingFlow.value = false
  }
}

// 编辑项目
const handleUpdateProject = async () => {
  if (!editForm.name.trim()) {
    message.error('请输入项目名称')
    return
  }
  updating.value = true
  try {
    await projectApi.updateProject(projectId.value, {
      name: editForm.name.trim(),
      description: editForm.description?.trim() || '',
      status: editForm.status
    })
    message.success('项目更新成功')
    editProjectVisible.value = false
    await loadProject()
  } catch (error) {
    message.error('更新项目失败')
  } finally {
    updating.value = false
  }
}

// 下拉菜单操作
const handleMenuClick = ({ key }) => {
  if (key === 'enrich') {
    handleEnrich()
  } else if (key === 'delete') {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除项目「${project.value.name}」吗？此操作不可恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await projectApi.deleteProject(projectId.value)
          message.success('项目已删除')
          router.push('/project')
        } catch (error) {
          message.error('删除项目失败')
        }
      }
    })
  }
}

// 监听编辑弹窗打开
watch(editProjectVisible, (val) => {
  if (val && project.value) {
    editForm.name = project.value.name || ''
    editForm.description = project.value.description || ''
    editForm.status = project.value.status || 'draft'
  }
})

// --- 访谈链接相关 ---

/** 获取流程名称 */
const getFlowName = (flowId) => {
  const flow = flows.value.find(f => f.id === flowId)
  return flow ? flow.name : `流程 #${flowId}`
}

/** 生成访谈链接 */
const getInterviewLink = (interview) => {
  const origin = window.location.origin
  return `${origin}/interview/${interview.interview_token || interview.id}`
}

/** 时间禁用：结束日期不可早于开始日期，且跨度不超过一个月 */
const disabledDate = (current) => {
  if (!current) return false
  // 不限制过去日期（开始时间随意），只限制跨度
  return false
}

/** 自动生成访谈名称：项目名称 + 当前时间 */
const autoGenerateInterviewName = () => {
  if (!project.value) return
  const now = dayjs().format('YYYYMMDD_HHmm')
  interviewForm.name = `${project.value.name}_${now}`
}

/** 点击生成访谈链接按钮：先校验再打开弹窗 */
const handleGenerateInterviewLink = async () => {
  try {
    const result = await interviewApi.validateReady(projectId.value)
    if (!result.ready) {
      const detail = result.missing.join('；')
      Modal.warning({
        title: '项目尚未就绪',
        content: detail,
        okText: '知道了'
      })
      return
    }
    await loadModeratorOptions()
    // 保存已确认的流程列表供弹窗选择
    confirmedFlows.value = result.confirmed_flows.map(f => f.to_dict ? f.to_dict() : f)
    // 重置表单
    interviewForm.name = ''
    interviewForm.dateRange = null
    interviewForm.linked_flows = []
    interviewForm.moderator_ids = []
    interviewForm.max_participants = 10
    ensureDefaultModerator()
    createInterviewVisible.value = true
  } catch (error) {
    message.error('校验失败: ' + (error.message || '未知错误'))
  }
}

/** 创建访谈记录 */
const handleCreateInterview = async () => {
  if (!interviewForm.name.trim()) {
    message.error('请输入访谈名称')
    return
  }
  if (!interviewForm.dateRange || interviewForm.dateRange.length < 2) {
    message.error('请选择有效时间')
    return
  }
  if (interviewForm.linked_flows.length === 0) {
    message.error('请至少关联一个访谈流程')
    return
  }
  if (interviewForm.moderator_ids.length === 0) {
    message.error('请至少选择一位主持人')
    return
  }

  // 校验跨度不超过一个月
  const start = interviewForm.dateRange[0]
  const end = interviewForm.dateRange[1]
  if (end.diff(start, 'day') > 30) {
    message.error('有效时间跨度不能超过一个月')
    return
  }

  creatingInterview.value = true
  try {
    await interviewApi.createInterview(projectId.value, {
      name: interviewForm.name.trim(),
      valid_from: start.format('YYYY-MM-DD HH:mm:ss'),
      valid_until: end.format('YYYY-MM-DD HH:mm:ss'),
      max_participants: interviewForm.max_participants,
      linked_flows: interviewForm.linked_flows,
      moderator_ids: interviewForm.moderator_ids
    })
    message.success('访谈链接创建成功')
    createInterviewVisible.value = false
    await loadProject()
  } catch (error) {
    message.error('创建失败: ' + (error.message || '未知错误'))
  } finally {
    creatingInterview.value = false
  }
}

/** 复制访谈链接 */
const handleCopyLink = async (interview) => {
  const link = getInterviewLink(interview)
  try {
    await navigator.clipboard.writeText(link)
    message.success('链接已复制')
  } catch {
    message.error('复制失败，请手动复制')
  }
}

/** 显示二维码弹窗 */
const handleShowQrCode = async (interview) => {
  currentInterview.value = interview
  qrCodeDataUrl.value = ''
  qrCodeVisible.value = true
  // 等待弹窗渲染后生成二维码
  await nextTick()
  try {
    const link = getInterviewLink(interview)
    qrCodeDataUrl.value = await QRCode.toDataURL(link, {
      width: 240,
      margin: 2,
      color: {
        dark: '#1a1a1a',
        light: '#ffffff'
      }
    })
  } catch (err) {
    console.error('生成二维码失败:', err)
    message.error('二维码生成失败')
  }
}

/** 删除访谈记录 */
const handleDeleteInterview = async (interview) => {
  try {
    await interviewApi.deleteInterview(projectId.value, interview.id)
    message.success('访谈记录已删除')
    await loadProject()
  } catch (error) {
    message.error('删除失败: ' + (error.message || '未知错误'))
  }
}

const handleArchiveInterview = async (interview) => {
  if (!interview?.id) return

  archivingInterviewId.value = interview.id
  try {
    await interviewApi.archiveInterview(projectId.value, interview.id)
    message.success('访谈记录已入库')
    await loadProject()
  } catch (error) {
    message.error(error.message || '入库失败')
  } finally {
    archivingInterviewId.value = null
  }
}

const handleArchiveAvailableInterviews = async () => {
  const firstInterview = displayedInterviews.value[0]
  if (!firstInterview?.id) {
    message.info('没有访谈可入库')
    return
  }

  archivingAll.value = true
  try {
    await interviewApi.archiveInterview(projectId.value, firstInterview.id)
    message.success('访谈记录已入库')
    await loadProject()
  } catch (error) {
    message.error(error.message || '入库失败')
  } finally {
    archivingAll.value = false
  }
}

// 路由参数变化时重新加载
watch(
  () => route.params.project_id,
  (newId) => {
    if (newId) {
      projectId.value = parseInt(newId)
      loadProject()
    }
  },
  { immediate: true }
)

onMounted(() => {
  if (route.params.project_id) {
    projectId.value = parseInt(route.params.project_id)
  }
  setInterval(() => {
    nowTick.value = Date.now()
  }, 60000)
})
</script>

<style lang="less" scoped>
.project-detail-container {
  min-height: 100vh;
  background-color: var(--gray-25);
}

.loading-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 300px;
  gap: 16px;
}

.project-content {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-card {
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 12px;
  overflow: hidden;

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid var(--gray-100);
    background: var(--gray-10);

    h3 {
      margin: 0;
      font-size: 14px;
      font-weight: 600;
      color: var(--gray-800);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .section-actions {
      display: flex;
      gap: 8px;
    }
  }

  .section-body {
    padding: 16px;
  }
}

// AI 摘要
.ai-summary-section {
  margin-top: 16px;
  padding: 12px 16px;
  background: var(--main-5);
  border-radius: 8px;
  border: 1px solid var(--main-20);

  .summary-header {
    display: flex;
    align-items: center;
    gap: 6px;
    font-weight: 600;
    font-size: 14px;
    margin-bottom: 12px;
    color: var(--main-color);
  }

  .summary-content {
    font-size: 13px;
    color: var(--gray-800);

    .summary-item {
      margin-bottom: 8px;
      line-height: 1.6;

      &:last-child {
        margin-bottom: 0;
      }

      strong {
        color: var(--gray-700);
      }

      ul {
        margin: 4px 0;
        padding-left: 20px;
      }

      .ant-tag {
        margin: 2px 4px 2px 0;
      }
    }
  }
}

// 文档上传
.document-info {
  display: flex;
  justify-content: space-between;
  align-items: center;

  .document-item {
    display: flex;
    align-items: center;
    gap: 12px;

    svg {
      color: var(--main-color);
    }

    .document-meta {
      display: flex;
      align-items: center;
      gap: 8px;

      .document-name {
        font-size: 14px;
        color: var(--gray-800);
        font-weight: 500;
      }

      .document-status {
        font-size: 12px;
        padding: 2px 8px;
        border-radius: 4px;

        &.success {
          color: var(--color-success-700);
          background: var(--color-success-50);
        }
      }
    }
  }

  .document-actions {
    display: flex;
    gap: 8px;
  }
}

.upload-area {
  .upload-trigger {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 32px;
    border: 2px dashed var(--gray-200);
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.3s;

    &:hover {
      border-color: var(--main-color);
      background: var(--main-5);
    }

    .upload-text {
      margin: 12px 0 4px;
      font-size: 14px;
      color: var(--gray-700);
    }

    .upload-hint {
      font-size: 12px;
      color: var(--gray-500);
    }
  }
}

// 流程列表
.flow-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.flow-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--main-color);
    background: var(--main-5);
  }

  .flow-info {
    .flow-name {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 500;
      color: var(--gray-800);
      margin-bottom: 4px;
    }

    .flow-meta {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: var(--gray-600);

      .flow-duration,
      .flow-source {
        font-size: 12px;
      }
    }
  }

  .flow-actions {
    display: flex;
    gap: 4px;
  }
}

// 访谈记录列表
.interview-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

// 空状态
.empty-section {
  text-align: center;
  padding: 20px 0;
  color: var(--gray-500);
  font-size: 13px;
}

// 流程编辑器头部
.flow-editor-header {
  margin-bottom: 8px;
}

.back-btn {
  padding: 0 4px;
  color: var(--gray-600);

  &:hover {
    color: var(--main-color);
  }
}

// 流程类型标签
.flow-type-tag {
  margin-left: 4px;
  font-size: 11px;
}

// 表单错误
.form-error {
  color: #ff4d4f;
  font-size: 12px;
  margin-top: 4px;
}

// 表单提示
.form-hint {
  font-size: 12px;
  color: var(--gray-500);
  margin-top: 4px;
}

// 流程复选框列表
.interview-selection-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;

  .interview-selection-item {
    margin-bottom: 0;
  }
}

.flow-checkbox-list {
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  padding: 8px;
}

.flow-checkbox-item {
  display: flex;
  width: 100%;
  padding: 6px 8px;
  border-radius: 6px;
  margin-bottom: 4px;

  &:last-child {
    margin-bottom: 0;
  }

  &:hover {
    background: var(--gray-50);
  }
}

.flow-checkbox-content {
  display: flex;
  flex-direction: column;
  gap: 2px;

  .flow-checkbox-name {
    font-weight: 500;
    color: var(--gray-800);
    font-size: 13px;
  }

  .flow-checkbox-meta {
    font-size: 12px;
    color: var(--gray-500);
  }
}

// 访谈记录列表（重新设计）
.interview-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 12px;
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  transition: all 0.2s;
 &:hover {
      border-color: var(--main-color);
    }

  .interview-info {
    flex: 1;
    min-width: 0;
    padding: 8px;
    border: 1px solid transparent;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;

    .interview-name-row {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px;

      .interview-name {
        font-weight: 500;
        color: var(--gray-800);
        font-size: 14px;
      }
    }

    .interview-detail {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 12px;
      color: var(--gray-500);
      margin-bottom: 6px;

      .interview-participants {
        color: var(--gray-500);
      }
    }

    .interview-flows {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;

      .ant-tag {
        background: var(--color-success-50);
        color: var(--color-success-700);
        border: none;
        font-size: 11px;
      }
    }
  }

  .interview-actions {
    display: flex;
    gap: 2px;
    flex-shrink: 0;
  }
}

// 二维码弹窗
.qr-code-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 0;

  .qr-code-image-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 240px;
    height: 240px;
    padding: 8px;
    border: 1px solid var(--gray-200);
    border-radius: 12px;
    background: #fff;

    .qr-code-img {
      width: 100%;
      height: 100%;
      object-fit: contain;
    }
  }

  .qr-code-url {
    margin-top: 12px;
    font-size: 11px;
    color: var(--gray-500);
    word-break: break-all;
    text-align: center;
    max-width: 280px;
  }

  .qr-code-hint {
    margin-top: 8px;
    font-size: 12px;
    color: var(--gray-400);
  }
}
</style>
