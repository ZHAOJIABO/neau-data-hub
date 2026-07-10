<template>
  <div class="app-container agri-page canal-optimize-page">
    <section class="agri-page__hero canal-optimize-hero">
      <div class="hero-content">
        <span class="agri-page__eyebrow canal-optimize-eyebrow">NSGA-II OPTIMIZATION</span>
        <h1 class="agri-page__title">渠系优化配水</h1>
        <p class="agri-page__desc">
          基于 NSGA-II 多目标进化算法的渠系分级优化：<strong>干支优化</strong>对干-支渠道进行连续配水，
          <strong>支斗轮续灌优化</strong>对支-斗渠道进行组间轮灌组内续灌。选择渠段后提交后端计算，
          ECharts 动态渲染所有图表。
        </p>
        <div class="agri-page__siblings">
          <router-link to="/model/irrigation" class="sibling-link">
            <el-icon><Promotion /></el-icon>
            <span>灌溉决策</span>
          </router-link>
          <router-link to="/model/canal/kinematic" class="sibling-link">
            <el-icon><Promotion /></el-icon>
            <span>渠系水动力学</span>
          </router-link>
        </div>
      </div>
      <div class="agri-page__tags">
        <span class="canal-optimize-tag">NSGA-II</span>
        <span class="canal-optimize-tag canal-optimize-tag--pink">干支 / 支斗 分级</span>
        <span class="canal-optimize-tag canal-optimize-tag--indigo">ECharts 动态</span>
      </div>
      <div class="hero-decor" aria-hidden="true">
        <span class="hero-decor__wave hero-decor__wave--1" />
        <span class="hero-decor__wave hero-decor__wave--2" />
        <span class="hero-decor__wave hero-decor__wave--3" />
      </div>
    </section>

    <el-row :gutter="20" class="page-layout">
      <!-- ============ 左侧：参数配置 ============ -->
      <el-col :xs="24" :lg="8" class="config-col">
        <el-card shadow="hover" class="config-card glass-card result-card">
          <template #header>
            <div class="card-header">
              <div>
                <div class="card-title">渠系优化配水</div>
                <div class="card-desc">加载渠系数据并选择目标渠段，提交后端分级优化计算。</div>
              </div>
              <el-tag :type="resultError ? 'danger' : activeResult ? 'success' : 'info'">
                {{ resultError ? '接口异常' : activeResult ? '方案已生成' : '待提交' }}
              </el-tag>
            </div>
            <!-- Tab 切换 -->
            <el-tabs v-model="activeTab" class="mode-tabs mt8" @tab-change="onTabChange">
              <el-tab-pane label="干支优化" name="trunk-branch" />
              <el-tab-pane label="支斗轮续灌" name="branch-lateral" />
            </el-tabs>
          </template>

          <div class="config-body">
            <el-alert type="info" :closable="false" show-icon
              title="算法超参默认（POP=80, GEN=60）保证秒级响应；如需更高精度可调大 pop/n_gen。"
              class="mb12" />

            <el-form ref="formRef" :model="form" label-position="top" size="small" class="opt-form">
              <!-- 通用：接口 API Key -->
              <el-form-item label="接口 API Key" required>
                <el-input v-model="form.apiKey" type="password" show-password clearable
                  placeholder="X-Irrigation-Api-Key" />
              </el-form-item>

              <!-- 通用：加载数据 -->
              <div class="db-row mb12">
                <el-button size="small" type="primary" plain @click="loadFromDb" :loading="loadingDb">
                  加载渠系数据
                </el-button>
                <span class="muted-text">已加载 {{ dbCanals.length }} 条</span>
              </div>

              <!-- ============ 干支 Tab ============ -->
              <template v-if="activeTab === 'trunk-branch'">
                <el-form-item label="选择干渠（level-2）" required>
                  <el-select v-model="form.trunkCanalId" placeholder="请选择一条干渠" filterable clearable
                    style="width: 100%" :disabled="dbCanals.length === 0" @change="onTrunkChange">
                    <el-option v-for="c in trunkCanals" :key="c.canal_id"
                      :label="`${c.canal_id}${c.canal_name ? ' · ' + c.canal_name : ''} (L${c.level})`"
                      :value="c.canal_id" />
                  </el-select>
                </el-form-item>

                <div v-if="trunkPreview" class="subtree-preview mb12">
                  <div class="subtree-preview__label">
                    将传入 {{ trunkPreview.stats.n_trunk + trunkPreview.stats.n_branch }} 条渠道：
                  </div>
                  <div class="subtree-preview__levels">
                    <el-tag size="small" class="mr6" type="info">
                      干 L2: {{ trunkPreview.stats.n_trunk }}条
                    </el-tag>
                    <el-tag size="small" type="success">
                      支 L3: {{ trunkPreview.stats.n_branch }}条
                    </el-tag>
                  </div>
                </div>

                <div class="divider-soft" />

                <el-row :gutter="12">
                  <el-col :span="12">
                    <el-form-item label="t_max (h)">
                      <el-input-number v-model="form.tb_tMax" :min="1" :max="2000" :step="1" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="q/qd 下限">
                      <el-input-number v-model="form.tb_flowRatioMin" :min="0.1" :max="1" :step="0.05" :precision="2"
                        style="width: 100%" />
                    </el-form-item>
                  </el-col>
                </el-row>

                <el-row :gutter="12">
                  <el-col :span="12">
                    <el-form-item label="q/qd 上限">
                      <el-input-number v-model="form.tb_flowRatioMax" :min="0.1" :max="1.5" :step="0.05" :precision="2"
                        style="width: 100%" />
                    </el-form-item>
                  </el-col>
                </el-row>

                <el-divider content-position="left">NSGA-II 超参</el-divider>

                <el-row :gutter="12">
                  <el-col :span="12">
                    <el-form-item label="种群 pop">
                      <el-input-number v-model="form.tb_popSize" :min="10" :max="600" :step="10" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="迭代 n_gen">
                      <el-input-number v-model="form.tb_nGen" :min="10" :max="2000" :step="50" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                </el-row>

                <el-form-item label="随机种子">
                  <el-input-number v-model="form.tb_seed" :min="0" :max="999" :step="1" style="width: 100%" />
                </el-form-item>

                <el-divider content-position="left">土壤参数</el-divider>

                <el-row :gutter="12">
                  <el-col :span="12">
                    <el-form-item label="渗透指数 m">
                      <el-input-number v-model="form.tb_permIndexM" :min="0" :step="0.05" :precision="3"
                        style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="渗透系数 A">
                      <el-input-number v-model="form.tb_permCoefA" :min="0" :step="0.1" :precision="3"
                        style="width: 100%" />
                    </el-form-item>
                  </el-col>
                </el-row>

                <el-divider content-position="left">目标权重（时间优先）</el-divider>

                <el-row :gutter="12">
                  <el-col :span="8">
                    <el-form-item label="w_时间">
                      <el-input-number v-model="form.tb_prefTime" :min="0" :max="1" :step="0.05" :precision="2"
                        style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="w_损失">
                      <el-input-number v-model="form.tb_prefLoss" :min="0" :max="1" :step="0.05" :precision="2"
                        style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="w_波动">
                      <el-input-number v-model="form.tb_prefFlowVar" :min="0" :max="1" :step="0.05" :precision="2"
                        style="width: 100%" />
                    </el-form-item>
                  </el-col>
                </el-row>

                <el-form-item label="混合系数 α">
                  <el-input-number v-model="form.tb_alpha" :min="0" :max="1" :step="0.05" :precision="2"
                    style="width: 100%" />
                </el-form-item>
              </template>

              <!-- ============ 支斗 Tab ============ -->
              <template v-else>
                <el-form-item label="选择支渠（level-3）" required>
                  <el-select v-model="form.branchCanalId" placeholder="请选择一条支渠" filterable clearable
                    style="width: 100%" :disabled="dbCanals.length === 0" @change="onBranchChange">
                    <el-option v-for="c in branchCanals" :key="c.canal_id"
                      :label="`${c.canal_id}${c.canal_name ? ' · ' + c.canal_name : ''} (L${c.level})`"
                      :value="c.canal_id" />
                  </el-select>
                </el-form-item>

                <div v-if="branchPreview" class="subtree-preview mb12">
                  <div class="subtree-preview__label">
                    将传入 {{ branchPreview.stats.n_branch + branchPreview.stats.n_lateral }} 条渠道：
                  </div>
                  <div class="subtree-preview__levels">
                    <el-tag size="small" class="mr6" type="info">
                      支 L3: {{ branchPreview.stats.n_branch }}条
                    </el-tag>
                    <el-tag size="small" type="warning">
                      斗 L4: {{ branchPreview.stats.n_lateral }}条
                    </el-tag>
                  </div>
                </div>

                <div class="divider-soft" />

                <el-row :gutter="12">
                  <el-col :span="12">
                    <el-form-item label="t_max (h)">
                      <el-input-number v-model="form.bl_tMax" :min="1" :max="2000" :step="1" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="最小组数">
                      <el-input-number v-model="form.bl_minGroups" :min="2" :max="10" :step="1" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                </el-row>

                <el-row :gutter="12">
                  <el-col :span="12">
                    <el-form-item label="最大组数">
                      <el-input-number v-model="form.bl_maxGroups" :min="2" :max="10" :step="1" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="q/qd 下限">
                      <el-input-number v-model="form.bl_flowRatioMin" :min="0.1" :max="1" :step="0.05" :precision="2"
                        style="width: 100%" />
                    </el-form-item>
                  </el-col>
                </el-row>

                <el-row :gutter="12">
                  <el-col :span="12">
                    <el-form-item label="q/qd 上限">
                      <el-input-number v-model="form.bl_flowRatioMax" :min="0.1" :max="1.5" :step="0.05" :precision="2"
                        style="width: 100%" />
                    </el-form-item>
                  </el-col>
                </el-row>

                <el-divider content-position="left">NSGA-II 超参</el-divider>

                <el-row :gutter="12">
                  <el-col :span="12">
                    <el-form-item label="种群 pop">
                      <el-input-number v-model="form.bl_popSize" :min="10" :max="600" :step="10" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="迭代 n_gen">
                      <el-input-number v-model="form.bl_nGen" :min="10" :max="2000" :step="50" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                </el-row>

                <el-form-item label="随机种子">
                  <el-input-number v-model="form.bl_seed" :min="0" :max="999" :step="1" style="width: 100%" />
                </el-form-item>

                <el-divider content-position="left">土壤参数</el-divider>

                <el-row :gutter="12">
                  <el-col :span="12">
                    <el-form-item label="渗透指数 m">
                      <el-input-number v-model="form.bl_permIndexM" :min="0" :step="0.05" :precision="3"
                        style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="渗透系数 A">
                      <el-input-number v-model="form.bl_permCoefA" :min="0" :step="0.1" :precision="3"
                        style="width: 100%" />
                    </el-form-item>
                  </el-col>
                </el-row>

                <el-divider content-position="left">目标权重</el-divider>

                <el-row :gutter="12">
                  <el-col :span="8">
                    <el-form-item label="w_时间">
                      <el-input-number v-model="form.bl_prefTime" :min="0" :max="1" :step="0.05" :precision="2"
                        style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="w_损失">
                      <el-input-number v-model="form.bl_prefLoss" :min="0" :max="1" :step="0.05" :precision="2"
                        style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="w_波动">
                      <el-input-number v-model="form.bl_prefFlowVar" :min="0" :max="1" :step="0.05" :precision="2"
                        style="width: 100%" />
                    </el-form-item>
                  </el-col>
                </el-row>

                <el-form-item label="混合系数 α">
                  <el-input-number v-model="form.bl_alpha" :min="0" :max="1" :step="0.05" :precision="2"
                    style="width: 100%" />
                </el-form-item>
              </template>

              <div class="action-row">
                <el-button type="primary" :loading="submitting" :disabled="!canSubmit" @click="submitOptimize"
                  class="action-primary">
                  {{ activeTab === 'trunk-branch' ? '开始干支优化' : '开始支斗轮续灌优化' }}
                </el-button>
                <el-button :disabled="!activeResult" @click="resetResult" class="action-secondary">
                  清空结果
                </el-button>
              </div>
            </el-form>

            <el-divider content-position="left">接口说明</el-divider>
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="干支接口">
                /api/v1/irrigation/canal/optimize/trunk-branch
              </el-descriptions-item>
              <el-descriptions-item label="支斗接口">
                /api/v1/irrigation/canal/optimize/branch-lateral
              </el-descriptions-item>
              <el-descriptions-item label="请求方式">POST / application/json</el-descriptions-item>
              <el-descriptions-item label="鉴权头">X-Irrigation-Api-Key</el-descriptions-item>
              <el-descriptions-item label="返回">结构化 JSON</el-descriptions-item>
            </el-descriptions>
          </div>
        </el-card>
      </el-col>

      <!-- ============ 右侧：结果图表 ============ -->
      <el-col :xs="24" :lg="16" class="result-col">
        <!-- 未提交时的占位 -->
        <div v-if="!activeResult" class="placeholder glass-card result-card">
          <div class="placeholder-title">尚未提交优化</div>
          <div class="placeholder-desc">
            切换 Tab 选择干支优化或支斗轮续灌，配置参数后提交。后端返回结构化 JSON，
            将在右侧依次展示：KPI 概览卡、甘特图、时序曲线、Pareto 前沿、损失分析。
          </div>
        </div>

        <!-- ============ 干支优化结果 ============ -->
        <template v-else-if="activeTab === 'trunk-branch' && tbResult">
          <!-- KPI 概览 -->
          <div class="kpi-row">
            <div class="kpi-box kpi-box--0">
              <div class="kpi-label">F1 总输水时间</div>
              <div class="kpi-value">{{ fmtNumber(tbResult.topsis_summary?.total_time_h, 2) }}<span
                  class="kpi-unit">h</span></div>
              <div class="kpi-foot">TOPSIS 优选方案</div>
            </div>
            <div class="kpi-box kpi-box--1">
              <div class="kpi-label">TOPSIS 评分</div>
              <div class="kpi-value">{{ fmtNumber(tbResult.summary?.topsis_score, 4) }}</div>
              <div class="kpi-foot">越接近 1 越优</div>
            </div>
            <div class="kpi-box kpi-box--2">
              <div class="kpi-label">F3 流量波动</div>
              <div class="kpi-value">{{ fmtNumber(tbResult.topsis_summary?.flow_var, 4) }}</div>
              <div class="kpi-foot">Var(Q) 越小越平稳</div>
            </div>
            <div class="kpi-box kpi-box--3">
              <div class="kpi-label">F2 全渠系渗漏损失</div>
              <div class="kpi-value">{{ fmtNumber(tbResult.topsis_summary?.total_loss_m3, 0) }}<span
                  class="kpi-unit">m³</span></div>
              <div class="kpi-foot">
                干 {{ fmtNumber(tbResult.topsis_summary?.trunk_loss_m3, 0) }} +
                支 {{ fmtNumber(tbResult.topsis_summary?.branch_loss_m3, 0) }}
              </div>
            </div>
            <div class="kpi-box kpi-box--4">
              <div class="kpi-label">渠系规模</div>
              <div class="kpi-value">{{ tbResult.summary?.n_branches }}<span class="kpi-unit">支</span></div>
              <div class="kpi-foot">{{ tbResult.summary?.trunk_canal_id }} · 干支优化</div>
            </div>
            <div class="kpi-box kpi-box--5">
              <div class="kpi-label">干渠峰值流量</div>
              <div class="kpi-value">{{ fmtNumber(tbResult.trunk_canal?.Q_total_m3s, 3) }}<span
                  class="kpi-unit">m³/s</span></div>
              <div class="kpi-foot">设计 {{ fmtNumber(tbResult.trunk_canal?.Qmax_m3s, 3) }} m³/s</div>
            </div>
          </div>

          <!-- 熵权 / 目标值 / 损失构成 -->
          <el-row :gutter="20" class="chart-row">
            <el-col :xs="24" :sm="12" :lg="8">
              <el-card shadow="hover" class="chart-card glass-card result-card">
                <template #header>
                  <div class="chart-header">
                    <span class="chart-title">熵权分布</span>
                    <span class="chart-sub">三目标权重</span>
                  </div>
                </template>
                <div ref="tbEntropyRef" class="chart" />
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :lg="8">
              <el-card shadow="hover" class="chart-card glass-card result-card">
                <template #header>
                  <div class="chart-header">
                    <span class="chart-title">目标值归一化</span>
                    <span class="chart-sub">F1/F2/F3 相对</span>
                  </div>
                </template>
                <div ref="tbObjectiveRef" class="chart" />
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :lg="8">
              <el-card shadow="hover" class="chart-card glass-card result-card">
                <template #header>
                  <div class="chart-header">
                    <span class="chart-title">损失构成</span>
                    <span class="chart-sub">干 / 支</span>
                  </div>
                </template>
                <div ref="tbLossPieRef" class="chart" />
              </el-card>
            </el-col>
          </el-row>

          <!-- Pareto 前沿 3D -->
          <el-card shadow="hover" class="chart-card glass-card result-card mt16">
            <template #header>
              <div class="chart-header">
                <div>
                  <span class="chart-title">Pareto 前沿（3D 散点）</span>
                  <span class="chart-sub">F1 时间 / F2 损失 / F3 波动 · 颜色=TOPSIS 评分</span>
                </div>
                <el-tag size="small" type="success">
                  已选 {{ tbParetoSelected }} / {{ tbResult.pareto?.length || 0 }}
                </el-tag>
              </div>
            </template>
            <div ref="tbParetoRef" class="chart chart-tall" />
          </el-card>

          <!-- 干支配水甘特图 -->
          <el-card shadow="hover" class="chart-card glass-card result-card mt16">
            <template #header>
              <div class="chart-header">
                <div>
                  <span class="chart-title">干支配水甘特图</span>
                  <span class="chart-sub">干渠连续配水 + 支渠依次开启</span>
                </div>
                <div class="chart-tags">
                  <el-tag size="small" type="primary">
                    干渠 {{ fmtNumber(tbResult.trunk_canal?.t_max_h, 2) }} h
                  </el-tag>
                  <el-tag size="small" type="warning">
                    峰值 {{ fmtNumber(tbResult.trunk_canal?.Q_total_m3s, 3) }} m³/s
                  </el-tag>
                </div>
              </div>
            </template>
            <div ref="tbGanttRef" class="chart chart-tall" />
          </el-card>

          <!-- 干渠时序 -->
          <el-card shadow="hover" class="chart-card glass-card result-card mt16">
            <template #header>
              <div class="chart-header">
                <div>
                  <span class="chart-title">干渠流量 / 水位 时序</span>
                  <span class="chart-sub">阶梯式连续配水 · 点数 {{ tbResult.time_series?.length || 0 }}</span>
                </div>
              </div>
            </template>
            <div ref="tbTimeSeriesRef" class="chart chart-tall" />
          </el-card>

          <!-- 支渠详情表 -->
          <el-card shadow="hover" class="chart-card glass-card result-card mt16">
            <template #header>
              <div class="chart-header">
                <span class="chart-title">支渠配水详情</span>
              </div>
            </template>
            <el-table :data="tbResult.branches || []" border size="small" stripe>
              <el-table-column prop="name" label="支渠" min-width="100" />
              <el-table-column label="设计流量" min-width="110" align="right">
                <template #default="{ row }">{{ fmtNumber(row.qd, 3) }} m³/s</template>
              </el-table-column>
              <el-table-column label="实际流量" min-width="110" align="right">
                <template #default="{ row }">{{ fmtNumber(row.q_actual, 4) }} m³/s</template>
              </el-table-column>
              <el-table-column label="占比" min-width="80" align="right">
                <template #default="{ row }">{{ fmtNumber(row.ratio, 4) }}</template>
              </el-table-column>
              <el-table-column label="开始" min-width="80" align="right">
                <template #default="{ row }">{{ fmtNumber(row.t_start_h, 2) }} h</template>
              </el-table-column>
              <el-table-column label="持续" min-width="80" align="right">
                <template #default="{ row }">{{ fmtNumber(row.duration_h, 2) }} h</template>
              </el-table-column>
              <el-table-column label="结束" min-width="80" align="right">
                <template #default="{ row }">{{ fmtNumber(row.t_end_h, 2) }} h</template>
              </el-table-column>
              <el-table-column label="损失" min-width="100" align="right">
                <template #default="{ row }">{{ fmtNumber(row.loss_m3, 0) }} m³</template>
              </el-table-column>
            </el-table>
          </el-card>
        </template>

        <!-- ============ 支斗轮续灌结果 ============ -->
        <template v-else-if="activeTab === 'branch-lateral' && blResult">
          <!-- KPI 概览 -->
          <div class="kpi-row">
            <div class="kpi-box kpi-box--0">
              <div class="kpi-label">F1 总输水时间</div>
              <div class="kpi-value">{{ fmtNumber(blResult.topsis_summary?.total_time_h, 2) }}<span
                  class="kpi-unit">h</span></div>
              <div class="kpi-foot">TOPSIS 优选方案</div>
            </div>
            <div class="kpi-box kpi-box--1">
              <div class="kpi-label">TOPSIS 评分</div>
              <div class="kpi-value">{{ fmtNumber(blResult.summary?.topsis_score, 4) }}</div>
              <div class="kpi-foot">越接近 1 越优</div>
            </div>
            <div class="kpi-box kpi-box--2">
              <div class="kpi-label">最优分组数</div>
              <div class="kpi-value">{{ blResult.summary?.best_n_groups }}<span class="kpi-unit">组</span></div>
              <div class="kpi-foot">组间轮灌 / 组内续灌</div>
            </div>
            <div class="kpi-box kpi-box--3">
              <div class="kpi-label">F2 渗漏损失</div>
              <div class="kpi-value">{{ fmtNumber(blResult.topsis_summary?.total_loss_m3, 0) }}<span
                  class="kpi-unit">m³</span></div>
              <div class="kpi-foot">
                支 {{ fmtNumber(blResult.topsis_summary?.branch_loss_m3, 0) }} +
                斗 {{ fmtNumber(blResult.topsis_summary?.lateral_loss_m3, 0) }}
              </div>
            </div>
            <div class="kpi-box kpi-box--4">
              <div class="kpi-label">渠系规模</div>
              <div class="kpi-value">{{ blResult.summary?.n_laterals }}<span class="kpi-unit">斗</span></div>
              <div class="kpi-foot">{{ blResult.summary?.branch_canal_id }} · 支斗轮续灌</div>
            </div>
            <div class="kpi-box kpi-box--5">
              <div class="kpi-label">支渠设计流量</div>
              <div class="kpi-value">{{ fmtNumber(blResult.branch_canal?.Q_design_m3s, 3) }}<span
                  class="kpi-unit">m³/s</span></div>
              <div class="kpi-foot">轮灌总时间 {{ fmtNumber(blResult.branch_canal?.t_max_h, 2) }} h</div>
            </div>
          </div>

          <!-- 熵权 / 目标值 / 损失构成 -->
          <el-row :gutter="20" class="chart-row">
            <el-col :xs="24" :sm="12" :lg="8">
              <el-card shadow="hover" class="chart-card glass-card result-card">
                <template #header>
                  <div class="chart-header">
                    <span class="chart-title">熵权分布</span>
                    <span class="chart-sub">三目标权重</span>
                  </div>
                </template>
                <div ref="blEntropyRef" class="chart" />
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :lg="8">
              <el-card shadow="hover" class="chart-card glass-card result-card">
                <template #header>
                  <div class="chart-header">
                    <span class="chart-title">目标值归一化</span>
                    <span class="chart-sub">F1/F2/F3 相对</span>
                  </div>
                </template>
                <div ref="blObjectiveRef" class="chart" />
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :lg="8">
              <el-card shadow="hover" class="chart-card glass-card result-card">
                <template #header>
                  <div class="chart-header">
                    <span class="chart-title">损失构成</span>
                    <span class="chart-sub">支 / 斗</span>
                  </div>
                </template>
                <div ref="blLossPieRef" class="chart" />
              </el-card>
            </el-col>
          </el-row>

          <!-- Pareto 前沿 3D -->
          <el-card shadow="hover" class="chart-card glass-card result-card mt16">
            <template #header>
              <div class="chart-header">
                <div>
                  <span class="chart-title">Pareto 前沿（3D 散点）</span>
                  <span class="chart-sub">F1 时间 / F2 损失 / F3 波动 · 颜色=TOPSIS 评分</span>
                </div>
                <el-tag size="small" type="success">
                  已选 {{ blParetoSelected }} / {{ blResult.pareto?.length || 0 }}
                </el-tag>
              </div>
            </template>
            <div ref="blParetoRef" class="chart chart-tall" />
          </el-card>

          <!-- 轮灌分组甘特图 -->
          <el-card shadow="hover" class="chart-card glass-card result-card mt16">
            <template #header>
              <div class="chart-header">
                <div>
                  <span class="chart-title">斗渠轮续灌甘特图</span>
                  <span class="chart-sub">组间轮灌 · 组内续灌</span>
                </div>
                <el-tag size="small" type="primary">
                  {{ blResult.groups?.length || 0 }} 轮灌组
                </el-tag>
              </div>
            </template>
            <div ref="blGanttRef" class="chart chart-tall" />
          </el-card>

          <!-- 斗渠损失柱状图 -->
          <el-card shadow="hover" class="chart-card glass-card result-card mt16">
            <template #header>
              <div class="chart-header">
                <span class="chart-title">斗渠输水损失</span>
              </div>
            </template>
            <div ref="blLossBarRef" class="chart chart-tall" />
          </el-card>

          <!-- 斗渠详情表 -->
          <el-card shadow="hover" class="chart-card glass-card result-card mt16">
            <template #header>
              <div class="chart-header">
                <span class="chart-title">斗渠配水详情</span>
              </div>
            </template>
            <el-table :data="blResult.laterals || []" border size="small" stripe>
              <el-table-column prop="name" label="斗渠" min-width="100" />
              <el-table-column label="所属组" min-width="80" align="center">
                <template #default="{ row }">
                  <el-tag size="small">G{{ row.group }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="设计流量" min-width="110" align="right">
                <template #default="{ row }">{{ fmtNumber(row.Q_design, 3) }} m³/s</template>
              </el-table-column>
              <el-table-column label="实际流量" min-width="110" align="right">
                <template #default="{ row }">{{ fmtNumber(row.Q_actual, 4) }} m³/s</template>
              </el-table-column>
              <el-table-column label="占比" min-width="80" align="right">
                <template #default="{ row }">{{ fmtNumber(row.ratio, 4) }}</template>
              </el-table-column>
              <el-table-column label="持续" min-width="80" align="right">
                <template #default="{ row }">{{ fmtNumber(row.duration_h, 2) }} h</template>
              </el-table-column>
              <el-table-column label="损失" min-width="100" align="right">
                <template #default="{ row }">{{ fmtNumber(row.loss_m3, 0) }} m³</template>
              </el-table-column>
            </el-table>
          </el-card>
        </template>

        <!-- 错误提示 -->
        <div v-if="resultError" class="error-box glass-card result-card mt16">
          <el-alert type="danger" :title="resultError" show-icon :closable="true" />
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, getCurrentInstance, nextTick, onUnmounted, reactive, ref, watch } from 'vue'
import { Promotion } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import 'echarts-gl'

import { runTrunkBranchOptimize, runBranchLateralOptimize, listCanal } from '@/api/model/canal'

defineOptions({ name: 'CanalOptimize' })

const { proxy } = getCurrentInstance()
const IRRIGATION_API_KEY = import.meta.env.VITE_IRRIGATION_API_KEY || 'irrigation_live_20260605_f2K9mQ7xLp4N8vRb6TzY'

const submitting = ref(false)
const loadingDb = ref(false)
const activeTab = ref('trunk-branch')
const resultError = ref('')

// 干支结果 & 支斗结果
const tbResult = ref(null)
const blResult = ref(null)

const activeResult = computed(() => activeTab.value === 'trunk-branch' ? tbResult.value : blResult.value)

// Chart refs
const tbEntropyRef = ref(null)
const tbObjectiveRef = ref(null)
const tbLossPieRef = ref(null)
const tbParetoRef = ref(null)
const tbGanttRef = ref(null)
const tbTimeSeriesRef = ref(null)
const blEntropyRef = ref(null)
const blObjectiveRef = ref(null)
const blLossPieRef = ref(null)
const blParetoRef = ref(null)
const blGanttRef = ref(null)
const blLossBarRef = ref(null)

let tbEntropyChart = null, tbObjectiveChart = null, tbLossPieChart = null
let tbParetoChart = null, tbGanttChart = null, tbTimeSeriesChart = null
let blEntropyChart = null, blObjectiveChart = null, blLossPieChart = null
let blParetoChart = null, blGanttChart = null, blLossBarChart = null

const tbParetoSelected = computed(() => (tbResult.value?.pareto || []).filter(p => p.selected).length)
const blParetoSelected = computed(() => (blResult.value?.pareto || []).filter(p => p.selected).length)

// ── 表单 ──
const form = reactive({
  apiKey: IRRIGATION_API_KEY,
  // 干支
  trunkCanalId: '',
  tb_tMax: 360, tb_flowRatioMin: 0.6, tb_flowRatioMax: 1.0,
  tb_popSize: 120, tb_nGen: 120, tb_seed: 1,
  tb_permIndexM: 0.4, tb_permCoefA: 1.9,
  tb_prefTime: 0.7, tb_prefLoss: 0.1, tb_prefFlowVar: 0.2,
  tb_alpha: 0.5,
  // 支斗
  branchCanalId: '',
  bl_tMax: 360, bl_flowRatioMin: 0.6, bl_flowRatioMax: 1.0,
  bl_minGroups: 2, bl_maxGroups: 6,
  bl_popSize: 100, bl_nGen: 100, bl_seed: 1,
  bl_permIndexM: 0.4, bl_permCoefA: 1.9,
  bl_prefTime: 0.4, bl_prefLoss: 0.3, bl_prefFlowVar: 0.3,
  bl_alpha: 0.5,
})

// ── 数据库渠段 ──
const dbCanals = ref([])

// 过滤后的选择列表
const trunkCanals = computed(() => dbCanals.value.filter(c => c.level === '2'))
const branchCanals = computed(() => dbCanals.value.filter(c => c.level === '3'))

// ── 干支子树预览 ──
const trunkPreview = computed(() => {
  if (!form.trunkCanalId) return null
  const trunk = dbCanals.value.find(c => c.canal_id === form.trunkCanalId)
  if (!trunk) return null
  const branchSet = new Set()
  const queue = [form.trunkCanalId]
  while (queue.length) {
    const pid = queue.shift()
    for (const c of dbCanals.value) {
      if (c.parent_id === pid) {
        if (c.level === '3') branchSet.add(c.canal_id)
        if (!branchSet.has(c.canal_id)) queue.push(c.canal_id)
      }
    }
  }
  return {
    stats: {
      n_trunk: 1,
      n_branch: branchSet.size,
    }
  }
})

// ── 支斗子树预览 ──
const branchPreview = computed(() => {
  if (!form.branchCanalId) return null
  const branch = dbCanals.value.find(c => c.canal_id === form.branchCanalId)
  if (!branch) return null
  const lateralSet = new Set()
  const queue = [form.branchCanalId]
  while (queue.length) {
    const pid = queue.shift()
    for (const c of dbCanals.value) {
      if (c.parent_id === pid) {
        if (c.level === '4') lateralSet.add(c.canal_id)
        if (!lateralSet.has(c.canal_id)) queue.push(c.canal_id)
      }
    }
  }
  return {
    stats: {
      n_branch: 1,
      n_lateral: lateralSet.size,
    }
  }
})

// ── 提交条件 ──
const canSubmit = computed(() => {
  if (activeTab.value === 'trunk-branch') {
    return form.trunkCanalId && trunkPreview.value && trunkPreview.value.stats.n_branch > 0
  }
  return form.branchCanalId && branchPreview.value && branchPreview.value.stats.n_lateral > 0
})

// ── 收集子树 ──
function collectTrunkSubtree() {
  const included = new Set([form.trunkCanalId])
  const queue = [form.trunkCanalId]
  while (queue.length) {
    const pid = queue.shift()
    for (const c of dbCanals.value) {
      if (c.parent_id === pid && !included.has(c.canal_id)) {
        if (c.level === '2' || c.level === '3') {
          included.add(c.canal_id)
          queue.push(c.canal_id)
        }
      }
    }
  }
  const canals = dbCanals.value.filter(c => included.has(c.canal_id))
  const topology = canals
    .filter(c => c.parent_id != null)
    .map(c => ({ canal_id: c.canal_id, parent_id: c.parent_id }))
  return { canals, topology }
}

function collectBranchSubtree() {
  const included = new Set([form.branchCanalId])
  const queue = [form.branchCanalId]
  while (queue.length) {
    const pid = queue.shift()
    for (const c of dbCanals.value) {
      if (c.parent_id === pid && !included.has(c.canal_id)) {
        if (c.level === '3' || c.level === '4') {
          included.add(c.canal_id)
          queue.push(c.canal_id)
        }
      }
    }
  }
  const canals = dbCanals.value.filter(c => included.has(c.canal_id))
  const topology = canals
    .filter(c => c.parent_id != null)
    .map(c => ({ canal_id: c.canal_id, parent_id: c.parent_id }))
  return { canals, topology }
}

function onTabChange() {
  resetResult()
}

function onTrunkChange() {
  tbResult.value = null
}

function onBranchChange() {
  blResult.value = null
}

// ── 加载数据 ──
async function loadFromDb() {
  loadingDb.value = true
  try {
    const res = await listCanal({ pageNum: 1, pageSize: 200 })
    const rows = res?.rows || res?.data?.rows || []
    dbCanals.value = rows.map(r => ({
      canal_id: r.canal_id ?? r.canalId,
      canal_name: r.canal_name ?? r.canalName,
      parent_id: r.parent_id ?? r.parentId ?? null,
      level: r.level != null ? String(r.level) : null,
      length: parseFloat(r.length ?? 0),
      design_flow: parseFloat(r.design_flow ?? r.designFlow ?? 0),
      bottom_width: parseFloat(r.bottom_width ?? r.bottomWidth ?? 0),
      slope: parseFloat(r.slope ?? 0),
      side_slope: parseFloat(r.side_slope ?? 1.5),
      roughness: parseFloat(r.roughness ?? 0.015),
      water_demand: parseFloat(r.water_demand ?? r.waterDemand ?? 0),
      position: parseFloat(r.position ?? 0),
    })).filter(r => r.canal_id != null)
    form.trunkCanalId = ''
    form.branchCanalId = ''
    proxy.$modal.msgSuccess(`已加载 ${dbCanals.value.length} 条渠段`)
  } catch (err) {
    proxy.$modal.msgError('获取渠系数据失败：' + (err?.message || err))
  } finally {
    loadingDb.value = false
  }
}

function resetResult() {
  tbResult.value = null
  blResult.value = null
  resultError.value = ''
  destroyAllCharts()
}

function destroyAllCharts() {
  ;[
    tbEntropyChart, tbObjectiveChart, tbLossPieChart,
    tbParetoChart, tbGanttChart, tbTimeSeriesChart,
    blEntropyChart, blObjectiveChart, blLossPieChart,
    blParetoChart, blGanttChart, blLossBarChart,
  ].forEach(c => { if (c) c.dispose() })
  tbEntropyChart = tbObjectiveChart = tbLossPieChart = null
  tbParetoChart = tbGanttChart = tbTimeSeriesChart = null
  blEntropyChart = blObjectiveChart = blLossPieChart = null
  blParetoChart = blGanttChart = blLossBarChart = null
}

function fmtNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  const num = Number(value)
  if (!Number.isFinite(num)) return '--'
  return num.toFixed(digits)
}

const COLOR_PALETTE = [
  '#5b8def', '#22c55e', '#f97316', '#a855f7', '#ec4899',
  '#14b8a6', '#facc15', '#06b6d4', '#84cc16', '#ef4444',
  '#6366f1', '#0ea5e9', '#f59e0b', '#10b981', '#8b5cf6'
]

function getColor(i) { return COLOR_PALETTE[i % COLOR_PALETTE.length] }

function initChart(el, chartRef) {
  if (!el || !el.isConnected) return null
  if (chartRef) { chartRef.dispose() }
  return echarts.init(el)
}

// ── 提交 ──
async function submitOptimize() {
  if (!canSubmit.value) return
  if (!form.apiKey.trim()) {
    proxy.$modal.msgError('请输入接口 API Key')
    return
  }

  const requestToken = Date.now()
  resultError.value = ''
  destroyAllCharts()
  submitting.value = true

  try {
    if (activeTab.value === 'trunk-branch') {
      tbResult.value = null
      const { canals, topology } = collectTrunkSubtree()
      const payload = buildTrunkPayload(canals, topology)
      const data = await runTrunkBranchOptimize(payload, form.apiKey.trim())
      if (requestToken !== requestToken) return
      tbResult.value = data
      await nextTick()
      renderTrunkBranchCharts()
    } else {
      blResult.value = null
      const { canals, topology } = collectBranchSubtree()
      const payload = buildBranchPayload(canals, topology)
      const data = await runBranchLateralOptimize(payload, form.apiKey.trim())
      if (requestToken !== requestToken) return
      blResult.value = data
      await nextTick()
      renderBranchLateralCharts()
    }
    proxy.$modal.msgSuccess('优化完成')
  } catch (err) {
    resultError.value = err?.message || '优化失败'
    proxy.$modal?.msgError?.(resultError.value)
  } finally {
    submitting.value = false
  }
}

function buildTrunkPayload(canals, topology) {
  return {
    mode: 'trunk-branch',
    canals: canals.map(c => ({
      canal_id: c.canal_id,
      canal_name: c.canal_name || null,
      level: c.level,
      length: c.length,
      design_flow: c.design_flow,
      design_depth: 0.0,
      top_width: 0.0,
      bottom_width: c.bottom_width,
      slope: c.slope,
      side_slope: c.side_slope,
      roughness: c.roughness,
      gate_height: 0.0,
      gate_width: 0.0,
      min_gate_opening: 0.0,
      max_gate_opening: 0.0,
      water_demand: c.water_demand,
      parent_id: c.parent_id,
    })),
    topology: topology.map(t => ({ canal_id: t.canal_id, parent_id: t.parent_id })),
    trunk_canal_id: form.trunkCanalId,
    t_max: form.tb_tMax,
    flow_ratio_min: form.tb_flowRatioMin,
    flow_ratio_max: form.tb_flowRatioMax,
    pop_size: form.tb_popSize,
    n_gen: form.tb_nGen,
    seed: form.tb_seed,
    permeability_index: form.tb_permIndexM,
    permeability_coefficient: form.tb_permCoefA,
    pref_weight_time: form.tb_prefTime,
    pref_weight_loss: form.tb_prefLoss,
    pref_weight_flow_var: form.tb_prefFlowVar,
    alpha: form.tb_alpha,
  }
}

function buildBranchPayload(canals, topology) {
  return {
    mode: 'branch-lateral',
    canals: canals.map(c => ({
      canal_id: c.canal_id,
      canal_name: c.canal_name || null,
      level: c.level,
      length: c.length,
      design_flow: c.design_flow,
      design_depth: 0.0,
      top_width: 0.0,
      bottom_width: c.bottom_width,
      slope: c.slope,
      side_slope: c.side_slope,
      roughness: c.roughness,
      gate_height: 0.0,
      gate_width: 0.0,
      min_gate_opening: 0.0,
      max_gate_opening: 0.0,
      water_demand: c.water_demand,
      parent_id: c.parent_id,
    })),
    topology: topology.map(t => ({ canal_id: t.canal_id, parent_id: t.parent_id })),
    branch_canal_id: form.branchCanalId,
    t_max: form.bl_tMax,
    flow_ratio_min: form.bl_flowRatioMin,
    flow_ratio_max: form.bl_flowRatioMax,
    min_groups: form.bl_minGroups,
    max_groups: form.bl_maxGroups,
    pop_size: form.bl_popSize,
    n_gen: form.bl_nGen,
    seed: form.bl_seed,
    permeability_index: form.bl_permIndexM,
    permeability_coefficient: form.bl_permCoefA,
    pref_weight_time: form.bl_prefTime,
    pref_weight_loss: form.bl_prefLoss,
    pref_weight_flow_var: form.bl_prefFlowVar,
    alpha: form.bl_alpha,
  }
}

// ================================================================
// 干支优化图表渲染
// ================================================================
function renderTrunkBranchCharts() {
  renderTbEntropy()
  renderTbObjective()
  renderTbLossPie()
  renderTbPareto()
  renderTbGantt()
  renderTbTimeSeries()
  setTimeout(() => window.dispatchEvent(new Event('resize')), 50)
}

function renderTbEntropy() {
  tbEntropyChart = initChart(tbEntropyRef.value, tbEntropyChart)
  if (!tbEntropyChart) return
  const w = tbResult.value?.summary?.entropy_weights || {}
  const data = [
    { name: 'F1 输水时间', value: Number(w.F1_time || 0) },
    { name: 'F2 渗漏损失', value: Number(w.F2_loss || 0) },
    { name: 'F3 流量波动', value: Number(w.F3_flow_var || 0) },
  ]
  tbEntropyChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}<br/>权重 {c} ({d}%)' },
    legend: { bottom: 0, textStyle: { fontSize: 12 } },
    series: [{
      type: 'pie', radius: ['45%', '70%'], center: ['50%', '45%'],
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { formatter: '{b}\n{d}%', fontSize: 11 },
      data, color: ['#5b8def', '#ef4444', '#f59e0b']
    }]
  })
}

function renderTbObjective() {
  tbObjectiveChart = initChart(tbObjectiveRef.value, tbObjectiveChart)
  if (!tbObjectiveChart) return
  const o = tbResult.value?.summary?.objective_values || {}
  const vals = [Number(o.F1_total_time_h || 0), Number(o.F2_total_loss_m3 || 0), Number(o.F3_flow_var || 0)]
  const mx = Math.max(...vals, 1)
  tbObjectiveChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { top: 30, left: 50, right: 30, bottom: 30 },
    xAxis: { type: 'category', data: ['F1 时间', 'F2 损失', 'F3 波动'], axisLabel: { fontSize: 12 } },
    yAxis: { type: 'value', name: '相对值', axisLabel: { fontSize: 11 } },
    series: [{
      type: 'bar', barWidth: '50%',
      data: [
        { value: vals[0] / mx, itemStyle: { color: '#5b8def' } },
        { value: vals[1] / mx, itemStyle: { color: '#ef4444' } },
        { value: vals[2] / mx, itemStyle: { color: '#f59e0b' } },
      ],
      label: { show: true, position: 'top', formatter: ({ value }) => value.toFixed(2) }
    }]
  })
}

function renderTbLossPie() {
  tbLossPieChart = initChart(tbLossPieRef.value, tbLossPieChart)
  if (!tbLossPieChart) return
  const s = tbResult.value?.topsis_summary || {}
  const data = [
    { name: '干渠损失', value: Number(s.trunk_loss_m3 || 0) },
    { name: '支渠损失', value: Number(s.branch_loss_m3 || 0) },
  ]
  tbLossPieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}<br/>{c} m³ ({d}%)' },
    legend: { bottom: 0, textStyle: { fontSize: 12 } },
    series: [{
      type: 'pie', radius: ['25%', '70%'], center: ['50%', '45%'],
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { formatter: '{b}\n{d}%', fontSize: 11 },
      data, color: ['#5b8def', '#22c55e']
    }]
  })
}

function renderTbPareto() {
  tbParetoChart = initChart(tbParetoRef.value, tbParetoChart)
  if (!tbParetoChart) return
  const data = tbResult.value?.pareto || []
  if (!data.length) return
  const option = {
    title: { text: 'Pareto 前沿（3D 散点）', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'item', formatter: (p) => {
      const d = p.data
      return `F1=${d.value[0].toFixed(2)} h<br/>F2=${d.value[1].toFixed(2)} m³<br/>F3=${d.value[2].toFixed(4)}<br/>score=${d.value[3].toFixed(4)}${d.value[4] ? '<br/>★ TOPSIS 优选' : ''}`
    }},
    visualMap: {
      show: true, dimension: 3,
      min: Math.min(...data.map(d => d.score)),
      max: Math.max(...data.map(d => d.score)),
      orient: 'vertical', right: 10, top: 'center', calculable: true,
      text: ['score', ''],
      inRange: { color: ['#bfdfd2', '#53999d', '#ecb66b', '#ec8e5a'] }
    },
    xAxis3D: { name: 'F1: 输水时间 (h)', type: 'value' },
    yAxis3D: { name: 'F2: 渗漏损失 (m³)', type: 'value' },
    zAxis3D: { name: 'F3: 流量波动', type: 'value' },
    grid3D: {
      boxWidth: 110, boxDepth: 110,
      viewControl: { projection: 'perspective', alpha: 20, beta: 30 },
      light: { main: { intensity: 1.2 }, ambient: { intensity: 0.3 } }
    },
    series: [{
      type: 'scatter3D', symbolSize: 12,
      data: data.map(d => ({
        value: [d.F1, d.F2, d.F3, d.score, d.selected],
        itemStyle: d.selected ? { color: '#ec8e5a', borderColor: '#fff', borderWidth: 2 } : undefined
      }))
    }]
  }
  if (data.some(d => d.selected)) {
    option.series.push({
      type: 'scatter3D', symbolSize: 26, symbol: 'star',
      data: data.filter(d => d.selected).map(d => ({ value: [d.F1, d.F2, d.F3, d.score, true] })),
      itemStyle: { color: '#ec8e5a' }
    })
  }
  tbParetoChart.setOption(option)
}

function renderTbGantt() {
  tbGanttChart = initChart(tbGanttRef.value, tbGanttChart)
  if (!tbGanttChart) return
  const branches = tbResult.value?.branches || []
  const trunk = tbResult.value?.trunk_canal || {}
  const rows = []
  rows.push({ name: '干渠 ' + (tbResult.value?.summary?.trunk_canal_id || ''), isTrunk: true, t_start: 0, duration: Number(trunk.t_max_h || 0) })
  branches.forEach(b => {
    rows.push({ name: '支渠 ' + b.name, isBranch: true, t_start: Number(b.t_start_h || 0), duration: Number(b.duration_h || 0) })
  })
  const yCategories = rows.map(r => r.name)
  const series = rows.map((r, i) => ({
    name: r.name, type: 'custom',
    renderItem: (params, api) => {
      const x0 = api.coord([r.t_start, i])[0]
      const x1 = api.coord([r.t_start + r.duration, i])[0]
      const y = api.coord([0, i])[1]
      const height = api.size([0, 1])[1] * 0.55
      return {
        type: 'rect',
        shape: { x: x0, y: y - height / 2, width: Math.max(x1 - x0, 1), height },
        style: { fill: r.isTrunk ? '#0f172a' : '#5b8def', stroke: '#fff', lineWidth: 1 }
      }
    },
    encode: { x: [0, 1], y: 0 },
    data: [[r.t_start, r.duration, i]]
  }))
  tbGanttChart.setOption({
    tooltip: { trigger: 'item', formatter: (p) => {
      const r = rows[p.dataIndex]
      return `<b>${r.name}</b><br/>开始 ${fmtNumber(r.t_start, 2)} h · 持续 ${fmtNumber(r.duration, 2)} h`
    }},
    grid: { top: 30, left: 120, right: 30, bottom: 40 },
    xAxis: { type: 'value', name: '时间 (h)', nameLocation: 'middle', nameGap: 25 },
    yAxis: { type: 'category', data: yCategories, axisLabel: { fontSize: 11 } },
    dataZoom: [{ type: 'inside', xAxisIndex: 0 }, { type: 'slider', xAxisIndex: 0, height: 18, bottom: 5 }],
    series
  })
}

function renderTbTimeSeries() {
  tbTimeSeriesChart = initChart(tbTimeSeriesRef.value, tbTimeSeriesChart)
  if (!tbTimeSeriesChart) return
  const ts = tbResult.value?.time_series || []
  tbTimeSeriesChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0, data: ['Q (m³/s)', 'H (m)'], textStyle: { fontSize: 12 } },
    grid: { top: 36, left: 60, right: 60, bottom: 50 },
    xAxis: {
      type: 'category', data: ts.map(p => p.t_h), name: '时间 (h)',
      nameLocation: 'middle', nameGap: 25,
      axisLabel: { interval: Math.max(0, Math.floor(ts.length / 12) - 1) }
    },
    yAxis: [
      { type: 'value', name: 'Q (m³/s)', position: 'left', nameTextStyle: { fontSize: 11 } },
      { type: 'value', name: 'H (m)', position: 'right', nameTextStyle: { fontSize: 11 } }
    ],
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 5 }],
    series: [
      { name: 'Q (m³/s)', type: 'line', smooth: false, symbol: 'none', step: 'end',
        lineStyle: { width: 2, color: '#5b8def' },
        areaStyle: { color: 'rgba(91,141,239,0.18)' },
        data: ts.map(p => p.Q_m3s) },
      { name: 'H (m)', type: 'line', smooth: false, symbol: 'none',
        yAxisIndex: 1, lineStyle: { width: 2, color: '#22c55e' },
        data: ts.map(p => p.H_m) },
    ]
  })
}

// ================================================================
// 支斗轮续灌图表渲染
// ================================================================
function renderBranchLateralCharts() {
  renderBlEntropy()
  renderBlObjective()
  renderBlLossPie()
  renderBlPareto()
  renderBlGantt()
  renderBlLossBar()
  setTimeout(() => window.dispatchEvent(new Event('resize')), 50)
}

function renderBlEntropy() {
  blEntropyChart = initChart(blEntropyRef.value, blEntropyChart)
  if (!blEntropyChart) return
  const w = blResult.value?.summary?.entropy_weights || {}
  const data = [
    { name: 'F1 输水时间', value: Number(w.F1_time || 0) },
    { name: 'F2 渗漏损失', value: Number(w.F2_loss || 0) },
    { name: 'F3 时间差异', value: Number(w.F3_flow_var || 0) },
  ]
  blEntropyChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}<br/>权重 {c} ({d}%)' },
    legend: { bottom: 0, textStyle: { fontSize: 12 } },
    series: [{
      type: 'pie', radius: ['45%', '70%'], center: ['50%', '45%'],
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { formatter: '{b}\n{d}%', fontSize: 11 },
      data, color: ['#5b8def', '#ef4444', '#f59e0b']
    }]
  })
}

function renderBlObjective() {
  blObjectiveChart = initChart(blObjectiveRef.value, blObjectiveChart)
  if (!blObjectiveChart) return
  const o = blResult.value?.summary?.objective_values || {}
  const vals = [Number(o.F1_total_loss_m3 || 0), Number(o.F2_flow_diff || 0), Number(o.F3_time_diff || 0)]
  const mx = Math.max(...vals, 1)
  blObjectiveChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { top: 30, left: 50, right: 30, bottom: 30 },
    xAxis: { type: 'category', data: ['F1 损失', 'F2 流量差', 'F3 时间差'], axisLabel: { fontSize: 12 } },
    yAxis: { type: 'value', name: '相对值', axisLabel: { fontSize: 11 } },
    series: [{
      type: 'bar', barWidth: '50%',
      data: [
        { value: vals[0] / mx, itemStyle: { color: '#5b8def' } },
        { value: vals[1] / mx, itemStyle: { color: '#ef4444' } },
        { value: vals[2] / mx, itemStyle: { color: '#f59e0b' } },
      ],
      label: { show: true, position: 'top', formatter: ({ value }) => value.toFixed(2) }
    }]
  })
}

function renderBlLossPie() {
  blLossPieChart = initChart(blLossPieRef.value, blLossPieChart)
  if (!blLossPieChart) return
  const s = blResult.value?.topsis_summary || {}
  const data = [
    { name: '支渠损失', value: Number(s.branch_loss_m3 || 0) },
    { name: '斗渠损失', value: Number(s.lateral_loss_m3 || 0) },
  ]
  blLossPieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}<br/>{c} m³ ({d}%)' },
    legend: { bottom: 0, textStyle: { fontSize: 12 } },
    series: [{
      type: 'pie', radius: ['25%', '70%'], center: ['50%', '45%'],
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { formatter: '{b}\n{d}%', fontSize: 11 },
      data, color: ['#22c55e', '#f97316']
    }]
  })
}

function renderBlPareto() {
  blParetoChart = initChart(blParetoRef.value, blParetoChart)
  if (!blParetoChart) return
  const data = blResult.value?.pareto || []
  if (!data.length) return
  const option = {
    title: { text: 'Pareto 前沿（3D 散点）', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'item', formatter: (p) => {
      const d = p.data
      return `F1=${d.value[0].toFixed(2)} m³<br/>F2=${d.value[1].toFixed(4)}<br/>F3=${d.value[2].toFixed(3)} h<br/>score=${d.value[3].toFixed(4)}${d.value[4] ? '<br/>★ TOPSIS 优选' : ''}`
    }},
    visualMap: {
      show: true, dimension: 3,
      min: Math.min(...data.map(d => d.score)),
      max: Math.max(...data.map(d => d.score)),
      orient: 'vertical', right: 10, top: 'center', calculable: true,
      text: ['score', ''],
      inRange: { color: ['#bfdfd2', '#53999d', '#ecb66b', '#ec8e5a'] }
    },
    xAxis3D: { name: 'F1: 输水损失 (m³)', type: 'value' },
    yAxis3D: { name: 'F2: 流量差异', type: 'value' },
    zAxis3D: { name: 'F3: 时间差异 (h)', type: 'value' },
    grid3D: {
      boxWidth: 110, boxDepth: 110,
      viewControl: { projection: 'perspective', alpha: 20, beta: 30 },
      light: { main: { intensity: 1.2 }, ambient: { intensity: 0.3 } }
    },
    series: [{
      type: 'scatter3D', symbolSize: 12,
      data: data.map(d => ({
        value: [d.F1, d.F2, d.F3, d.score, d.selected],
        itemStyle: d.selected ? { color: '#ec8e5a', borderColor: '#fff', borderWidth: 2 } : undefined
      }))
    }]
  }
  if (data.some(d => d.selected)) {
    option.series.push({
      type: 'scatter3D', symbolSize: 26, symbol: 'star',
      data: data.filter(d => d.selected).map(d => ({ value: [d.F1, d.F2, d.F3, d.score, true] })),
      itemStyle: { color: '#ec8e5a' }
    })
  }
  blParetoChart.setOption(option)
}

function renderBlGantt() {
  blGanttChart = initChart(blGanttRef.value, blGanttChart)
  if (!blGanttChart) return
  const groups = blResult.value?.groups || []
  const laterals = blResult.value?.laterals || []
  const rows = []
  groups.forEach(g => {
    rows.push({ name: `G${g.group} 轮灌组`, isGroup: true, t_start: Number(g.start_h || 0), duration: Number(g.duration_h || 0) })
    const gLats = laterals.filter(l => l.group === g.group)
    gLats.forEach(l => {
      rows.push({ name: `  · ${l.name || l.Name}`, isLateral: true, t_start: Number(g.start_h || 0), duration: Number(l.duration_h || 0) })
    })
  })
  const yCategories = rows.map(r => r.name)
  const GROUP_COLORS = ['#22c55e', '#f59e0b', '#5b8def', '#ec4899', '#a855f7', '#14b8a6']
  const series = rows.map((r, i) => ({
    name: r.name, type: 'custom',
    renderItem: (params, api) => {
      const x0 = api.coord([r.t_start, i])[0]
      const x1 = api.coord([r.t_start + r.duration, i])[0]
      const y = api.coord([0, i])[1]
      const height = api.size([0, 1])[1] * (r.isGroup ? 0.6 : 0.5)
      const color = r.isGroup ? GROUP_COLORS[(parseInt(r.name.slice(1)) - 1) % GROUP_COLORS.length] : '#94a3b8'
      return {
        type: 'rect',
        shape: { x: x0, y: y - height / 2, width: Math.max(x1 - x0, 1), height },
        style: { fill: color, stroke: '#fff', lineWidth: 1 }
      }
    },
    encode: { x: [0, 1], y: 0 },
    data: [[r.t_start, r.duration, i]]
  }))
  blGanttChart.setOption({
    tooltip: { trigger: 'item', formatter: (p) => {
      const r = rows[p.dataIndex]
      return `<b>${r.name}</b><br/>开始 ${fmtNumber(r.t_start, 2)} h · 持续 ${fmtNumber(r.duration, 2)} h`
    }},
    grid: { top: 30, left: 140, right: 30, bottom: 40 },
    xAxis: { type: 'value', name: '时间 (h)', nameLocation: 'middle', nameGap: 25 },
    yAxis: { type: 'category', data: yCategories, axisLabel: { fontSize: 11 } },
    dataZoom: [{ type: 'inside', xAxisIndex: 0 }, { type: 'slider', xAxisIndex: 0, height: 18, bottom: 5 }],
    series
  })
}

function renderBlLossBar() {
  blLossBarChart = initChart(blLossBarRef.value, blLossBarChart)
  if (!blLossBarChart) return
  const laterals = blResult.value?.laterals || []
  laterals.sort((a, b) => {
    const na = a.name || a.Name || ''
    const nb = b.name || b.Name || ''
    const ma = na.match(/(\d+)$/)
    const mb = nb.match(/(\d+)$/)
    return (ma ? parseInt(ma[1]) : 0) - (mb ? parseInt(mb[1]) : 0)
  })
  const names = laterals.map(l => l.name || l.Name)
  const losses = laterals.map(l => Number(l.loss_m3 || 0))
  const colors = laterals.map((_, i) => COLOR_PALETTE[i % COLOR_PALETTE.length])
  blLossBarChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { top: 30, left: 60, right: 30, bottom: 60 },
    xAxis: { type: 'category', data: names, axisLabel: { fontSize: 11, rotate: 30 } },
    yAxis: { type: 'value', name: 'm³', nameTextStyle: { fontSize: 11 } },
    series: [{
      type: 'bar', data: laterals.map((l, i) => ({
        value: Number(l.loss_m3 || 0),
        itemStyle: { color: colors[i], borderRadius: [4, 4, 0, 0] }
      })),
      label: { show: true, position: 'top', fontSize: 10, formatter: ({ value }) => fmtNumber(value, 0) }
    }]
  })
}

watch(activeResult, async (val) => {
  if (!val) return
  await nextTick()
  if (activeTab.value === 'trunk-branch') renderTrunkBranchCharts()
  else renderBranchLateralCharts()
})

window.addEventListener('resize', () => {
  ;[
    tbEntropyChart, tbObjectiveChart, tbLossPieChart,
    tbParetoChart, tbGanttChart, tbTimeSeriesChart,
    blEntropyChart, blObjectiveChart, blLossPieChart,
    blParetoChart, blGanttChart, blLossBarChart,
  ].forEach(c => { if (c) c.resize() })
})

onUnmounted(() => { destroyAllCharts() })
</script>

<style scoped>
.canal-optimize-page { padding-bottom: 28px; }
.agri-page__siblings { display: flex; gap: 12px; margin-top: 14px; flex-wrap: wrap; }
.sibling-link { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 999px; background: var(--surface-soft-bg); border: 1px solid var(--hairline-color); color: var(--text-primary); font-size: 0.867em; text-decoration: none; transition: all 0.2s ease; }
.sibling-link:hover { background: var(--el-color-primary-light-9); border-color: var(--el-color-primary-light-5); color: var(--el-color-primary); }
.page-layout { align-items: stretch; }
.db-row { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; }
.muted-text { color: var(--text-secondary); font-size: 12px; margin-left: 8px; }
.divider-soft { height: 1px; margin: 6px 0 14px; background: linear-gradient(90deg, transparent, rgba(14, 165, 233, 0.25), transparent); }
.subtree-preview { padding: 8px 12px; border-radius: 8px; background: rgba(14, 165, 233, 0.06); border: 1px solid rgba(14, 165, 233, 0.15); }
.subtree-preview__label { font-size: 12px; color: var(--text-secondary); margin-bottom: 6px; }
.subtree-preview__levels { display: flex; flex-wrap: wrap; gap: 4px; }
.mr6 { margin-right: 6px; }
.mode-tabs :deep(.el-tabs__header) { margin-bottom: 0; }
.mode-tabs :deep(.el-tabs__nav-wrap::after) { display: none; }
.mt8 { margin-top: 8px; }
.config-col { display: flex; min-width: 0; }
.config-col .config-card { display: flex; flex-direction: column; flex: 1 1 auto; width: 100%; }
.config-col .config-card :deep(.el-card__body) { flex: 1 1 auto; display: flex; flex-direction: column; min-height: 0; }
.config-body { flex: 1 1 auto; min-height: 0; overflow-y: auto; padding-right: 4px; }
.result-col { display: flex; flex-direction: column; min-width: 0; }
.config-card, .chart-card { border-radius: 20px; border: 1px solid var(--hairline-color); box-shadow: var(--content-shadow-soft); overflow: hidden; }
.card-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.card-title { font-size: 18px; font-weight: 650; color: var(--text-primary); }
.card-desc { margin-top: 6px; color: var(--text-secondary); line-height: 1.6; }
.chart-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.chart-title { font-size: 1em; font-weight: 650; color: var(--text-primary); }
.chart-sub { display: block; margin-top: 4px; font-size: 0.8em; color: var(--text-secondary); }
.chart-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.mb12 { margin-bottom: 12px; }
.mt16 { margin-top: 16px; }
.opt-form :deep(.el-form-item) { margin-bottom: 14px; }
.opt-form :deep(.el-form-item__label) { font-size: 0.8em; color: var(--text-regular); padding: 0 0 4px; line-height: 1.3; font-weight: 500; }
.action-row { display: flex; gap: 10px; margin-top: 12px; }
.action-primary { flex: 1; }
.action-secondary { flex: 0 0 auto; }
.placeholder { padding: 56px 20px; text-align: center; background: var(--surface-soft-bg); border-radius: 20px; border: 1px dashed var(--hairline-color); }
.placeholder-title { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.placeholder-desc { margin-top: 10px; font-size: 0.867em; line-height: 1.7; color: var(--text-secondary); max-width: 600px; margin-left: auto; margin-right: auto; }
.chart { width: 100%; height: 320px; }
.chart-tall { height: 420px; }
.chart-row { margin-top: 16px; }
.chart-row + .chart-row { margin-top: 16px; }
.kpi-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-top: 16px; }
.kpi-box { padding: 18px 20px; border-radius: 18px; background: var(--surface-bg); border: 1px solid var(--hairline-color); box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05); overflow: hidden; }
.kpi-label { font-size: 0.867em; color: var(--text-secondary); font-weight: 500; }
.kpi-value { margin-top: 8px; font-size: 28px; font-weight: 700; color: var(--text-primary); line-height: 1.1; }
.kpi-unit { margin-left: 4px; font-size: 0.933em; font-weight: 500; color: var(--text-secondary); }
.kpi-foot { margin-top: 8px; font-size: 12px; color: var(--text-secondary); line-height: 1.5; }
.error-box { padding: 16px; }
@media (max-width: 1200px) { .chart { height: 300px; } .chart-tall { height: 380px; } }
@media (max-width: 992px) { .config-col { display: block; } .config-body { max-height: none; overflow: visible; } }
@media (max-width: 768px) { .kpi-value { font-size: 22px; } .chart { height: 280px; } .chart-tall { height: 340px; } }
</style>
