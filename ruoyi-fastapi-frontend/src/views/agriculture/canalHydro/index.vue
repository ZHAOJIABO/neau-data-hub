<template>
  <div class="app-container agri-page canal-hydro-page">
    <!-- ============ Hero ============ -->
    <section class="agri-page__hero canal-hydro-hero">
      <div class="hero-decor" aria-hidden="true">
        <span class="hero-decor__wave hero-decor__wave--1" />
        <span class="hero-decor__wave hero-decor__wave--2" />
        <span class="hero-decor__wave hero-decor__wave--3" />
      </div>
      <div class="hero-content">
        <span class="agri-page__eyebrow canal-hydro-eyebrow">MINUTE-BY-MINUTE HYDRODYNAMICS</span>
        <h1 class="agri-page__title">全渠系逐分钟水动力学仿真</h1>
        <p class="agri-page__desc">
          前端传入完整渠系数据并显式给出每条渠段的上游入流时序，后端按渠系拓扑逐条做
          MacCormack 显式 1D 圣维南仿真，通过节点连续校验实现干-支-斗-农的逐分钟接力，
          最终返回全渠系 (t, x, Q, h, V) 的时空结果，ECharts 动态展示。
        </p>
        <div class="agri-page__siblings">
          <router-link to="/model/irrigation" class="sibling-link">
            <el-icon><Promotion /></el-icon>
            <span>灌溉决策</span>
          </router-link>
          <router-link to="/model/canal/optimize" class="sibling-link">
            <el-icon><Promotion /></el-icon>
            <span>渠系配水优化</span>
          </router-link>
          <router-link to="/model/canal" class="sibling-link">
            <el-icon><Promotion /></el-icon>
            <span>渠系管理</span>
          </router-link>
        </div>
      </div>
      <div class="agri-page__tags">
        <span class="tag tag--cyan">MacCormack</span>
        <span class="tag tag--teal">节点连续耦合</span>
        <span class="tag tag--indigo">dt 30s</span>
        <span class="tag tag--violet">≤ 12 h</span>
      </div>
    </section>

    <el-row :gutter="20" class="page-layout">
      <!-- ============ 左侧：参数配置 ============ -->
      <el-col :xs="24" :lg="8" class="config-col">
        <el-card shadow="hover" class="config-card glass-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">仿真参数</div>
                <div class="card-desc">节点连续耦合 · 逐分钟接力</div>
              </div>
              <el-tag :type="resultError ? 'danger' : result ? 'success' : 'info'" effect="dark" round>
                {{ resultError ? '接口异常' : result ? '仿真完成' : '待提交' }}
              </el-tag>
            </div>
          </template>

          <div class="config-body">
            <el-alert
              type="info"
              :closable="false"
              show-icon
              title="每条渠段必须给入流时序 inflow_series，未给则按恒定设计流量入流。"
              class="mb16"
            />

            <el-form ref="formRef" :model="form" label-position="top" size="small" class="hydro-form">
              <el-form-item label="干渠编号">
                <el-input v-model="form.mainCanalId" placeholder="默认 1" clearable />
              </el-form-item>

              <el-row :gutter="12">
                <el-col :span="12">
                  <el-form-item label="仿真时长 (h)">
                    <el-input-number v-model="form.simDurationMin" :min="1" :max="24" :step="1" style="width: 100%" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="时间步 dt (s)">
                    <el-select v-model="form.dtSec" style="width: 100%">
                      <el-option :value="30" label="30s" />
                      <el-option :value="60" label="60s" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="12">
                <el-col :span="12">
                  <el-form-item label="流量下限比 (Q_min / Q_design) · 不淤下限">
                    <el-input-number
                      v-model="form.designFlowRatioMin"
                      :min="0.1"
                      :max="1.0"
                      :step="0.05"
                      :precision="2"
                      style="width: 100%"
                    />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="说明">
                    <div class="form-hint">
                      v_scour：Q &gt; Q_design<br />
                      v_silt：Q &lt; {{ form.designFlowRatioMin }} × Q_design
                    </div>
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="12">
                <el-col :span="12">
                  <el-form-item label="水深安全余量 h_safety (m) · h_max = 设计水深 + 余量">
                    <el-input-number
                      v-model="form.hSafetyMarginM"
                      :min="0.05"
                      :max="1.0"
                      :step="0.05"
                      :precision="2"
                      style="width: 100%"
                    />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="说明">
                    <div class="form-hint">
                      h_over：h &gt; h_max（设计水深 + {{ form.hSafetyMarginM }} m）
                    </div>
                  </el-form-item>
                </el-col>
              </el-row>

              <el-form-item label="末级下游水位模式">
                <el-select v-model="form.downstreamHMode" style="width: 100%">
                  <el-option value="normal" label="正常水深 (Manning)" />
                  <el-option value="design" label="设计水深" />
                  <el-option value="fixed" label="固定下游水位" />
                </el-select>
              </el-form-item>

              <el-form-item v-if="form.downstreamHMode === 'fixed'" label="固定下游水位 (m)">
                <el-input-number v-model="form.fixedDownstreamH" :min="0" :max="10" :step="0.05" style="width: 100%" />
              </el-form-item>

              <div class="divider-soft" />

              <el-form-item label="渠段数据来源">
                <el-radio-group v-model="form.source" class="source-switch">
                  <el-radio-button value="db">数据库</el-radio-button>
                  <el-radio-button value="manual">本页编辑</el-radio-button>
                </el-radio-group>
              </el-form-item>

              <div v-if="form.source === 'db'" class="mb12 db-row">
                <el-button size="small" type="primary" plain @click="loadFromDb" :loading="loadingDb">
                  从渠系管理加载
                </el-button>
                <el-button
                  size="small"
                  type="success"
                  plain
                  :disabled="!hasOptimizeResult"
                  :title="hasOptimizeResult ? '' : '请先在渠系配水优化页运行一次优化'"
                  @click="openImportDialog = true"
                >
                  <el-icon><Download /></el-icon>
                  <span>从优化结果导入</span>
                </el-button>
                <span class="muted-text">已加载 {{ dbCanals.length }} 条渠段</span>
              </div>

              <el-button
                type="primary"
                :loading="running"
                :disabled="!canSubmit"
                class="run-btn"
                @click="onSubmit"
              >
                <el-icon v-if="!running"><VideoPlay /></el-icon>
                <span>{{ running ? '仿真进行中…' : '运行全渠系仿真' }}</span>
              </el-button>

              <el-alert
                v-if="resultError"
                type="error"
                :title="resultError"
                :closable="false"
                show-icon
                class="mt12"
              />
            </el-form>
          </div>
        </el-card>

        <el-card v-if="form.source === 'manual'" shadow="hover" class="config-card mt16 glass-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">渠段编辑（手动模式）</div>
                <div class="card-desc">至少 1 干 + 1 支 + 1 斗，每条必填 inflow_series</div>
              </div>
              <el-button size="small" type="primary" plain @click="addCanalRow">新增渠段</el-button>
            </div>
          </template>
          <div class="canal-edit-list">
            <el-collapse v-model="openCids">
              <el-collapse-item
                v-for="row in form.canals"
                :key="row.canal_id"
                :name="row.canal_id"
                :title="`${row.canal_id} · L=${row.length}m · Q=${row.design_flow} m³/s`"
              >
                <el-row :gutter="10">
                  <el-col :span="12">
                    <el-form-item label="渠段编号" label-position="top">
                      <el-input v-model="row.canal_id" size="small" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="父渠段" label-position="top">
                      <el-input v-model="row.parent_id" size="small" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="长度 m" label-position="top">
                      <el-input-number v-model="row.length" :min="0" :step="100" size="small" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="设计 Q m³/s" label-position="top">
                      <el-input-number v-model="row.design_flow" :min="0" :step="0.1" size="small" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="设计水深 m" label-position="top">
                      <el-input-number v-model="row.design_depth" :min="0" :step="0.1" size="small" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="渠底宽 m" label-position="top">
                      <el-input-number v-model="row.bottom_width" :min="0" :step="0.1" size="small" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="边坡 m" label-position="top">
                      <el-input-number v-model="row.side_slope" :min="0" :step="0.1" size="small" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="糙率" label-position="top">
                      <el-input-number v-model="row.roughness" :min="0" :step="0.001" size="small" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="纵坡" label-position="top">
                      <el-input-number v-model="row.slope" :min="0" :step="0.0001" size="small" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="入流 Q (m³/s)" label-position="top">
                      <el-input-number v-model="row._q" :min="0" :step="0.1" size="small" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8" class="remove-cell">
                    <el-button type="danger" size="small" plain @click="removeCanalRow(row.canal_id)">删除</el-button>
                  </el-col>
                </el-row>
              </el-collapse-item>
            </el-collapse>
          </div>
        </el-card>
      </el-col>

      <!-- ============ 右侧：结果展示 ============ -->
      <el-col :xs="24" :lg="16" class="result-col">
        <el-card v-if="result" shadow="hover" class="result-card glass-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">KPI · 仿真总览</div>
                <div class="card-desc">
                  {{ result.summary.n_canals }} 段渠系 · {{ formatHours(result.summary.sim_duration_min) }} · dt {{ result.summary.dt_sec }}s · 模式 {{ result.summary.downstream_h_mode }}
                </div>
              </div>
              <div class="header-actions">
                <el-tag :type="kpiConvergedType" effect="dark" round>{{ kpiConvergedText }}</el-tag>
                <el-tag :type="kpiContinuityType" effect="dark" round>节点连续违例 {{ result.summary.node_continuity_violations }}</el-tag>
                <el-tag :type="kpiViolationsType" effect="dark" round>违例 {{ result.summary.total_violations }}</el-tag>
              </div>
            </div>
          </template>
          <el-row :gutter="12">
            <el-col :xs="12" :sm="6" v-for="(kpi, idx) in kpiList" :key="kpi.label">
              <div class="kpi-box" :class="`kpi-box--${idx}`">
                <div class="kpi-label">{{ kpi.label }}</div>
                <div class="kpi-value">{{ kpi.value }}</div>
                <div class="kpi-hint">{{ kpi.hint }}</div>
              </div>
            </el-col>
          </el-row>
          <div v-if="violationBreakdown" class="vio-breakdown">
            <div class="vio-breakdown__head">
              <span class="vio-breakdown__title">违例分布诊断</span>
              <span class="vio-breakdown__hint">
                {{ violationBreakdown.time_bucket_min }} 分钟分桶 · 仅用于查看分布，不影响物理求解
              </span>
            </div>
            <div class="vio-breakdown__types">
              <div
                v-for="t in typeRows"
                :key="t.type"
                class="vio-chip"
                :class="`vio-chip--${t.tone}`"
                :title="t.title"
              >
                <span class="vio-chip__name">{{ t.type }}</span>
                <span class="vio-chip__count">{{ t.count.toLocaleString() }}</span>
                <span class="vio-chip__pct">{{ t.pct.toFixed(1) }}%</span>
              </div>
            </div>
            <div v-if="canalRows.length" class="vio-breakdown__section">
              <div class="vio-breakdown__sub">渠段 Top-5（合计占总违例）</div>
              <div class="vio-bar-list">
                <div v-for="row in canalRows" :key="row.canal_id" class="vio-bar">
                  <span class="vio-bar__name">{{ row.canal_id }}</span>
                  <span class="vio-bar__track">
                    <span class="vio-bar__fill" :style="{ width: row.pct + '%' }" />
                  </span>
                  <span class="vio-bar__count">{{ row.count.toLocaleString() }}</span>
                </div>
              </div>
            </div>
            <div v-if="bucketRows.length" class="vio-breakdown__section">
              <div class="vio-breakdown__sub">
                时间分布（5 min 桶，Top-10 高峰期）
              </div>
              <div class="vio-bucket-list">
                <div v-for="b in bucketRows" :key="b.label" class="vio-bucket">
                  <span class="vio-bucket__label">{{ b.label }} min</span>
                  <span class="vio-bar__track">
                    <span class="vio-bar__fill" :style="{ width: b.pct + '%' }" />
                  </span>
                  <span class="vio-bar__count">{{ b.count.toLocaleString() }}</span>
                </div>
              </div>
            </div>
          </div>
        </el-card>

        <el-card v-if="result" shadow="hover" class="result-card mt16 glass-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">渠系拓扑（节点连续）</div>
                <div class="card-desc">悬停查看父 → 子边（线宽 ∝ 渠长）</div>
              </div>
              <div class="legend-pills">
                <span class="legend-pill"><i class="dot dot--cyan" />干</span>
                <span class="legend-pill"><i class="dot dot--teal" />支</span>
                <span class="legend-pill"><i class="dot dot--amber" />斗</span>
                <span class="legend-pill"><i class="dot dot--rose" />农</span>
              </div>
            </div>
          </template>
          <div ref="topologyChartEl" class="chart-large chart-glass" />
        </el-card>

        <el-card v-if="result" shadow="hover" class="result-card mt16 glass-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">渠段 × 时间 热力图</div>
                <div class="card-desc">每行 = 1 条渠段 · 每列 = 1 个时间点 · 单元颜色 = 数值</div>
              </div>
              <el-radio-group v-model="heatMetric" size="small" class="metric-switch">
                <el-radio-button value="q_m3s">流量 Q</el-radio-button>
                <el-radio-button value="h_m">水深 h</el-radio-button>
                <el-radio-button value="v_mps">流速 v</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="heatChartEl" class="chart-large chart-glass" />
        </el-card>

        <el-card v-if="result" shadow="hover" class="result-card mt16 glass-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">代表断面时序子图</div>
                <div class="card-desc">每条渠段取首 / 中 / 末三个断面；可勾选要查看的渠段</div>
              </div>
              <!--
                故意不用 <el-select multiple>:el-select 内部 el-popper 用
                @floating-ui/dom 的 useFloating,在 result 同步赋值导致
                <el-option> 数量从 0 变成 N 时,会触发 popperElementRef →
                createPopper → instance.update() → Object.assign(states.value, ...)
                → 再次 trigger 组件 effect,与 result 触发的 componentUpdate
                在同一 tick 互相递归,导致 Maximum recursive updates exceeded。
                用 el-checkbox-group 渲染渠段勾选,完全绕开 popper 链。
              -->
              <div v-if="result?.canals?.length" class="canal-picker canal-picker-list">
                <el-checkbox-group v-model="selectedCanals" size="small" class="canal-checkbox-group">
                  <el-checkbox
                    v-for="c in result.canals"
                    :key="c.canal_id"
                    :value="c.canal_id"
                    :label="c.canal_id"
                    border
                    size="small"
                  >
                    {{ c.canal_id }} ({{ c.level || '-' }})
                  </el-checkbox>
                </el-checkbox-group>
              </div>
            </div>
          </template>
          <el-empty v-if="selectedCanals.length === 0" description="请从右上角选择要展示的渠段" />
          <el-row v-else :gutter="12">
            <el-col v-for="cid in selectedCanals" :key="cid" :xs="24" :md="12">
              <div :ref="(el) => setSeriesChartEl(el, cid)" class="chart-medium chart-glass" :data-cid="cid" />
            </el-col>
          </el-row>
        </el-card>

        <el-card v-if="result" shadow="hover" class="result-card mt16 glass-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">违例明细</div>
                <div class="card-desc">h_over · v_scour · v_silt · solver_fail · node_continuity</div>
              </div>
              <!--
                同样不用 <el-select>:见"代表断面时序子图"卡片头的注释。
                el-select 内部 el-popper 的 useFloating watcher 在 result
                同步赋值时,会与 result 触发的 componentUpdate 互相递归。
                这里 option 虽是静态,但 el-select 第一次 mount 时 popper 仍
                会同步 forceUpdate,改用 el-radio-group 完全绕开 popper 链。
              -->
              <el-radio-group v-model="violationFilter" size="small" class="filter-radio-group">
                <el-radio-button value="" label="">全部</el-radio-button>
                <el-radio-button value="h_over" label="h_over" />
                <el-radio-button value="v_scour" label="v_scour" />
                <el-radio-button value="v_silt" label="v_silt" />
                <el-radio-button value="solver_fail" label="solver_fail" />
                <el-radio-button value="node_continuity" label="node_continuity" />
              </el-radio-group>
            </div>
          </template>
          <!--
            故意不用 <el-table>:el-table 内部的 useStyle3 会在 :data 替换时同步
            触发 setData → setOptions 链,与 result 触发的依赖链在同一 tick
            互相递归,导致 Maximum recursive updates exceeded。
            用 div 列表渲染,绑定一个由我们显式控制的 ref,完全绕开 el-table。
          -->
          <div v-if="filteredViolations.length === 0" class="violation-empty">无违例</div>
          <div v-else class="violation-scroll">
            <div class="violation-head">
              <span class="col col-time">时间 (min)</span>
              <span class="col col-canal">渠段</span>
              <span class="col col-x">x (m)</span>
              <span class="col col-type">类型</span>
              <span class="col col-detail">详情</span>
            </div>
            <div
              v-for="(row, i) in filteredViolations"
              :key="`${row.time_min ?? ''}-${row.canal_id ?? ''}-${row.x_m ?? ''}-${row.type ?? ''}-${i}`"
              class="violation-row"
            >
              <span class="col col-time">{{ row.time_min ?? '-' }}</span>
              <span class="col col-canal">{{ row.canal_id ?? row.parent_id ?? '-' }}</span>
              <span class="col col-x">{{ row.x_m ?? '—' }}</span>
              <span class="col col-type">
                <el-tag :type="violationTagType(row.type)" effect="light" size="small" round>
                  {{ row.type }}
                </el-tag>
              </span>
              <span class="col col-detail">{{ row.detail }}</span>
            </div>
          </div>
        </el-card>

        <el-empty v-if="!result && !resultError && !running" description="提交左侧表单后开始全渠系水动力学仿真">
          <template #image>
            <el-icon class="empty-icon"><Aim /></el-icon>
          </template>
        </el-empty>

        <!-- ============ 从优化结果导入 对话框 ============ -->
        <el-dialog
          v-model="openImportDialog"
          title="从渠系配水优化结果导入"
          width="640px"
          :close-on-click-modal="false"
        >
          <div v-if="!optimizeSnapshot" class="import-empty">
            <el-alert
              type="warning"
              :closable="false"
              show-icon
              title="未发现可用的优化结果"
              description="请先在『渠系配水优化』页面运行一次优化，回到本页后即可在此导入。"
            />
          </div>
          <div v-else>
            <el-alert
              type="info"
              :closable="false"
              show-icon
              class="mb12"
              :title="`最近一次优化：${optimizeSnapshot.savedAtLabel} · 干渠 ${optimizeSnapshot.main_canal_id}`"
            />
            <el-table :data="optimizeSnapshot.previewRows" size="small" border stripe>
              <el-table-column prop="name" label="渠段" min-width="120" />
              <el-table-column prop="q" label="q (m³/s)" width="100" />
              <el-table-column prop="t_start_min" label="开始 (min)" width="110" />
              <el-table-column prop="t_end_min" label="结束 (min)" width="110" />
              <el-table-column prop="duration_min" label="持续 (min)" width="100" />
            </el-table>
            <div class="import-options mt12">
              <el-form label-position="top" size="small">
                <el-form-item label="导入方式">
                  <el-radio-group v-model="importMode">
                    <el-radio-button value="replace">替换 (使用优化流量)</el-radio-button>
                    <el-radio-button value="merge">叠加 (与已有入流合并)</el-radio-button>
                  </el-radio-group>
                </el-form-item>
                <el-form-item v-if="importMode === 'replace'" label="入流时序形态">
                  <el-radio-group v-model="inflowShape">
                    <el-radio-button value="rect">矩形 (阶跃)</el-radio-button>
                    <el-radio-button value="ramp">梯形 (5 min 渐变)</el-radio-button>
                  </el-radio-group>
                </el-form-item>
              </el-form>
            </div>
          </div>
          <template #footer>
            <el-button @click="openImportDialog = false">取消</el-button>
            <el-button
              type="primary"
              :disabled="!optimizeSnapshot"
              @click="applyOptimizeImport"
            >
              导入并填入入流时序
            </el-button>
          </template>
        </el-dialog>

        <div v-if="running" class="running-overlay glass-card">
          <div class="running-content">
            <div class="running-spinner" />
            <div class="running-title">全渠系水动力学仿真中</div>
            <div class="running-desc">MacCormack 显式 · 节点连续接力 · 请稍候</div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { GraphChart, HeatmapChart, LineChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { ElMessage } from 'element-plus'
import { Aim, Download, Promotion, VideoPlay } from '@element-plus/icons-vue'
import { listCanal as fetchCanals } from '@/api/agriculture/canal'
import { runFullHydro } from '@/api/agriculture/canal'

echarts.use([
  GraphChart,
  HeatmapChart,
  LineChart,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
  CanvasRenderer
])

const DEFAULT_API_KEY = 'irrigation_live_20260605_f2K9mQ7xLp4N8vRb6TzY'

const DEFAULT_INFLOW = (q) => [{ time_min: 0, q_m3s: q }, { time_min: 720, q_m3s: q }]

function formatHours(totalMin) {
  const m = Number(totalMin) || 0
  const h = m / 60
  return Number.isInteger(h) ? `${h} h` : `${h.toFixed(2)} h`
}

function makeBlankCanal(cid, parentId, designFlow, length) {
  return {
    canal_id: cid,
    parent_id: parentId,
    level: '',
    length,
    design_flow: designFlow,
    design_depth: 0.0,
    top_width: 0.0,
    bottom_width: 0.0,
    slope: 0.0,
    side_slope: 1.5,
    roughness: 0.015,
    water_demand: 0.0,
    _q: designFlow,
    inflow_series: DEFAULT_INFLOW(designFlow)
  }
}

const formRef = ref(null)
const form = reactive({
  apiKey: DEFAULT_API_KEY,
  mainCanalId: '1',
  simDurationMin: 24,
  dtSec: 30,
  vMax: 1.5,            // 保留字段已废弃（仍兼容旧 API）；新逻辑用 designFlowRatioMin
  vMin: 0.3,             // 同上
  designFlowRatioMin: 0.6,
  hSafetyMarginM: 0.3,
  downstreamHMode: 'normal',
  fixedDownstreamH: 0.5,
  source: 'db',
  canals: [
    makeBlankCanal('1', null, 4.0, 1500),
    makeBlankCanal('1-1', '1', 2.0, 800),
    makeBlankCanal('1-1-1', '1-1', 1.0, 400)
  ]
})

const openCids = ref(['1', '1-1', '1-1-1'])
const dbCanals = ref([])
const loadingDb = ref(false)
const running = ref(false)
const result = ref(null)
const resultError = ref('')
const heatMetric = ref('q_m3s')
const violationFilter = ref('')
const selectedCanals = ref([])

// ============ 从优化结果导入：状态与转换逻辑 ============
const openImportDialog = ref(false)
const importMode = ref('replace')  // 'replace' | 'merge'
const inflowShape = ref('ramp')     // 'rect' | 'ramp'
const optimizeSnapshot = ref(null)

function readOptimizeSnapshot() {
  try {
    const raw = sessionStorage.getItem('canal_optimize_result')
    if (!raw) return null
    const snap = JSON.parse(raw)
    if (!snap || (!snap.branches?.length && !snap.laterals?.length)) return null
    const previewRows = []
    for (const b of snap.branches || []) {
      const tStartH = Number(b.t_start_h || 0)
      const durH = Number(b.duration_h || 0)
      previewRows.push({
        name: `支渠 ${b.name}`,
        q: Number(b.q_actual || 0).toFixed(3),
        t_start_min: (tStartH * 60).toFixed(0),
        t_end_min: ((tStartH + durH) * 60).toFixed(0),
        duration_min: (durH * 60).toFixed(0)
      })
    }
    for (const l of snap.laterals || []) {
      const tStartH = Number(l.start_h ?? l.t_start_h ?? 0)
      const durH = Number(l.duration_h || 0)
      previewRows.push({
        name: `斗渠 ${l.name} (G${l.group})`,
        q: Number(l.Q_actual || 0).toFixed(3),
        t_start_min: (tStartH * 60).toFixed(0),
        t_end_min: ((tStartH + durH) * 60).toFixed(0),
        duration_min: (durH * 60).toFixed(0)
      })
    }
    const savedAt = snap.savedAt ? new Date(snap.savedAt) : null
    return {
      ...snap,
      previewRows,
      savedAtLabel: savedAt
        ? `${savedAt.getFullYear()}-${String(savedAt.getMonth() + 1).padStart(2, '0')}-${String(savedAt.getDate()).padStart(2, '0')} ${String(savedAt.getHours()).padStart(2, '0')}:${String(savedAt.getMinutes()).padStart(2, '0')}`
        : '未知时间'
    }
  } catch (_) {
    return null
  }
}

const hasOptimizeResult = computed(() => readOptimizeSnapshot() !== null)

watch(openImportDialog, (open) => {
  if (open) optimizeSnapshot.value = readOptimizeSnapshot()
})

function buildInflowSeriesFromOptim(tStartH, durationH, q, totalMin, shape) {
  // 输出 [time_min, q_m3s] 序列，覆盖 [0, totalMin]
  const t0 = tStartH * 60
  const t1 = (tStartH + durationH) * 60
  const ramp = 5  // 5 min 渐变，与后端 FullHydroContext.DEFAULT_RAMP_MIN 对齐
  const series = []
  if (shape === 'rect') {
    // 0..t0: 0, t0: 跳到 q, t1: 跳回 0, totalMin: 0
    series.push({ time_min: 0, q_m3s: 0 })
    if (t0 > 0) series.push({ time_min: t0, q_m3s: q })
    if (t1 < totalMin) series.push({ time_min: t1, q_m3s: 0 })
    series.push({ time_min: totalMin, q_m3s: 0 })
  } else {
    // 梯形渐变: [t0-ramp, t0] 由 0 渐变到 q；[t1, t1+ramp] 由 q 渐变回 0
    const rStart = Math.max(0, t0 - ramp)
    series.push({ time_min: 0, q_m3s: 0 })
    if (rStart > 0) series.push({ time_min: rStart, q_m3s: 0 })
    series.push({ time_min: t0, q_m3s: q })
    series.push({ time_min: t1, q_m3s: q })
    if (t1 + ramp < totalMin) series.push({ time_min: t1 + ramp, q_m3s: 0 })
    series.push({ time_min: totalMin, q_m3s: 0 })
  }
  // 去重 + 排序 + 确保至少 2 点
  const seen = new Set()
  const uniq = []
  for (const p of series) {
    if (seen.has(p.time_min)) continue
    seen.add(p.time_min)
    uniq.push(p)
  }
  uniq.sort((a, b) => a.time_min - b.time_min)
  if (uniq.length < 2) uniq.push({ time_min: totalMin, q_m3s: 0 })
  return uniq
}

function mergeInflowSeries(base, addition) {
  // 简单合并：把 addition 的非零段叠加到 base 上
  // 这里保持 base 为主，addition 在 [t0, t1] 区间内把 q 提升到 max(base, addition)
  // 实现：把所有时间点合并排序，对每个 (t, q) 段取最大
  const pts = []
  for (const p of base || []) pts.push({ time_min: p.time_min, q_m3s: p.q_m3s })
  for (const p of addition) pts.push({ time_min: p.time_min, q_m3s: p.q_m3s })
  pts.sort((a, b) => a.time_min - b.time_min)
  // 在时间点序列中：q(t) = max of all prior values, but we want piecewise
  // 简化策略：取每个时间点的 max
  const merged = []
  for (let i = 0; i < pts.length; i++) {
    if (merged.length === 0 || merged[merged.length - 1].time_min !== pts[i].time_min) {
      merged.push(pts[i])
    } else {
      merged[merged.length - 1].q_m3s = Math.max(merged[merged.length - 1].q_m3s, pts[i].q_m3s)
    }
  }
  return merged
}

function applyOptimizeImport() {
  if (!optimizeSnapshot.value) {
    ElMessage.warning('没有可用的优化结果')
    return
  }
  if (!dbCanals.value.length) {
    ElMessage.warning('请先点击"从渠系管理加载"获取渠段基础数据')
    return
  }
  const totalMin = form.simDurationMin * 60
  const shape = inflowShape.value
  const mode = importMode.value
  // 干渠入流时序：使用优化结果的 time_series（如有），否则用 design_flow 恒定
  const mainId = String(optimizeSnapshot.value.main_canal_id || '').trim()
  const ts = optimizeSnapshot.value.time_series || []
  let mainInflow = null
  if (mainId) {
    const mainRecord = dbCanals.value.find(c =>
      String(c.canal_id ?? c.canalId) === mainId
    )
    if (mainRecord) {
      if (ts.length) {
        mainInflow = ts.map(p => ({
          time_min: Number(p.t_h || 0) * 60,
          q_m3s: Number(p.Q_m3s || 0)
        }))
        // 收尾
        if (mainInflow[mainInflow.length - 1].time_min < totalMin) {
          mainInflow.push({ time_min: totalMin, q_m3s: mainInflow[mainInflow.length - 1].q_m3s })
        }
      } else {
        mainInflow = DEFAULT_INFLOW(Number(mainRecord.design_flow || 0))
      }
    }
  }
  let updated = 0
  let matched = 0
  // 支渠：按 canal_id 匹配
  for (const b of optimizeSnapshot.value.branches || []) {
    const cid = String(b.name || '').trim()
    const rec = dbCanals.value.find(c => String(c.canal_id ?? c.canalId) === cid)
    if (!rec) continue
    matched++
    const tStartH = Number(b.t_start_h || 0)
    const durH = Number(b.duration_h || 0)
    const q = Number(b.q_actual || 0)
    const newSeries = buildInflowSeriesFromOptim(tStartH, durH, q, totalMin, shape)
    rec.inflow_series = mode === 'merge' ? mergeInflowSeries(rec.inflow_series, newSeries) : newSeries
    rec._q = q
    updated++
  }
  // 斗渠：按 name 匹配
  for (const l of optimizeSnapshot.value.laterals || []) {
    const cid = String(l.name || '').trim()
    const rec = dbCanals.value.find(c => String(c.canal_id ?? c.canalId) === cid)
    if (!rec) continue
    matched++
    const tStartH = Number(l.start_h ?? l.t_start_h ?? 0)
    const durH = Number(l.duration_h || 0)
    const q = Number(l.Q_actual || 0)
    const newSeries = buildInflowSeriesFromOptim(tStartH, durH, q, totalMin, shape)
    rec.inflow_series = mode === 'merge' ? mergeInflowSeries(rec.inflow_series, newSeries) : newSeries
    rec._q = q
    updated++
  }
  // 干渠：使用 main_canal 时序
  if (mainId && mainInflow) {
    const rec = dbCanals.value.find(c => String(c.canal_id ?? c.canalId) === mainId)
    if (rec) {
      rec.inflow_series = mode === 'merge' ? mergeInflowSeries(rec.inflow_series, mainInflow) : mainInflow
      updated++
    }
  }
  // 触发响应式更新
  dbCanals.value = dbCanals.value.slice()
  ElMessage.success(`已导入：${matched} 条渠段匹配，更新 ${updated} 条入流时序`)
  openImportDialog.value = false
}

const topologyChartEl = ref(null)
const heatChartEl = ref(null)
let topologyChart = null
let heatChart = null
const seriesCharts = new Map()
const seriesElByCid = new Map()
const seriesElVersion = ref(0)
let seriesRenderRaf = 0

function setSeriesChartEl(el, cid) {
  if (el) {
    const isNew = !seriesElByCid.has(cid)
    seriesElByCid.set(cid, el)
    // Only bump version when registering a brand-new element, so the watcher
    // can re-render after a user toggles canals.  On the initial mount of
    // N chart containers (all of which return truthy el on the same tick),
    // only the FIRST call per cid increments — subsequent calls for the same
    // cid in the same tick are no-ops, breaking the el → version++ →
    // watcher → render → more els → version++ recursion that causes
    // "Maximum recursive updates exceeded".
    if (isNew) seriesElVersion.value++
  } else {
    seriesElByCid.delete(cid)
  }
}

const canSubmit = computed(() => {
  if (form.source === 'db' && dbCanals.value.length === 0) return false
  if (form.source === 'manual' && form.canals.length === 0) return false
  return true
})

const kpiConvergedText = computed(() => {
  if (!result.value) return ''
  const s = result.value.summary
  return `${s.n_converged}/${s.n_canals} 收敛 (${(s.converged_ratio * 100).toFixed(0)}%)`
})
const kpiConvergedType = computed(() => {
  if (!result.value) return 'info'
  return result.value.summary.converged_ratio >= 0.95 ? 'success' : 'warning'
})
const kpiViolationsType = computed(() => {
  if (!result.value) return 'info'
  const v = result.value.summary.total_violations
  if (v === 0) return 'success'
  if (v < 20) return 'warning'
  return 'danger'
})
const kpiContinuityType = computed(() => {
  if (!result.value) return 'info'
  const v = result.value.summary.node_continuity_violations
  if (v === 0) return 'success'
  return 'warning'
})

const kpiList = computed(() => {
  if (!result.value) return []
  const s = result.value.summary
  return [
    { label: '渠段数', value: s.n_canals, hint: 'BFS 仿真节点' },
    { label: '仿真时长', value: formatHours(s.sim_duration_min), hint: `dt = ${s.dt_sec} s` },
    { label: '下游模式', value: s.downstream_h_mode, hint: '末级渠段边界' },
    { label: '总违例', value: s.total_violations, hint: '水深 / 流速 / 节点连续' }
  ]
})

const filteredViolations = computed(() => {
  if (!result.value) return []
  if (!violationFilter.value) return result.value.violations.slice(0, 200)
  return result.value.violations.filter((v) => v.type === violationFilter.value).slice(0, 200)
})

const violationBreakdown = computed(() => {
  const summary = result.value?.summary
  if (!summary) return null
  return summary.violation_breakdown || null
})

const TYPE_TONE = {
  h_over: 'danger',
  v_scour: 'warning',
  v_silt: 'warning',
  solver_fail: 'danger',
  node_continuity: 'info'
}

const typeRows = computed(() => {
  const b = violationBreakdown.value
  if (!b) return []
  const byType = b.by_type || {}
  const total = Object.values(byType).reduce((a, n) => a + n, 0)
  if (total === 0) return []
  const order = ['h_over', 'v_scour', 'v_silt', 'solver_fail', 'node_continuity']
  const known = order.filter((t) => byType[t] != null)
  const extras = Object.keys(byType).filter((t) => !order.includes(t))
  return [...known, ...extras].map((t) => ({
    type: t,
    count: byType[t] || 0,
    pct: (byType[t] / total) * 100,
    tone: TYPE_TONE[t] || 'info',
    title: t === 'h_over'
      ? `水深超过设计水深 + ${(form.hSafetyMarginM ?? 0.3).toFixed(2)} m`
      : t === 'v_scour' ? '流量超过渠道设计流量 (Q > Q_design)'
      : t === 'v_silt' ? `流量低于 ${(form.designFlowRatioMin ?? 0.6).toFixed(2)} × Q_design`
      : t === 'solver_fail' ? 'CFL 5 次重试后仍不满足'
      : t === 'node_continuity' ? '父→子节点流量不连续（>5%）'
      : '其他类型'
  }))
})

const canalRows = computed(() => {
  const b = violationBreakdown.value
  if (!b) return []
  const list = b.top_canals || []
  const max = list.reduce((m, r) => Math.max(m, r.count), 0)
  return list.map((r) => ({
    canal_id: r.canal_id,
    count: r.count,
    pct: max > 0 ? (r.count / max) * 100 : 0
  }))
})

const bucketRows = computed(() => {
  const b = violationBreakdown.value
  if (!b) return []
  const buckets = b.time_buckets || {}
  const entries = Object.entries(buckets)
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10)
  const max = entries.reduce((m, e) => Math.max(m, e.count), 0)
  return entries.map((e) => ({
    label: e.label,
    count: e.count,
    pct: max > 0 ? (e.count / max) * 100 : 0
  }))
})

function violationTagType(type) {
  const map = {
    h_over: 'danger',
    v_scour: 'warning',
    v_silt: 'warning',
    solver_fail: 'danger',
    node_continuity: 'info'
  }
  return map[type] || 'info'
}

function addCanalRow() {
  const id = `manual-${form.canals.length + 1}`
  form.canals.push(makeBlankCanal(id, null, 1.0, 500))
  openCids.value.push(id)
}

function removeCanalRow(cid) {
  form.canals = form.canals.filter((c) => c.canal_id !== cid)
}

async function loadFromDb() {
  loadingDb.value = true
  try {
    const res = await fetchCanals({ pageNum: 1, pageSize: 200 })
    const rows = res?.rows || res?.data?.rows || []
    dbCanals.value = rows.map((r) => ({
      ...r,
      _q: Number(r.design_flow || 0),
      inflow_series: DEFAULT_INFLOW(Number(r.design_flow || 0))
    }))
    ElMessage.success(`已加载 ${dbCanals.value.length} 条渠段`)
  } catch (err) {
    ElMessage.error(`加载渠系数据失败：${err?.message || err}`)
  } finally {
    loadingDb.value = false
  }
}

function buildCanalsPayload() {
  const src = form.source === 'db' ? dbCanals.value : form.canals
  return src.map((c) => {
    // listCanal 返回驼峰(CanalBaseModel 用 to_camel),手动行表单是下划线
    const canalId = c.canal_id ?? c.canalId
    const parentId = c.parent_id ?? c.parentId
    const canalName = c.canal_name ?? c.canalName
    return {
      canal_id: canalId,
      canal_name: canalName || null,
      parent_id: parentId || null,
      level: c.level || null,
      length: Number(c.length || 0),
      design_flow: Number(c.design_flow ?? c.designFlow ?? 0),
      design_depth: Number(c.design_depth ?? c.designDepth ?? 0),
      top_width: Number(c.top_width ?? c.topWidth ?? 0),
      bottom_width: Number(c.bottom_width ?? c.bottomWidth ?? 0),
      slope: Number(c.slope || 0),
      side_slope: Number(c.side_slope ?? c.sideSlope ?? 1.5),
      roughness: Number(c.roughness || 0.015),
      inflow_series: c.inflow_series || DEFAULT_INFLOW(Number(c.design_flow ?? c.designFlow ?? 0))
    }
  })
}

function clearCharts() {
  topologyChart && topologyChart.dispose()
  heatChart && heatChart.dispose()
  for (const ch of seriesCharts.values()) ch.dispose()
  seriesCharts.clear()
  topologyChart = null
  heatChart = null
}

async function onSubmit() {
  running.value = true
  resultError.value = ''
  clearCharts()
  result.value = null
  selectedCanals.value = []
  try {
    const payload = {
      main_canal_id: form.mainCanalId || '1',
      canals: buildCanalsPayload(),
      sim_duration_min: form.simDurationMin * 60,
      dt_sec: form.dtSec,
      design_flow_ratio_min: form.designFlowRatioMin,
      h_safety_margin_m: form.hSafetyMarginM,
      downstream_h_mode: form.downstreamHMode,
      fixed_downstream_h: form.downstreamHMode === 'fixed' ? form.fixedDownstreamH : null
    }
    const data = await runFullHydro(payload, form.apiKey)
    result.value = data
    await nextTick()
    if (data?.canals?.length) {
      selectedCanals.value = data.canals.slice(0, Math.min(data.canals.length, 6)).map((c) => c.canal_id)
    }
    await nextTick()
    // 把 echarts 渲染推迟到下一个宏任务,与 Vue 的 patch / watcher 队列完全错开
    setTimeout(renderAllCharts, 0)
    ElMessage.success('全渠系仿真完成')
  } catch (err) {
    resultError.value = err?.response?.data?.msg || err?.message || String(err)
    result.value = null
    selectedCanals.value = []
  } finally {
    running.value = false
  }
}

function renderAllCharts() {
  if (!result.value) return
  // 每个 echarts 渲染之间用 setTimeout(0) 隔断,让 ECharts 内部
  // Promise.then(forceUpdate) 与 Vue 的同步调度器完全错开,
  // 避免 Maximum recursive updates exceeded
  setTimeout(renderTopology, 0)
  setTimeout(renderHeat, 0)
  setTimeout(renderSeries, 0)
}

watch(heatMetric, () => setTimeout(renderHeat, 0))
watch(selectedCanals, () => setTimeout(renderSeries, 0))

function levelColor(level) {
  const map = {
    '1': '#0EA5E9',
    main: '#0EA5E9',
    '2': '#14B8A6',
    branch: '#14B8A6',
    '3': '#F59E0B',
    lateral: '#F59E0B',
    '4': '#F43F5E',
    farm: '#F43F5E'
  }
  return map[level] || '#8B5CF6'
}

function renderTopology() {
  if (!topologyChartEl.value) return
  if (!topologyChart) {
    topologyChart = echarts.init(topologyChartEl.value)
  }

  const { roots, nodes, edges } = result.value.topology
  const root = (roots && roots[0]) || '1'

  // Build children index (backend uses 'from'/'to')
  const childrenOf = {}
  for (const e of edges) {
    if (!childrenOf[e.from]) childrenOf[e.from] = []
    childrenOf[e.from].push(e.to)
  }

  // --- Simple clean two-pass tree layout ---
  // rawX: left-to-right fractional position (integer = slot)
  // depthOf: depth level (root=0)
  const rawX = {}
  const depthOf = {}

  function subtreeWidth(nodeId) {
    const children = childrenOf[nodeId] || []
    if (children.length === 0) return 1
    return children.reduce((sum, c) => sum + subtreeWidth(c), 0)
  }

  // PASS 1: post-order — assign fractional x to each node (centered above children)
  function walkX(nodeId, depth) {
    depthOf[nodeId] = depth
    const children = childrenOf[nodeId] || []
    if (children.length === 0) {
      rawX[nodeId] = 0
      return
    }
    for (const child of children) walkX(child, depth + 1)
    rawX[nodeId] = (rawX[children[0]] + rawX[children[children.length - 1]]) / 2
  }
  walkX(root, 0)

  // PASS 2: pre-order — spread children so subtrees don't overlap
  const SLOT = 2  // minimum gap between subtree centers
  function spread(nodeId) {
    const children = childrenOf[nodeId] || []
    if (children.length < 2) {
      for (const c of children) spread(c)
      return
    }
    const widths = children.map(c => subtreeWidth(c))
    let left = rawX[children[0]]
    for (let i = 1; i < children.length; i++) {
      const right = rawX[children[i]]
      const needed = left + widths[i - 1] * SLOT + 1 - right
      if (needed > 0) {
        shiftSubtree(children[i], needed)
      }
      left = rawX[children[i]] + widths[i] * SLOT
    }
    for (const c of children) spread(c)
  }

  function shiftSubtree(nodeId, delta) {
    rawX[nodeId] += delta
    for (const c of childrenOf[nodeId] || []) shiftSubtree(c, delta)
  }

  spread(root)

  // Ensure orphan nodes are positioned
  for (const n of nodes) {
    if (rawX[n.id] === undefined) rawX[n.id] = 0
    if (depthOf[n.id] === undefined) depthOf[n.id] = 0
  }

  // --- Convert to pixel coordinates ---
  const xVals = Object.values(rawX)
  const xMin = Math.min(...xVals)
  const xMax = Math.max(...xVals)
  const xRange = Math.max(xMax - xMin, 1)
  const dMax = Math.max(...Object.values(depthOf), 0)

  const STEP_X = 90   // px per unit x
  const STEP_Y = 70   // px per depth level
  const PAD_X = 60     // left padding
  const PAD_Y = 50     // top padding

  const nodeMap = {}
  for (const n of nodes) {
    const flow = n.design_flow || 1
    const d = depthOf[n.id] || 0
    nodeMap[n.id] = {
      id: n.id,
      name: n.id,
      x: PAD_X + (rawX[n.id] - xMin) / xRange * (xRange * STEP_X),
      y: PAD_Y + d * STEP_Y,
      symbolSize: Math.max(16, Math.min(50, flow * 2.5 + 12)),
      label: { show: true, fontSize: 10, color: '#0b3b66', fontWeight: 600 },
      itemStyle: {
        color: levelColor(n.level),
        borderColor: '#ffffff',
        borderWidth: 2,
        shadowBlur: 10,
        shadowColor: 'rgba(14, 165, 233, 0.28)'
      },
      value: n
    }
  }

  const echartsNodes = Object.values(nodeMap)
  const echartsEdges = edges.map((e) => ({
    source: e.from,
    target: e.to,
    lineStyle: {
      width: Math.max(0.6, Math.min(3.5, (e.length || 100) / 1500)),
      color: '#4ab8e8',
      curveness: 0,
      opacity: 0.65
    }
  }))

  topologyChart.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      formatter: (p) => {
        if (p.dataType === 'node') {
          return `<b>${p.data.id}</b><br/>L=${p.data.value.length} m<br/>Q=${p.data.value.design_flow} m³/s<br/>水深=${p.data.value.design_depth} m`
        }
        return `${p.data.source} → ${p.data.target}<br/>L=${p.data.value?.length || '-'} m`
      }
    },
    series: [
      {
        type: 'graph',
        layout: 'none',
        roam: true,
        symbol: 'circle',
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: 5,
        data: echartsNodes,
        links: echartsEdges,
        lineStyle: { opacity: 0.65 },
        emphasis: { focus: 'adjacency', lineStyle: { width: 3 } }
      }
    ]
  })
}

function renderHeat() {
  if (!heatChartEl.value) return
  if (!heatChart) {
    heatChart = echarts.init(heatChartEl.value)
  }
  const canals = result.value.canals.map((c) => c.canal_id)
  const times = [...new Set(result.value.timeseries.map((r) => r.t_min))].sort((a, b) => a - b)
  const metric = heatMetric.value
  const data = []
  let vmin = Infinity
  let vmax = -Infinity
  const canalIdx = new Map(canals.map((c, i) => [c, i]))
  const timeIdx = new Map(times.map((t, i) => [t, i]))
  for (const r of result.value.timeseries) {
    if (!timeIdx.has(r.t_min) || !canalIdx.has(r.canal_id)) continue
    const v = Number(r[metric] || 0)
    data.push([timeIdx.get(r.t_min), canalIdx.get(r.canal_id), v])
    if (v < vmin) vmin = v
    if (v > vmax) vmax = v
  }
  if (!isFinite(vmin)) vmin = 0
  if (!isFinite(vmax)) vmax = 1
  const palette = {
    q_m3s: ['#E0F2FE', '#0EA5E9', '#082F49'],
    h_m: ['#ECFEFF', '#14B8A6', '#0F766E'],
    v_mps: ['#FEF3C7', '#F59E0B', '#92400E']
  }
  heatChart.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      position: 'top',
      formatter: (p) => `${canals[p.value[1]]} · t=${times[p.value[0]]} min<br/>${metric} = ${p.value[2]}`
    },
    grid: { top: 30, left: 90, right: 30, bottom: 60 },
    xAxis: { type: 'category', data: times, axisLabel: { color: '#5b738e' }, splitArea: { show: true } },
    yAxis: { type: 'category', data: canals, axisLabel: { color: '#5b738e' }, splitArea: { show: true } },
    visualMap: {
      min: vmin,
      max: vmax,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      textStyle: { color: '#5b738e' },
      inRange: { color: palette[metric] || palette.q_m3s }
    },
    series: [
      {
        name: metric,
        type: 'heatmap',
        data,
        progressive: 1000,
        itemStyle: { borderRadius: 2, borderColor: 'rgba(255,255,255,0.5)', borderWidth: 1 },
        emphasis: { itemStyle: { borderColor: '#082F49', borderWidth: 1 } }
      }
    ]
  })
}

function renderSeries() {
  for (const [cid, ch] of seriesCharts.entries()) {
    if (!selectedCanals.value.includes(cid)) {
      ch.dispose()
      seriesCharts.delete(cid)
    }
  }
  for (const cid of selectedCanals.value) {
    const rows = result.value.timeseries.filter((r) => r.canal_id === cid)
    if (!rows.length) continue
    const xSet = [...new Set(rows.map((r) => r.x_m))].sort((a, b) => a - b)
    const tSet = [...new Set(rows.map((r) => r.t_min))].sort((a, b) => a - b)
    const palette = ['#0EA5E9', '#14B8A6', '#8B5CF6']
    const series = xSet.map((x, i) => {
      const points = rows.filter((r) => r.x_m === x).sort((a, b) => a.t_min - b.t_min)
      return {
        name: `x = ${x} m`,
        type: 'line',
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2, color: palette[i % palette.length] },
        itemStyle: { color: palette[i % palette.length] },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: palette[i % palette.length] + '55' },
            { offset: 1, color: palette[i % palette.length] + '00' }
          ])
        },
        data: points.map((p) => [p.t_min, p.h_m])
      }
    })
    const el = seriesElByCid.get(cid)
    if (!el) continue
    let ch = seriesCharts.get(cid)
    if (!ch) {
      ch = echarts.init(el)
      seriesCharts.set(cid, ch)
    }
    ch.setOption({
      backgroundColor: 'transparent',
      title: {
        text: `${cid} · h(t)`,
        left: 'center',
        textStyle: { color: '#1e3a8a', fontSize: 13, fontWeight: 600 }
      },
      tooltip: { trigger: 'axis' },
      legend: { textStyle: { color: '#5b738e' }, top: 22, type: 'scroll', icon: 'roundRect' },
      grid: { top: 56, left: 50, right: 18, bottom: 30 },
      xAxis: {
        type: 'category',
        name: 't (min)',
        data: tSet,
        axisLabel: { color: '#5b738e' },
        nameTextStyle: { color: '#5b738e' }
      },
      yAxis: {
        type: 'value',
        name: 'h (m)',
        axisLabel: { color: '#5b738e' },
        nameTextStyle: { color: '#5b738e' },
        splitLine: { lineStyle: { color: 'rgba(91, 115, 142, 0.18)' } }
      },
      series
    })
  }
}

function handleResize() {
  topologyChart && topologyChart.resize()
  heatChart && heatChart.resize()
  for (const ch of seriesCharts.values()) ch.resize()
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (seriesRenderRaf) {
    cancelAnimationFrame(seriesRenderRaf)
    seriesRenderRaf = 0
  }
  topologyChart && topologyChart.dispose()
  heatChart && heatChart.dispose()
  for (const ch of seriesCharts.values()) ch.dispose()
  seriesCharts.clear()
})

watch(seriesElVersion, () => {
  // 用 rAF 把 renderSeries 推到浏览器渲染管线之后,避免与 result 触发的
  // 组件 patch 互相挤占
  if (seriesRenderRaf) cancelAnimationFrame(seriesRenderRaf)
  seriesRenderRaf = requestAnimationFrame(() => {
    seriesRenderRaf = 0
    if (result.value) renderSeries()
  })
})
</script>

<style scoped>
/* ============ Hero 装饰 ============ */
.canal-hydro-hero {
  position: relative;
  overflow: hidden;
  isolation: isolate;
  background:
    radial-gradient(at 18% 18%, rgba(20, 184, 166, 0.22) 0%, transparent 55%),
    radial-gradient(at 82% 12%, rgba(14, 165, 233, 0.28) 0%, transparent 55%),
    radial-gradient(at 65% 90%, rgba(139, 92, 246, 0.18) 0%, transparent 55%),
    linear-gradient(135deg, #ecfeff 0%, #f0f9ff 60%, #f5f3ff 100%);
  color: #0b3b66;
  border: 1px solid rgba(14, 165, 233, 0.18);
}
.canal-hydro-hero .hero-content {
  position: relative;
  z-index: 2;
}
.canal-hydro-eyebrow {
  background: linear-gradient(120deg, rgba(14, 165, 233, 0.18), rgba(20, 184, 166, 0.18));
  color: #0e7490;
  border: 1px solid rgba(14, 165, 233, 0.3);
}
.canal-hydro-hero .agri-page__title {
  background: linear-gradient(120deg, #0c4a6e 0%, #0e7490 50%, #6d28d9 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.canal-hydro-hero .agri-page__desc {
  color: #1e5577;
}

/* ============ Hero 标签 ============ */
.tag {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.7);
  color: #0b3b66;
}
.tag--cyan   { background: rgba(14, 165, 233, 0.12); border-color: rgba(14, 165, 233, 0.3); color: #0369a1; }
.tag--teal   { background: rgba(20, 184, 166, 0.12); border-color: rgba(20, 184, 166, 0.3); color: #0f766e; }
.tag--indigo { background: rgba(99, 102, 241, 0.12); border-color: rgba(99, 102, 241, 0.3); color: #4338ca; }
.tag--violet { background: rgba(139, 92, 246, 0.12); border-color: rgba(139, 92, 246, 0.3); color: #6d28d9; }

.sibling-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.65);
  border: 1px solid rgba(14, 165, 233, 0.2);
  color: #0c4a6e;
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
  transition: all 200ms ease;
  backdrop-filter: blur(6px);
}
.sibling-link:hover {
  background: rgba(255, 255, 255, 0.95);
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(14, 165, 233, 0.15);
}

/* ============ 卡片 / 玻璃感 (玻璃感、玻璃感图表容器、KPI 卡已迁到 agriculture.scss) ============ */
.mb12 { margin-bottom: 12px; }
.card-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.card-title { font-size: 16px; font-weight: 700; color: #0c2c4d; }
.card-desc  { font-size: 12px; color: #5b738e; margin-top: 2px; }
.header-actions { display: flex; gap: 8px; flex-wrap: wrap; }

.mb12 { margin-bottom: 12px; }
.mt12 { margin-top: 12px; }
.mt16 { margin-top: 16px; }
.mb16 { margin-bottom: 16px; }
.muted-text { color: #5b738e; font-size: 12px; margin-left: 8px; }
.db-row { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; }

/* 导入对话框 */
.import-empty { padding: 12px 4px; }
.import-options { padding-top: 4px; border-top: 1px dashed rgba(14, 165, 233, 0.18); }

.divider-soft {
  height: 1px;
  margin: 6px 0 14px;
  background: linear-gradient(90deg, transparent, rgba(14, 165, 233, 0.25), transparent);
}

.source-switch { display: inline-flex; }
.metric-switch { display: inline-flex; }

/* ============ 运行按钮 ============ */
.run-btn {
  width: 100%;
  height: 44px;
  border: 0;
  border-radius: 14px;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: #ffffff;
  background: linear-gradient(120deg, #0EA5E9 0%, #14B8A6 60%, #6366F1 100%);
  box-shadow:
    0 8px 24px rgba(14, 165, 233, 0.35),
    0 2px 6px rgba(20, 184, 166, 0.2);
  transition: transform 180ms ease, box-shadow 180ms ease, filter 180ms ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.run-btn:hover {
  transform: translateY(-1px);
  filter: brightness(1.05);
  box-shadow:
    0 14px 32px rgba(14, 165, 233, 0.45),
    0 4px 10px rgba(20, 184, 166, 0.28);
}
.run-btn:active { transform: translateY(0); filter: brightness(0.98); }
.run-btn.is-disabled,
.run-btn:disabled {
  background: linear-gradient(120deg, #cbd5e1, #94a3b8);
  box-shadow: none;
  color: #f8fafc;
  cursor: not-allowed;
}

/* ============ KPI 卡（已迁到 agriculture.scss） ============ */

/* ============ Legend pills ============ */
.legend-pills { display: flex; gap: 8px; flex-wrap: wrap; }
.legend-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 9999px;
  font-size: 12px;
  color: #5b738e;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(91, 115, 142, 0.2);
}
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.dot--cyan  { background: #0EA5E9; box-shadow: 0 0 8px #0EA5E9; }
.dot--teal  { background: #14B8A6; box-shadow: 0 0 8px #14B8A6; }
.dot--amber { background: #F59E0B; box-shadow: 0 0 8px #F59E0B; }
.dot--rose  { background: #F43F5E; box-shadow: 0 0 8px #F43F5E; }

/* ============ 图表容器 ============ */
.chart-large { width: 100%; height: 380px; border-radius: 16px; }
.chart-medium { width: 100%; height: 240px; border-radius: 16px; }
/* .chart-glass 已迁到 agriculture.scss */

.canal-picker { min-width: 220px; }
.canal-picker-list { max-width: 720px; max-height: 120px; overflow-y: auto; padding: 4px; }
.canal-checkbox-group { display: flex; flex-wrap: wrap; gap: 6px; }
.canal-checkbox-group :deep(.el-checkbox) { margin-right: 0; }
.canal-checkbox-group :deep(.el-checkbox__label) { font-size: 12px; }
.filter-select { min-width: 160px; }
.filter-radio-group { flex-wrap: wrap; }

.canal-edit-list { max-height: 360px; overflow-y: auto; }
.remove-cell { display: flex; align-items: center; padding-top: 18px; }

.config-body { max-height: calc(100vh - 340px); overflow-y: auto; padding-right: 6px; }
.config-body::-webkit-scrollbar,
.canal-edit-list::-webkit-scrollbar { width: 6px; }
.config-body::-webkit-scrollbar-thumb,
.canal-edit-list::-webkit-scrollbar-thumb { background: rgba(14, 165, 233, 0.25); border-radius: 3px; }

/* ============ Empty state ============ */
.empty-icon { font-size: 56px; color: #93c5fd; }

/* ============ 运行遮罩 ============ */
.running-overlay {
  margin-top: 16px;
  padding: 40px 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 24px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.85), rgba(240, 249, 255, 0.7));
  border: 1px solid rgba(14, 165, 233, 0.2);
}
.running-content { text-align: center; }
.running-spinner {
  width: 48px; height: 48px;
  margin: 0 auto 12px;
  border-radius: 50%;
  border: 3px solid rgba(14, 165, 233, 0.2);
  border-top-color: #0EA5E9;
  animation: spin 0.9s linear infinite;
}
.running-title { font-size: 16px; font-weight: 700; color: #0c2c4d; }
.running-desc  { font-size: 12px; color: #5b738e; margin-top: 4px; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ============ 违例表（自定义 div 渲染） ============ */
.violation-empty {
  padding: 18px;
  text-align: center;
  color: #5b738e;
  font-size: 13px;
}
.violation-scroll {
  max-height: 360px;
  overflow-y: auto;
  border-radius: 6px;
  border: 1px solid rgba(14, 165, 233, 0.12);
  background: rgba(255, 255, 255, 0.6);
}
.violation-head,
.violation-row {
  display: grid;
  grid-template-columns: 100px 110px 80px 150px 1fr;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  font-size: 12.5px;
}
.violation-head {
  position: sticky;
  top: 0;
  z-index: 1;
  background: rgba(240, 249, 255, 0.92);
  color: #0c2c4d;
  font-weight: 600;
  border-bottom: 1px solid rgba(14, 165, 233, 0.18);
}
.violation-row {
  border-bottom: 1px solid rgba(14, 165, 233, 0.08);
  color: #334155;
}
.violation-row:nth-child(even) { background: rgba(240, 249, 255, 0.35); }
.violation-row:last-child { border-bottom: 0; }
.violation-row .col { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.violation-row .col-detail { white-space: normal; line-height: 1.45; }

/* ============ 违例分布诊断 ============ */
.vio-breakdown {
  margin-top: 14px;
  padding: 14px 16px 12px;
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.04), rgba(99, 102, 241, 0.04));
  border: 1px solid rgba(14, 165, 233, 0.16);
}
.vio-breakdown__head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 10px;
}
.vio-breakdown__title {
  font-size: 13px;
  font-weight: 700;
  color: #0c2c4d;
  letter-spacing: 0.02em;
}
.vio-breakdown__hint {
  font-size: 11.5px;
  color: #5b738e;
}
.vio-breakdown__types {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.vio-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.7);
  color: #334155;
}
.vio-chip--danger { border-color: rgba(239, 68, 68, 0.45); background: rgba(254, 226, 226, 0.55); }
.vio-chip--warning { border-color: rgba(245, 158, 11, 0.45); background: rgba(254, 243, 199, 0.55); }
.vio-chip--info { border-color: rgba(14, 165, 233, 0.4); background: rgba(224, 242, 254, 0.55); }
.vio-chip__name { font-weight: 600; }
.vio-chip__count {
  font-variant-numeric: tabular-nums;
  font-weight: 700;
  color: #0c2c4d;
}
.vio-chip__pct { color: #5b738e; font-variant-numeric: tabular-nums; }
.vio-breakdown__section { margin-top: 12px; }
.vio-breakdown__sub {
  font-size: 12px;
  font-weight: 600;
  color: #0c2c4d;
  margin-bottom: 6px;
}
.vio-bar-list,
.vio-bucket-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.vio-bar,
.vio-bucket {
  display: grid;
  grid-template-columns: 120px 1fr 90px;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: #334155;
}
.vio-bar__name,
.vio-bucket__label {
  font-variant-numeric: tabular-nums;
  font-weight: 500;
  color: #0c2c4d;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.vio-bar__track {
  position: relative;
  height: 8px;
  background: rgba(14, 165, 233, 0.08);
  border-radius: 4px;
  overflow: hidden;
}
.vio-bar__fill {
  position: absolute;
  inset: 0 auto 0 0;
  background: linear-gradient(90deg, #0ea5e9, #6366f1);
  border-radius: 4px;
  min-width: 2px;
  transition: width 0.3s ease;
}
.vio-bar__count {
  text-align: right;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  color: #0c2c4d;
}

/* ============ 响应式 ============ */
@media (max-width: 1100px) {
  .chart-large { height: 320px; }
}
@media (max-width: 768px) {
  .chart-large { height: 280px; }
  .chart-medium { height: 220px; }
}

.form-hint {
  font-size: 12px;
  line-height: 1.6;
  color: #5b738e;
  padding-top: 6px;
}
</style>
