<template>
  <div class="flow-editor">
    <!-- 工具栏 -->
    <div class="flow-toolbar">
      <div class="toolbar-left">
        <span class="flow-title">{{ flowName }}</span>
        <a-tag :color="statusColor" :bordered="false" size="small">{{ statusLabel }}</a-tag>
      </div>
      <div class="toolbar-right">
        <a-button size="small" @click="addNode" :disabled="readonly">
          <template #icon><PlusOutlined /></template>
          添加节点
        </a-button>
        <a-button
          v-if="!readonly"
          size="small"
          type="primary"
          :loading="saving"
          @click="handleSave"
        >
          保存
        </a-button>
        <a-button
          v-if="flowStatus === 'draft' && !readonly"
          size="small"
          type="primary"
          ghost
          @click="$emit('confirm')"
        >
          确认流程
        </a-button>
      </div>
    </div>

    <!-- Vue Flow 画布 -->
    <div class="flow-canvas" ref="canvasRef">
      <VueFlow
        v-model:nodes="nodes"
        v-model:edges="edges"
        :default-viewport="{ zoom: 0.9, x: 50, y: 50 }"
        :min-zoom="0.3"
        :max-zoom="2"
        fit-view-on-init
        :nodes-draggable="!readonly"
        :nodes-connectable="!readonly"
        :edges-deletable="!readonly"
        @node-click="onNodeClick"
        @connect="onConnect"
        class="vue-flow"
      >
        <Background :gap="16" />
        <Controls position="bottom-right" />

        <!-- 自定义节点模板 -->
        <template #node-interview="{ data }">
          <div class="interview-node" :class="{ active: selectedNodeId === data.nodeId }">
            <div class="node-header" :style="{ background: data.color || 'var(--main-color)' }">
              <span class="node-index">{{ data.index }}</span>
              <span class="node-label">{{ data.label }}</span>
            </div>
            <div class="node-body" v-if="data.question">
              <p class="node-question">{{ data.question }}</p>
              <span v-if="data.duration" class="node-duration">~{{ data.duration }} min</span>
            </div>
          </div>
        </template>
      </VueFlow>
    </div>

    <!-- 节点编辑抽屉 -->
    <a-drawer
      v-model:open="editDrawerVisible"
      title="编辑节点"
      width="400"
      :destroyOnClose="true"
    >
      <div v-if="editingNode" class="node-edit-form">
        <h3>节点名称</h3>
        <a-input v-model:value="editingNode.label" placeholder="节点名称" />

        <h3 style="margin-top: 16px">访谈问题</h3>
        <a-textarea
          v-model:value="editingNode.question"
          placeholder="请输入访谈问题"
          :auto-size="{ minRows: 3, maxRows: 8 }"
        />

        <h3 style="margin-top: 16px">预计时长（分钟）</h3>
        <a-input-number v-model:value="editingNode.duration" :min="1" :max="120" style="width: 100%" />

        <h3 style="margin-top: 16px">节点颜色</h3>
        <div class="color-options">
          <div
            v-for="color in nodeColors"
            :key="color"
            class="color-option"
            :class="{ active: editingNode.color === color }"
            :style="{ background: color }"
            @click="editingNode.color = color"
          />
        </div>

        <div style="margin-top: 24px; display: flex; gap: 8px">
          <a-button type="primary" @click="applyNodeEdit">应用修改</a-button>
          <a-button danger @click="deleteEditingNode">删除节点</a-button>
        </div>
      </div>
    </a-drawer>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import { PlusOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'

const props = defineProps({
  flowName: { type: String, default: '访谈流程' },
  flowData: { type: Object, default: () => ({ nodes: [], edges: [] }) },
  flowStatus: { type: String, default: 'draft' },
  saving: { type: Boolean, default: false },
  readonly: { type: Boolean, default: false }
})

const emit = defineEmits(['save', 'confirm', 'update:flowData'])

const { addEdges, getSelectedNodes, removeNodes } = useVueFlow()

const nodes = ref([])
const edges = ref([])
const canvasRef = ref(null)
const selectedNodeId = ref(null)

// 节点编辑
const editDrawerVisible = ref(false)
const editingNode = ref(null)

// 预设颜色
const nodeColors = [
  'var(--main-color)',
  'var(--color-info-500)',
  'var(--color-success-500)',
  'var(--color-warning-500)',
  'var(--color-accent-500)',
  '#8b5cf6'
]

const statusLabel = computed(() => {
  const map = { draft: '草稿', confirmed: '已确认', active: '进行中' }
  return map[props.flowStatus] || props.flowStatus
})

const statusColor = computed(() => {
  const map = { draft: 'default', confirmed: 'green', active: 'blue' }
  return map[props.flowStatus] || 'default'
})

// 从外部 flowData 转换为 VueFlow 格式
const transformToVueFlow = (data) => {
  if (!data || !data.nodes) return { nodes: [], edges: [] }

  const vfNodes = data.nodes.map((node, idx) => ({
    id: node.id || `node-${idx}`,
    type: 'interview',
    position: node.position || { x: 80, y: idx * 150 + 50 },
    data: {
      ...node.data,
      nodeId: node.id || `node-${idx}`,
      index: idx + 1,
      label: node.label || node.data?.label || `问题 ${idx + 1}`,
      question: node.data?.question || '',
      duration: node.data?.duration || 5,
      color: node.data?.color || nodeColors[idx % nodeColors.length]
    }
  }))

  const vfEdges = (data.edges || []).map((edge, idx) => ({
    id: edge.id || `edge-${idx}`,
    source: edge.source,
    target: edge.target,
    type: 'smoothstep',
    animated: true,
    style: { stroke: 'var(--gray-400)', strokeWidth: 2 }
  }))

  return { nodes: vfNodes, edges: vfEdges }
}

// 从 VueFlow 格式转回外部 flowData
const transformFromVueFlow = () => {
  const outNodes = nodes.value.map((node, idx) => ({
    id: node.id,
    label: node.data?.label || `问题 ${idx + 1}`,
    position: node.position,
    data: {
      label: node.data?.label || `问题 ${idx + 1}`,
      question: node.data?.question || '',
      duration: node.data?.duration || 5,
      color: node.data?.color || nodeColors[idx % nodeColors.length]
    }
  }))

  const outEdges = edges.value.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target
  }))

  return { nodes: outNodes, edges: outEdges }
}

// 监听外部 flowData 变化
watch(
  () => props.flowData,
  (newData) => {
    const transformed = transformToVueFlow(newData)
    nodes.value = transformed.nodes
    edges.value = transformed.edges
  },
  { immediate: true, deep: true }
)

// 节点点击
const onNodeClick = ({ node }) => {
  if (props.readonly) return
  selectedNodeId.value = node.data?.nodeId

  editingNode.value = {
    id: node.id,
    label: node.data?.label || '',
    question: node.data?.question || '',
    duration: node.data?.duration || 5,
    color: node.data?.color || 'var(--main-color)'
  }
  editDrawerVisible.value = true
}

// 连线
const onConnect = (params) => {
  addEdges([{
    ...params,
    type: 'smoothstep',
    animated: true,
    style: { stroke: 'var(--gray-400)', strokeWidth: 2 }
  }])
}

// 添加节点
const addNode = () => {
  const idx = nodes.value.length
  const lastNode = nodes.value[idx - 1]
  const newNode = {
    id: `node-${Date.now()}`,
    type: 'interview',
    position: { x: 80, y: idx * 150 + 50 },
    data: {
      nodeId: `node-${Date.now()}`,
      index: idx + 1,
      label: `问题 ${idx + 1}`,
      question: '',
      duration: 5,
      color: nodeColors[idx % nodeColors.length]
    }
  }
  nodes.value = [...nodes.value, newNode]

  // 自动连线到上一个节点
  if (lastNode) {
    edges.value = [...edges.value, {
      id: `edge-${Date.now()}`,
      source: lastNode.id,
      target: newNode.id,
      type: 'smoothstep',
      animated: true,
      style: { stroke: 'var(--gray-400)', strokeWidth: 2 }
    }]
  }
}

// 应用节点编辑
const applyNodeEdit = () => {
  if (!editingNode.value) return

  nodes.value = nodes.value.map((node) => {
    if (node.id === editingNode.value.id) {
      return {
        ...node,
        data: {
          ...node.data,
          label: editingNode.value.label,
          question: editingNode.value.question,
          duration: editingNode.value.duration,
          color: editingNode.value.color
        }
      }
    }
    return node
  })

  editDrawerVisible.value = false
  message.success('节点已更新')
}

// 删除编辑中的节点
const deleteEditingNode = () => {
  if (!editingNode.value) return
  removeNodes([editingNode.value.id])
  editDrawerVisible.value = false
  message.success('节点已删除')
}

// 保存
const handleSave = () => {
  const data = transformFromVueFlow()
  emit('save', data)
}
</script>

<style lang="less" scoped>
.flow-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--gray-0);
  border-radius: 12px;
  border: 1px solid var(--gray-150);
  overflow: hidden;
}

.flow-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  border-bottom: 1px solid var(--gray-150);
  background: var(--gray-10);

  .toolbar-left {
    display: flex;
    align-items: center;
    gap: 8px;

    .flow-title {
      font-weight: 600;
      font-size: 15px;
      color: var(--gray-800);
    }
  }

  .toolbar-right {
    display: flex;
    gap: 8px;
  }
}

.flow-canvas {
  flex: 1;
  height: 500px;
  min-height: 400px;

  .vue-flow {
    width: 100%;
    height: 100%;
  }
}

// 自定义节点样式
.interview-node {
  min-width: 200px;
  max-width: 280px;
  background: var(--gray-0);
  border-radius: 8px;
  border: 2px solid var(--gray-200);
  box-shadow: 0 2px 6px var(--shadow-2);
  overflow: hidden;
  transition: all 0.2s;

  &.active {
    border-color: var(--main-color);
    box-shadow: 0 0 0 2px var(--main-30), 0 2px 8px var(--shadow-3);
  }

  &:hover {
    border-color: var(--main-color);
  }

  .node-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    color: white;
    font-size: 13px;
    font-weight: 600;

    .node-index {
      width: 22px;
      height: 22px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.3);
      display: flex;
      justify-content: center;
      align-items: center;
      font-size: 11px;
      flex-shrink: 0;
    }

    .node-label {
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .node-body {
    padding: 8px 12px;

    .node-question {
      margin: 0;
      font-size: 12px;
      color: var(--gray-600);
      line-height: 1.5;
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .node-duration {
      display: block;
      margin-top: 4px;
      font-size: 11px;
      color: var(--gray-500);
    }
  }
}

// 节点编辑表单
.node-edit-form {
  h3 {
    margin-bottom: 8px;
    font-size: 13px;
    font-weight: 600;
    color: var(--gray-700);
  }
}

.color-options {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;

  .color-option {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    cursor: pointer;
    border: 2px solid transparent;
    transition: all 0.2s;

    &:hover {
      transform: scale(1.1);
    }

    &.active {
      border-color: var(--gray-800);
      box-shadow: 0 0 0 2px var(--gray-0);
    }
  }
}
</style>
