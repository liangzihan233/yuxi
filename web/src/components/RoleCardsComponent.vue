<template>
  <div class="role-cards-component extension-page-root">
    <div v-if="loading" class="loading-bar-wrapper">
      <div class="loading-bar"></div>
    </div>
    <div class="layout-wrapper" :class="{ 'content-loading': loading }">
      <div class="sidebar-list">
        <div class="sidebar-toolbar">
          <div class="search-box">
            <a-input
              v-model:value="searchQuery"
              placeholder="搜索角色卡..."
              allow-clear
              class="search-input"
            >
              <template #prefix><Search :size="14" class="text-muted" /></template>
            </a-input>
          </div>

          <a-tooltip title="刷新角色卡">
            <a-button class="sidebar-tool" :disabled="loading" @click="fetchRoleCards">
              <RotateCw :size="14" />
            </a-button>
          </a-tooltip>
        </div>

        <div class="list-container">
          <div
            v-if="!filteredEnabledRoleCards.length && !filteredDisabledRoleCards.length"
            class="empty-text"
          >
            <a-empty :image="false" :description="searchQuery ? '无匹配角色卡' : '暂无角色卡'" />
          </div>
          <div v-if="filteredEnabledRoleCards.length" class="list-section-title">已添加</div>
          <template v-for="(card, index) in filteredEnabledRoleCards" :key="`enabled-${card.name}`">
            <div
              class="list-item extension-list-item"
              :class="{ active: currentCard?.name === card.name }"
              @click="selectCard(card)"
            >
              <div class="item-main-row">
                <div class="item-header">
                  <Bot :size="16" class="item-icon" />
                  <span class="item-name">{{ card.name }}</span>
                </div>
                <div class="item-status">
                  <span class="status-chip status-chip-success">已添加</span>
                  <button
                    type="button"
                    class="inline-hover-action danger"
                    @click.stop="confirmDeleteCard(card)"
                  >
                    移除
                  </button>
                </div>
              </div>
            </div>
            <div
              v-if="index < filteredEnabledRoleCards.length - 1 || filteredDisabledRoleCards.length > 0"
              class="list-separator"
            ></div>
          </template>

          <div v-if="filteredDisabledRoleCards.length" class="list-section-title">可添加</div>
          <template v-for="(card, index) in filteredDisabledRoleCards" :key="`disabled-${card.name}`">
            <div
              class="list-item extension-list-item"
              :class="{ active: currentCard?.name === card.name }"
              @click="selectCard(card)"
            >
              <div class="item-main-row">
                <div class="item-header">
                  <Bot :size="16" class="item-icon" />
                  <span class="item-name">{{ card.name }}</span>
                </div>
                <div class="item-status">
                  <span class="status-chip">未添加</span>
                </div>
              </div>
            </div>
            <div v-if="index < filteredDisabledRoleCards.length - 1" class="list-separator"></div>
          </template>
        </div>
      </div>

      <div class="main-panel">
        <div v-if="!currentCard" class="unselected-state">
          <div class="hint-box">
            <Bot :size="40" class="text-muted" />
            <p>请在左侧选择角色卡进行查看</p>
          </div>
        </div>

        <template v-else>
          <div class="panel-top-bar">
            <h2 class="panel-title-row">
              <Bot :size="18" class="panel-title-icon" />
              <span><strong>{{ currentCard.name }}</strong></span>
            </h2>
            <div class="panel-actions">
              <a-space :size="8">
                <a-button
                  size="small"
                  @click="showEditModal(currentCard)"
                  class="lucide-icon-btn"
                  v-if="!currentCard.is_builtin"
                >
                  <Pencil :size="14" />
                  <span>编辑</span>
                </a-button>
                <a-button
                  size="small"
                  danger
                  ghost
                  :disabled="currentCard.is_builtin"
                  @click="confirmDeleteCard(currentCard)"
                  class="lucide-icon-btn"
                  v-if="!currentCard.is_builtin"
                >
                  <Trash2 :size="14" />
                  <span>删除</span>
                </a-button>
              </a-space>
            </div>
          </div>

          <div class="detail-section-container">
            <div class="detail-section">
              <div class="section-header">
                <MessageSquare :size="14" />
                <span>系统提示词</span>
              </div>
              <div class="section-content">
                <div class="code-panel">
                  <pre class="code-panel-pre">{{ currentCard.system_prompt }}</pre>
                </div>
              </div>
            </div>

            <div class="detail-section">
              <div class="section-header">
                <FileText :size="14" />
                <span>描述</span>
              </div>
              <div class="section-content description">
                {{ currentCard.description || '暂无描述' }}
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <a-modal
      v-model:open="formModalVisible"
      :title="editMode ? '编辑角色卡' : '添加角色卡'"
      @ok="handleFormSubmit"
      :confirmLoading="formLoading"
      @cancel="formModalVisible = false"
      :maskClosable="false"
      width="600px"
    >
      <a-form layout="vertical" class="extension-form">
        <a-form-item label="名称" required class="form-item">
          <a-input v-model:value="form.name" placeholder="请输入角色卡名称（唯一标识）" :disabled="editMode" />
        </a-form-item>

        <a-form-item label="描述" class="form-item">
          <a-input v-model:value="form.description" placeholder="请输入角色卡描述" />
        </a-form-item>

        <a-form-item label="角色信息" required class="form-item">
          <a-textarea v-model:value="form.system_prompt" placeholder="请输入角色信息" :rows="6" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { Search, Bot, RotateCw, MessageSquare, FileText, Pencil, Trash2 } from 'lucide-vue-next'
import { roleCardApi } from '@/apis/rolecard_api'

const loading = ref(false)
const roleCards = ref([])
const searchQuery = ref('')
const currentCard = ref(null)
const formModalVisible = ref(false)
const formLoading = ref(false)
const editMode = ref(false)
const form = reactive({
  name: '',
  description: '',
  system_prompt: '',
})

const getSortedRoleCards = (items) => {
  return [...items].sort((a, b) => {
    if (a.is_builtin !== b.is_builtin) {
      return a.is_builtin ? -1 : 1
    }
    return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  })
}

const filteredRoleCards = computed(() => {
  const sorted = getSortedRoleCards(roleCards.value)
  if (!searchQuery.value) return sorted
  const q = searchQuery.value.toLowerCase()
  return sorted.filter(
    (item) => item.name.toLowerCase().includes(q) || (item.system_prompt || '').toLowerCase().includes(q)
  )
})

const filteredEnabledRoleCards = computed(() => filteredRoleCards.value.filter((item) => item.enabled !== false))
const filteredDisabledRoleCards = computed(() => filteredRoleCards.value.filter((item) => item.enabled === false))

const fetchRoleCards = async () => {
  try {
    loading.value = true
    const result = await roleCardApi.getRoleCards()
    if (result.success) {
      roleCards.value = result.data || []
      if (currentCard.value) {
        const latest = roleCards.value.find((item) => item.name === currentCard.value.name)
        if (latest) {
          currentCard.value = latest
        } else {
          currentCard.value = null
        }
      }
      const defaultList = filteredEnabledRoleCards.value.length ? filteredEnabledRoleCards.value : filteredDisabledRoleCards.value
      if (!currentCard.value && defaultList.length > 0) {
        currentCard.value = defaultList[0]
      }
    }
  } finally {
    loading.value = false
  }
}

const selectCard = (card) => {
  currentCard.value = card
}

const showAddModal = () => {
  editMode.value = false
  Object.assign(form, {
    name: '',
    description: '',
    system_prompt: '',
  })
  formModalVisible.value = true
}

const showEditModal = async (card) => {
  try {
    const result = await roleCardApi.getRoleCard(card.name)
    if (result.success && result.data) {
      editMode.value = true
      Object.assign(form, {
        name: result.data.name,
        description: result.data.description || '',
        system_prompt: result.data.system_prompt || '',
      })
      formModalVisible.value = true
      return
    }
  } catch (err) {
    console.error('获取角色卡详情失败，回退使用列表数据:', err)
  }
  editMode.value = true
  Object.assign(form, {
    name: card.name,
    description: card.description || '',
    system_prompt: card.system_prompt || '',
  })
  formModalVisible.value = true
}

const handleFormSubmit = async () => {
  if (!form.name?.trim()) {
    message.error('名称不能为空')
    return
  }
  if (!form.system_prompt?.trim()) {
    message.error('系统提示词不能为空')
    return
  }

  try {
    formLoading.value = true
    if (editMode.value) {
      const result = await roleCardApi.updateRoleCard(form.name, {
        description: form.description || '',
        system_prompt: form.system_prompt,
      })
      if (!result.success) {
        message.error(result.message || '更新失败')
        return
      }
      message.success('角色卡更新成功')
    } else {
      const result = await roleCardApi.createRoleCard({
        name: form.name.trim(),
        description: form.description || '',
        system_prompt: form.system_prompt,
      })
      if (!result.success) {
        message.error(result.message || '创建失败')
        return
      }
      message.success('角色卡创建成功')
    }

    formModalVisible.value = false
    await fetchRoleCards()
    const latest = roleCards.value.find((item) => item.name === form.name.trim())
    if (latest) {
      currentCard.value = latest
    }
  } catch (err) {
    console.error('角色卡操作失败:', err)
    message.error(err.message || '操作失败')
  } finally {
    formLoading.value = false
  }
}

const confirmDeleteCard = (card) => {
  Modal.confirm({
    title: '确认删除角色卡',
    content: `确定要删除角色卡 "${card.name}" 吗？此操作不可撤销。`,
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      try {
        const result = await roleCardApi.deleteRoleCard(card.name)
        if (result.success) {
          message.success('角色卡删除成功')
          if (currentCard.value?.name === card.name) {
            currentCard.value = null
          }
          await fetchRoleCards()
        } else {
          message.error(result.message || '删除失败')
        }
      } catch (err) {
        console.error('删除角色卡失败:', err)
        message.error(err.message || '删除失败')
      }
    }
  })
}

onMounted(() => {
  fetchRoleCards()
})

defineExpose({
  fetchRoleCards,
  showAddModal,
})
</script>

<style lang="less" scoped>
@import '@/assets/css/extensions.less';
</style>
