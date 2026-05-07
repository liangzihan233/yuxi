<template>
  <div class="project-container layout-container">
    <HeaderComponent title="访谈调研">
      <template #actions>
        <a-button type="primary" @click="openCreateModal">
          <template #icon><PlusOutlined /></template>
          新建项目
        </a-button>
      </template>
    </HeaderComponent>

    <!-- 新建项目弹窗 -->
    <a-modal
      :open="createModalVisible"
      title="新建项目"
      :confirm-loading="creating"
      @ok="handleCreate"
      @cancel="cancelCreate"
      width="600px"
      destroyOnClose
    >
      <h3>项目名称<span style="color: var(--color-error-500)">*</span></h3>
      <a-input v-model:value="newProject.name" placeholder="请输入项目名称" size="large" />

      <h3 style="margin-top: 20px">项目描述</h3>
      <a-textarea
        v-model:value="newProject.description"
        placeholder="请输入项目描述（可选）"
        :auto-size="{ minRows: 3, maxRows: 6 }"
        size="large"
      />

      <template #footer>
        <a-button @click="cancelCreate">取消</a-button>
        <a-button type="primary" :loading="creating" @click="handleCreate">创建</a-button>
      </template>
    </a-modal>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <a-spin size="large" />
      <p>正在加载项目...</p>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!projects || projects.length === 0" class="empty-state">
      <h3 class="empty-title">暂无项目</h3>
      <p class="empty-description">创建您的第一个访谈调研项目，开始管理访谈流程</p>
      <a-button type="primary" size="large" @click="openCreateModal">
        <template #icon><PlusOutlined /></template>
        创建项目
      </a-button>
    </div>

    <!-- 项目列表 -->
    <div v-else class="projects">
      <div
        v-for="project in projects"
        :key="project.id"
        class="project card"
        @click="navigateToProject(project.id)"
      >
        <div class="top">
          <div class="icon">
            <ClipboardList :size="24" />
          </div>
          <div class="info">
            <h3>{{ project.name }}</h3>
            <p>
              <span>{{ project.interview_count || 0 }} 个访谈</span>
              <span class="flow-count">{{ project.flow_count || 0 }} 个流程</span>
              <span class="created-time-inline" v-if="project.created_at">
                {{ formatCreatedTime(project.created_at) }}
              </span>
            </p>
          </div>
        </div>
        <p class="description">{{ project.description || '暂无描述' }}</p>
        <div class="tags">
          <a-tag :bordered="false" :color="statusColorMap[project.status] || 'default'" size="small">
            {{ statusLabelMap[project.status] || project.status }}
          </a-tag>
          <a-tag v-if="project.document_url" color="blue" :bordered="false">已上传文档</a-tag>
          <a-tag v-if="project.ai_summary" color="purple" :bordered="false">AI 已完善</a-tag>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { PlusOutlined } from '@ant-design/icons-vue'
import { ClipboardList } from 'lucide-vue-next'
import { message } from 'ant-design-vue'
import { projectApi } from '@/apis/project_api'
import HeaderComponent from '@/components/HeaderComponent.vue'
import dayjs, { parseToShanghai } from '@/utils/time'

const router = useRouter()

const loading = ref(false)
const creating = ref(false)
const createModalVisible = ref(false)
const projects = ref([])

const newProject = reactive({
  name: '',
  description: ''
})

const statusLabelMap = {
  draft: '草稿',
  active: '进行中',
  completed: '已完成',
  archived: '已归档'
}

const statusColorMap = {
  draft: 'default',
  active: 'green',
  completed: 'blue',
  archived: 'orange'
}

const formatCreatedTime = (createdAt) => {
  if (!createdAt) return ''
  const parsed = parseToShanghai(createdAt)
  if (!parsed) return ''
  const today = dayjs().startOf('day')
  const createdDay = parsed.startOf('day')
  const diffInDays = today.diff(createdDay, 'day')
  if (diffInDays === 0) return '今天创建'
  if (diffInDays === 1) return '昨天创建'
  if (diffInDays < 7) return `${diffInDays} 天前创建`
  if (diffInDays < 30) return `${Math.floor(diffInDays / 7)} 周前创建`
  if (diffInDays < 365) return `${Math.floor(diffInDays / 30)} 个月前创建`
  return `${Math.floor(diffInDays / 365)} 年前创建`
}

const loadProjects = async () => {
  loading.value = true
  try {
    projects.value = await projectApi.listProjects()
  } catch (error) {
    message.error('加载项目列表失败')
    console.error('加载项目失败:', error)
  } finally {
    loading.value = false
  }
}

const openCreateModal = () => {
  createModalVisible.value = true
}

const cancelCreate = () => {
  createModalVisible.value = false
  newProject.name = ''
  newProject.description = ''
}

const handleCreate = async () => {
  if (!newProject.name.trim()) {
    message.error('请输入项目名称')
    return
  }
  creating.value = true
  try {
    await projectApi.createProject({
      name: newProject.name.trim(),
      description: newProject.description?.trim() || ''
    })
    message.success('项目创建成功')
    cancelCreate()
    await loadProjects()
  } catch (error) {
    message.error('创建项目失败: ' + (error.message || '未知错误'))
  } finally {
    creating.value = false
  }
}

const navigateToProject = (projectId) => {
  router.push({ path: `/project/${projectId}` })
}

onMounted(() => {
  loadProjects()
})
</script>

<style lang="less" scoped>
.project-container {
  padding: 0;
}

.loading-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 300px;
  gap: 16px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 100px 20px;
  text-align: center;

  .empty-title {
    font-size: 20px;
    font-weight: 600;
    color: var(--gray-900);
    margin: 0 0 12px 0;
    letter-spacing: -0.02em;
  }

  .empty-description {
    font-size: 14px;
    color: var(--gray-600);
    margin: 0 0 32px 0;
    line-height: 1.5;
    max-width: 320px;
  }

  .ant-btn {
    height: 44px;
    padding: 0 24px;
    font-size: 15px;
    font-weight: 500;
  }
}

.projects {
  padding: 12px 16px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.card {
  background: linear-gradient(45deg, var(--gray-0) 0%, var(--gray-25) 100%);
  box-shadow: 0px 1px 2px 0px var(--shadow-2);
  border: 1px solid var(--gray-50);
  transition: all 0.3s;
  position: relative;

  &:hover {
    background: linear-gradient(45deg, var(--gray-0) 0%, var(--main-30) 100%);
    box-shadow: 0px 1px 5px var(--shadow-3);
  }
}

.project {
  width: 100%;
  padding: 8px 12px;
  border-radius: 8px;
  height: 140px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;

  .top {
    display: flex;
    align-items: center;
    height: 54px;
    margin-bottom: 14px;

    .icon {
      width: 50px;
      height: 50px;
      font-size: 24px;
      margin-right: 14px;
      display: flex;
      justify-content: center;
      align-items: center;
      background: var(--main-30);
      border-radius: 12px;
      border: 1px solid var(--gray-150);
      color: var(--main-color);
      position: relative;
    }

    .info {
      flex: 1;
      min-width: 0;

      h3,
      p {
        margin: 0;
        color: var(--gray-10000);
      }

      h3 {
        font-size: 16px;
        font-weight: 600;
        letter-spacing: -0.02em;
        line-height: 1.4;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      p {
        color: var(--gray-700);
        font-size: 13px;
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        margin-top: 4px;
        font-weight: 400;

        .flow-count {
          color: var(--gray-700);
          font-size: 11px;
        }

        .created-time-inline {
          color: var(--gray-700);
          font-size: 11px;
          font-weight: 400;
          background: var(--gray-50);
          padding: 2px 6px;
          border-radius: 4px;
        }
      }
    }
  }

  .description {
    color: var(--gray-600);
    overflow: hidden;
    display: -webkit-box;
    line-clamp: 1;
    -webkit-line-clamp: 1;
    -webkit-box-orient: vertical;
    text-overflow: ellipsis;
    margin-bottom: 12px;
    font-size: 13px;
    font-weight: 400;
    flex: 1;
  }

  .tags {
    opacity: 0.8;
  }
}
</style>
