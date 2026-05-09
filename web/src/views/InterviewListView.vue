<template>
  <div class="interview-list-container layout-container">
    <HeaderComponent :title="projectName || '访谈列表'">
      <template #left>
        <a-button type="text" @click="goBack" class="back-btn">
          <template #icon><ArrowLeft :size="18" /></template>
        </a-button>
      </template>
    </HeaderComponent>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <a-spin size="large" />
      <p>正在加载...</p>
    </div>

    <template v-else>
      <div class="interview-list-content">
        <!-- 统计卡片 -->
        <div class="stats-row">
          <div class="stat-card" style="--accent: var(--color-success-700); --accent-bg: var(--color-success-10)">
            <div class="stat-icon" style="background: var(--color-success-10); color: var(--color-success-700)">
              <CheckCircle :size="20" />
            </div>
            <div class="stat-body">
              <span class="stat-value">{{ stats.completed }}</span>
              <span class="stat-label">已完成</span>
            </div>
          </div>

          <div class="stat-card" style="--accent: var(--color-primary-700); --accent-bg: var(--color-primary-50)">
            <div class="stat-icon" style="background: var(--color-primary-50); color: var(--color-primary-700)">
              <Clock :size="20" />
            </div>
            <div class="stat-body">
              <span class="stat-value">{{ stats.in_progress }}</span>
              <span class="stat-label">进行中</span>
            </div>
          </div>

          <div class="stat-card" style="--accent: var(--color-warning-700); --accent-bg: var(--color-warning-10)">
            <div class="stat-icon" style="background: var(--color-warning-10); color: var(--color-warning-700)">
              <Timer :size="20" />
            </div>
            <div class="stat-body">
              <span class="stat-value">{{ remainingDuration }}</span>
              <span class="stat-label">剩余时长</span>
            </div>
          </div>

          <div class="stat-card" style="--accent: #722ed1; --accent-bg: #f9f0ff">
            <div class="stat-icon" style="background: #f9f0ff; color: #722ed1">
              <Database :size="20" />
            </div>
            <div class="stat-body">
              <span class="stat-value">{{ stats.analyzing + stats.archived }}</span>
              <span class="stat-label">分析入库</span>
            </div>
          </div>
        </div>

        <!-- 筛选 + 表格 -->
        <div class="section-card">
          <div class="section-header">
            <h3><FileText :size="16" /> 访谈记录</h3>
            <div class="filter-tabs">
              <a-radio-group v-model:value="currentFilter" button-style="solid" size="small" @change="handleFilterChange">
                <a-radio-button value="">全部</a-radio-button>
                <a-radio-button value="completed">已完成</a-radio-button>
                <a-radio-button value="analyzing">已分析</a-radio-button>
                <a-radio-button value="archived">已入库</a-radio-button>
              </a-radio-group>
            </div>
          </div>
          <div class="section-body">
            <a-table
              :columns="columns"
              :data-source="tableData"
              :pagination="paginationConfig"
              :loading="tableLoading"
              row-key="id"
              size="middle"
              @change="handleTableChange"
              :locale="{ emptyText: currentFilter ? '当前筛选条件下暂无访谈记录' : '暂无访谈记录' }"
            >
              <!-- 访谈名称 -->
              <template #bodyCell="{ column, record }">
                <template v-if="column.dataIndex === 'name'">
                  <span class="interview-name-cell">{{ record.name || '访谈 #' + record.id }}</span>
                </template>

                <!-- 状态 -->
                <template v-else-if="column.dataIndex === 'status'">
                  <a-tag :color="statusColorMap[record.status] || 'default'" :bordered="false" size="small">
                    {{ statusLabelMap[record.status] || record.status }}
                  </a-tag>
                </template>

                <!-- 开始时间 -->
                <template v-else-if="column.dataIndex === 'started_at'">
                  {{ formatTime(record.started_at) }}
                </template>

                <!-- 完成时间 -->
                <template v-else-if="column.dataIndex === 'completed_at'">
                  {{ formatTime(record.completed_at) }}
                </template>

                <!-- 关联流程 -->
                <template v-else-if="column.dataIndex === 'linked_flows'">
                  <div v-if="record.linked_flows && record.linked_flows.length > 0" class="flow-tags">
                    <a-tag
                      v-for="flowId in record.linked_flows"
                      :key="flowId"
                      color="blue"
                      :bordered="false"
                      size="small"
                    >
                      {{ getFlowName(flowId) }}
                    </a-tag>
                  </div>
                  <span v-else class="text-muted">-</span>
                </template>

                <!-- 操作 -->
                <template v-else-if="column.dataIndex === 'actions'">
                  <div class="action-btns">
                    <a-button type="link" size="small" @click="handleView(record)">
                      <EyeOutlined /> 查看
                    </a-button>
                    <a-button type="link" size="small" :loading="analyzingId === record.id" @click="handleAnalyze(record)">
                      分析
                    </a-button>
                    <a-button type="link" size="small" @click="handleExport(record)">
                      <DownloadOutlined /> 导出
                    </a-button>
                    <a-popconfirm
                      title="确定删除此访谈记录？"
                      @confirm="handleDelete(record)"
                      ok-text="确定"
                      cancel-text="取消"
                    >
                      <a-button type="link" size="small" danger>删除</a-button>
                    </a-popconfirm>
                  </div>
                </template>
              </template>
            </a-table>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { ArrowLeft, FileText, CheckCircle, Clock, Timer, Database } from 'lucide-vue-next'
import { EyeOutlined, DownloadOutlined } from '@ant-design/icons-vue'
import { interviewApi, projectApi } from '@/apis/project_api'
import HeaderComponent from '@/components/HeaderComponent.vue'
import dayjs, { parseToShanghai } from '@/utils/time'

const route = useRoute()
const router = useRouter()

const projectId = ref(null)
const projectName = ref('')
const loading = ref(false)
const tableLoading = ref(false)

// 统计数据
const stats = reactive({
  total: 0,
  pending: 0,
  in_progress: 0,
  completed: 0,
  analyzing: 0,
  archived: 0,
  remaining_seconds: 0
})

// 表格数据
const tableData = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const currentFilter = ref('')
const analyzingId = ref(null)
const parentInterviewId = computed(() => {
  const raw = route.query.interview_id
  if (!raw) return null
  const parsed = Number(Array.isArray(raw) ? raw[0] : raw)
  return Number.isFinite(parsed) ? parsed : null
})

// 状态映射
const statusLabelMap = {
  pending: '待开始',
  in_progress: '进行中',
  completed: '已完成',
  analyzing: '已分析',
  archived: '已入库'
}

const statusColorMap = {
  pending: 'default',
  in_progress: 'processing',
  completed: 'green',
  analyzing: 'purple',
  archived: 'orange'
}

// 剩余时长格式化
const remainingDuration = computed(() => {
  const seconds = stats.remaining_seconds
  if (seconds <= 0) return '0h'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (hours > 0 && minutes > 0) return `${hours}h ${minutes}m`
  if (hours > 0) return `${hours}h`
  return `${minutes}m`
})

// 表格列定义
const columns = [
  { title: '访谈名称', dataIndex: 'name', width: 200 },
  { title: '状态', dataIndex: 'status', width: 100 },
  { title: '开始时间', dataIndex: 'started_at', width: 170 },
  { title: '完成时间', dataIndex: 'completed_at', width: 170 },
  { title: '关联流程', dataIndex: 'linked_flows', width: 200 },
  { title: '操作', dataIndex: 'actions', width: 200, fixed: 'right' }
]

// 分页配置
const paginationConfig = computed(() => {
  if (total.value === 0) return false
  return {
    current: currentPage.value,
    pageSize: pageSize.value,
    total: total.value,
    showSizeChanger: true,
    showQuickJumper: true,
    pageSizeOptions: ['10', '20', '50'],
    showTotal: (t) => `共 ${t} 条`,
    size: 'small'
  }
})

// 流程名称缓存
const flowNames = ref({})

const formatTime = (timeStr) => {
  if (!timeStr) return '-'
  const parsed = parseToShanghai(timeStr)
  return parsed ? parsed.format('YYYY-MM-DD HH:mm') : '-'
}

const getFlowName = (flowId) => {
  return flowNames.value[flowId] || `流程 #${flowId}`
}

const goBack = () => {
  router.push({ path: `/project/${projectId.value}` })
}

// 加载统计数据
const loadStats = async () => {
  try {
    const data = await interviewApi.getInterviewStats(projectId.value)
    Object.assign(stats, data)
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

// 加载表格数据
const loadTableData = async () => {
  tableLoading.value = true
  try {
    const result = await interviewApi.listInterviewsPaginated(projectId.value, {
      status: currentFilter.value || undefined,
      page: currentPage.value,
      pageSize: pageSize.value,
      interviewId: parentInterviewId.value || undefined
    })
    tableData.value = result.items || []
    total.value = result.total || 0
  } catch (error) {
    message.error('加载访谈列表失败')
    console.error(error)
  } finally {
    tableLoading.value = false
  }
}

// 筛选切换
const handleFilterChange = () => {
  currentPage.value = 1
  loadTableData()
}

// 表格分页变化
const handleTableChange = (pagination) => {
  currentPage.value = pagination.current
  pageSize.value = pagination.pageSize
  loadTableData()
}

// 查看详情（占位）
const handleView = (record) => {
  message.info('访谈详情页开发中')
}

// 导出文本记录
const handleExport = async (record) => {
  try {
    const response = await interviewApi.exportInterviewTranscript(projectId.value, record.id)
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${record.name || `interview-${record.id}`}-transcript.txt`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    message.success('导出成功')
  } catch (error) {
    console.error(error)
    message.error('导出失败')
  }
}

const handleAnalyze = async (record) => {
  if (!record?.id) return
  analyzingId.value = record.id
  try {
    await interviewApi.analyzeInterview(projectId.value, record.id)
    message.success('分析完成')
    await loadStats()
    await loadTableData()
  } catch (error) {
    console.error(error)
    message.error(error.message || '分析失败')
  } finally {
    analyzingId.value = null
  }
}

// 删除
const handleDelete = async (record) => {
  try {
    await interviewApi.deleteInterview(projectId.value, record.id)
    message.success('删除成功')
    await loadStats()
    await loadTableData()
  } catch (error) {
    message.error('删除失败: ' + (error.message || '未知错误'))
  }
}

// 初始化
const init = async () => {
  loading.value = true
  try {
    if (parentInterviewId.value) {
      currentFilter.value = 'completed'
    }
    const [projectData] = await Promise.all([
      projectApi.getProject(projectId.value),
      loadStats()
    ])
    projectName.value = projectData.name || '访谈列表'
    await loadTableData()
  } catch (error) {
    message.error('加载数据失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

watch(
  () => route.params.project_id,
  (newId) => {
    if (newId) {
      projectId.value = parseInt(newId)
      init()
    }
  },
  { immediate: true }
)
</script>

<style lang="less" scoped>
.interview-list-container {
  min-height: 100vh;
  background-color: var(--gray-25);
  padding: 0;

  .header-container {
    padding-left: 30px;
    padding-right: 30px;
  }
}

.loading-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 300px;
  gap: 16px;
}

.interview-list-content {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.back-btn {
  padding: 0 4px;
  color: var(--gray-600);

  &:hover {
    color: var(--main-color);
  }
}

// 统计卡片行
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.stat-card {
  background: var(--gray-0);
  border: 1px solid var(--gray-150);
  border-radius: 10px;
  padding: 14px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: all 0.2s;

  &:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    transform: translateY(-1px);
  }

  .stat-icon {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    display: flex;
    justify-content: center;
    align-items: center;
    flex-shrink: 0;
  }

  .stat-body {
    display: flex;
    flex-direction: column;
    gap: 2px;

    .stat-value {
      font-size: 20px;
      font-weight: 600;
      color: var(--gray-800);
      line-height: 1.2;
    }

    .stat-label {
      font-size: 12px;
      color: var(--gray-500);
      font-weight: 400;
    }
  }
}

// section-card 样式（复用 ProjectDetailView 模式）
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
  }

  .section-body {
    padding: 16px;
  }
}

// 筛选标签
.filter-tabs {
  :deep(.ant-radio-group) {
    .ant-radio-button-wrapper {
      font-size: 12px;
      height: 28px;
      line-height: 26px;
      padding: 0 12px;
    }
  }
}

// 空状态
.empty-section {
  text-align: center;
  padding: 40px 0;
  color: var(--gray-500);
  font-size: 13px;
}

// 表格内样式
.interview-name-cell {
  font-weight: 500;
  color: var(--gray-800);
}

.flow-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.text-muted {
  color: var(--gray-400);
}

.action-btns {
  display: flex;
  gap: 0;
  align-items: center;

  .ant-btn-link {
    font-size: 12px;
    padding: 0 4px;
    height: 24px;
  }
}

// 响应式
@media (max-width: 768px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
