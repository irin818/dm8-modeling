# Dm8 神经视觉响应：描述性群体 RF

本项目使用五次已保存的 fly 白噪声实验记录，追踪数字刺激、设备时钟与 ROI 平均图像强度，构建**可解释的群体感受野（RF）描述**。最新结果是 [Phase 6.5 Li 方法等价性审计](docs/PHASE6_5_LI_EQUIVALENCE_REPORT.md)：负中心跨方法稳健；弱环绕随方法改变，但当前数据不支持跨 fly 一致、可辨识的宽正环绕。历史 [Phase 6.4](docs/PHASE6_4_GAUSSIAN_DOG_TEST.md)、[Phase 6.3](docs/PHASE6_3_FLY_POPULATION_VALIDATION.md)与[Phase 6.2](docs/PHASE6_2_POPULATION_RF.md)保留为 `CURRENT_PIPELINE_BASELINE`。五只 fly 共用一条冻结刺激；`UV-15Hz` 是文件夹标签，不是实测光谱或辐照度。ROI 强度也未核实为正式校正后的 Dm8 钙响应。

## 从哪里开始

1. [项目结构](PROJECT_STRUCTURE.md)与[工作流](modeling_pipeline/README.md)：原始实验到群体 RF 的完整路径。
2. [Phase 6.5 报告](docs/PHASE6_5_LI_EQUIVALENCE_REPORT.md)：论文来源、当前代码流程、C0–C7 消融、40-lag、覆盖和 500 次最终 null；[Phase 6.4](docs/PHASE6_4_GAUSSIAN_DOG_TEST.md)保留历史模型比较，[Phase 6.3](docs/PHASE6_3_FLY_POPULATION_VALIDATION.md)保留五 fly 验证。
3. [历史模型结论](docs/HISTORICAL_MODELING_CONCLUSIONS.md)与[结果总表](docs/HISTORICAL_MODELING_RESULTS.csv)：旧预测模型的科学证据，代码已退役。
4. [清理记录](docs/PHASE6_2_CLEANUP_LOG.md)：删除范围、保留证据、原始数据完整性。

## 安装、验证与复算

需要 Python 3.11+，在仓库根目录：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m unittest discover -s tests -q
OPENBLAS_NUM_THREADS=2 .venv/bin/python modeling_pipeline/phase_06/run_population.py --workspace-root .
OPENBLAS_NUM_THREADS=2 .venv/bin/python modeling_pipeline/phase_06/run_validation.py --workspace-root .
OPENBLAS_NUM_THREADS=2 .venv/bin/python modeling_pipeline/phase_06/run_dog_test.py --workspace-root .
OPENBLAS_NUM_THREADS=2 .venv/bin/python modeling_pipeline/phase_06/run_li_equivalence_audit.py --workspace-root .
OPENBLAS_NUM_THREADS=2 .venv/bin/python modeling_pipeline/phase_06/run_li_equivalence_audit.py --workspace-root . --final-null
```

主图 1–5 的版本化副本在 [`docs/phase6_2_figures/`](docs/phase6_2_figures/)；完整逐 ROI、逐 fly、群体数组及来源 manifest 写到 Git 忽略的 `outputs/phase_06/population_rf/`。运行时间依机器而异；可用 `OPENBLAS_NUM_THREADS=2` 控制矩阵计算线程数。

Phase 6.3 的图、表和完整 null 分布副本在 [`docs/phase6_3_figures/`](docs/phase6_3_figures/) 与 [`docs/phase6_3_results/`](docs/phase6_3_results/)；本地计算写到 `outputs/phase_06/fly_population_validation/`。[Phase 6.4 的关键图表](docs/phase6_4_results/)只从冻结 Phase 6.3 图和 null 派生。[Phase 6.5 的表和图](docs/phase6_5_results/)单独保存，原始数据及旧阶段输出不覆盖。项目在 6.5 结束后停止，不自动进入预测模型。

`Dm8_module/` 与 `simulate/` 是**只读实验来源**，不得编辑、移动或删除。`Results.csv` 的 `MeanN` 列是 ROI 图像平均强度。已保存的数字刺激矩阵与播放逻辑可核验数字命令，不等于实测视网膜刺激。每次新结果都应保留原始行号、时钟依据、source SHA-256 和分析配置。

## 当前项目边界

Phase 6.1 严格单 ROI 检验结果为 `0/236 RF_RELIABLE`；[Phase 6.1b 方法审计](docs/PHASE6_1B_RF_METHOD_AUDIT.md)没有改变这一点。Phase 6.2 回答的是**全记录下五只 fly 的描述性平均结构**，没有把同一数据当独立验证，也没有以 p 值筛选 ROI。历史 Pixel、Ridge、CNN、共享模型和预测型 LOFO 的结果保留在文档中；当前不训练新预测模型。
