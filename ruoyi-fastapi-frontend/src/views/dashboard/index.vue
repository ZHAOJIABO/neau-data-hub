<template>
  <div class="dashboard-container">
    <div class="welcome-card">
      <h1 class="title">农业数据管理平台</h1>
      <p class="subtitle">东北农业大学农业数据综合管理系统</p>
    </div>
  </div>
</template>

<script setup>
defineOptions({
  name: "DashBoard",
});
</script>

<style scoped>
.dashboard-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 120px);
  padding: 24px;
}

.welcome-card {
  text-align: center;
}

.title {
  font-size: 36px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 16px;
}

.subtitle {
  font-size: 16px;
  color: var(--el-text-color-secondary);
}
</style>
