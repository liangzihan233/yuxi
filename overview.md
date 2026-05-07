# Yuxi 二次开发 - 前端页面开发完成

## 完成概览

本次完成了 outset_demo1.0 一期前端核心页面的开发，包括项目列表、项目详情、流程编辑器三个核心页面，并集成到现有 Yuxi 系统中。

## 新增文件 (4个)

| 文件 | 说明 |
|------|------|
| `web/src/apis/project_api.js` | 项目/流程/访谈 API 模块，11 个接口 |
| `web/src/views/ProjectListView.vue` | 项目列表页 - 卡片布局，新建项目弹窗 |
| `web/src/views/ProjectDetailView.vue` | 项目详情页 - 四区块：信息/文档/流程/访谈 |
| `web/src/components/InterviewFlowEditor.vue` | Vue Flow 流程可视化编辑器 |

## 修改文件 (2个)

| 文件 | 修改内容 |
|------|---------|
| `web/src/router/index.js` | 添加 `/project` + `/project/:project_id` 路由 |
| `web/src/layouts/AppLayout.vue` | 侧边栏新增"访谈调研"(Mic 图标) |

## 新增依赖

- @vue-flow/core
- @vue-flow/background
- @vue-flow/controls

## 关键设计决策

1. **完全复用现有 UI 规范** - Ant Design Vue 4.x + lucide-vue-next + CSS 变量 + Less
2. **项目列表参考 DataBaseView 卡片布局** - 保持视觉一致性
3. **流程编辑器使用 Vue Flow** - 自定义 interview 节点类型，支持拖拽/连线/编辑
4. **API 使用 apiAdminGet/Post/Put/Delete** - 遵循现有权限模式
5. **Vue Flow CSS 注意点** - @vue-flow/background 无 style.css 导出，不能导入

## 待完成

- Task 7: InterviewFlowAgent（可延后）
- 浏览器实际登录测试（需确认当前密码）
