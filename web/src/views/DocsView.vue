<template>
  <div class="docs-page">
    <div class="glass-header">
      <div class="logo" @click="goHome">
        <img
          :src="infoStore.organization.logo"
          :alt="infoStore.organization.name"
          class="logo-img"
        />
        <span class="logo-text">{{ infoStore.organization.name }}</span>
      </div>
      <div class="header-actions">
        <UserInfoComponent :show-button="true" />
      </div>
    </div>

    <div class="docs-shell">
      <aside class="docs-sidebar">
        <div class="sidebar-title">文档中心</div>
        <button
          v-for="item in menuItems"
          :key="item.key"
          class="menu-item"
          :class="{ active: activeMenu === item.key }"
          @click="activeMenu = item.key"
        >
          {{ item.label }}
        </button>
      </aside>

      <main class="docs-main">
        <section class="docs-intro-card">
          <p class="eyebrow">Documentation Center</p>
          <h1 class="docs-title">{{ activeMenuMeta.label }}</h1>
          <p class="docs-description">{{ activeMenuMeta.description }}</p>
        </section>

        <section class="docs-content-card">
          <div v-if="activeMenu === 'intro'" class="markdown-wrapper">
            <MdPreview :modelValue="introMarkdown" :theme="theme" previewTheme="github" />
          </div>
          <div v-else class="update-placeholder">
            <FileText :size="20" />
            <div>
              <h3>新版改动</h3>
              <p>该栏目内容正在整理中，后续可在这里补充版本更新说明。</p>
            </div>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/preview.css'
import { FileText } from 'lucide-vue-next'
import { useInfoStore } from '@/stores/info'
import { useThemeStore } from '@/stores/theme'
import UserInfoComponent from '@/components/UserInfoComponent.vue'
import introMarkdown from '@/docs/main.md?raw'

const router = useRouter()
const infoStore = useInfoStore()
const themeStore = useThemeStore()

const activeMenu = ref('intro')
const menuItems = [
  {
    key: 'intro',
    label: '简介',
    description: '查看平台的系统定位、功能设计与核心流程。'
  },
  {
    key: 'changes',
    label: '新版改动',
    description: '聚合展示新版能力更新与版本说明。'
  }
]

const theme = computed(() => (themeStore.isDark ? 'dark' : 'light'))
const activeMenuMeta = computed(
  () => menuItems.find((item) => item.key === activeMenu.value) || menuItems[0]
)

const goHome = () => {
  router.push('/')
}
</script>

<style scoped lang="less">
.docs-page {
  min-height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(96, 165, 250, 0.18), transparent 30%),
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.12), transparent 26%),
    linear-gradient(180deg, #f7faff 0%, #eef4ff 100%);
  padding: 24px;
  box-sizing: border-box;
}

.glass-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 20px;
  margin-bottom: 24px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(18px);
  box-shadow: 0 12px 40px rgba(15, 23, 42, 0.08);
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.logo-img {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  object-fit: cover;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: var(--gray-900, #111827);
}

.docs-shell {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 24px;
  min-height: calc(100vh - 128px);
}

.docs-sidebar {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 22px 18px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(255, 255, 255, 0.76);
  backdrop-filter: blur(18px);
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.08);
  align-self: start;
  position: sticky;
  top: 24px;
}

.sidebar-title {
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--gray-500, #6b7280);
}

.menu-item {
  border: none;
  border-radius: 16px;
  padding: 14px 16px;
  text-align: left;
  font-size: 15px;
  font-weight: 500;
  color: var(--gray-700, #374151);
  background: transparent;
  transition: all 0.2s ease;
  cursor: pointer;
}

.menu-item:hover {
  background: rgba(59, 130, 246, 0.08);
  color: var(--color-primary, #2563eb);
}

.menu-item.active {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.16), rgba(96, 165, 250, 0.22));
  color: var(--color-primary, #2563eb);
}

.docs-main {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-width: 0;
}

.docs-intro-card,
.docs-content-card {
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(255, 255, 255, 0.76);
  backdrop-filter: blur(18px);
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.08);
}

.docs-intro-card {
  padding: 28px 32px;
}

.eyebrow {
  margin: 0 0 10px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-primary, #2563eb);
}

.docs-title {
  margin: 0;
  font-size: 32px;
  line-height: 1.2;
  color: var(--gray-900, #111827);
}

.docs-description {
  margin: 12px 0 0;
  font-size: 15px;
  line-height: 1.8;
  color: var(--gray-600, #4b5563);
}

.docs-content-card {
  padding: 12px;
  min-height: 0;
}

.markdown-wrapper {
  border-radius: 22px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.96);
}

.markdown-wrapper :deep(.md-editor) {
  background: transparent;
}

.markdown-wrapper :deep(.md-editor-preview-wrapper) {
  padding: 28px 32px;
}

.update-placeholder {
  min-height: 360px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  border-radius: 22px;
  background: rgba(59, 130, 246, 0.05);
  color: var(--gray-700, #374151);
  text-align: left;
}

.update-placeholder h3 {
  margin: 0 0 8px;
  font-size: 20px;
  color: var(--gray-900, #111827);
}

.update-placeholder p {
  margin: 0;
  line-height: 1.7;
}

@media (max-width: 960px) {
  .docs-page {
    padding: 16px;
  }

  .docs-shell {
    grid-template-columns: 1fr;
  }

  .docs-sidebar {
    position: static;
    flex-direction: row;
    flex-wrap: wrap;
  }

  .sidebar-title {
    width: 100%;
  }

  .docs-intro-card {
    padding: 24px;
  }

  .markdown-wrapper :deep(.md-editor-preview-wrapper) {
    padding: 20px;
  }
}
</style>
