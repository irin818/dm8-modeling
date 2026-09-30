# Dm8 神经视觉响应：描述性群体 RF

本项目使用五次已保存的 fly 白噪声实验记录，追踪数字刺激、设备时钟与 ROI 平均图像强度，构建**可解释的群体感受野（RF）描述**。最新结果是 [Phase 6.3 各 fly 共性/异质性与完整零模型](docs/PHASE6_3_FLY_POPULATION_VALIDATION.md)：负中心在五 fly 各自及群体的重新定位 null 下有探索性证据；环绕极性、位置与时间存在异质性。基础方法见 [Phase 6.2](docs/PHASE6_2_POPULATION_RF.md)。五只 fly 共用一条冻结刺激；`UV-15Hz` 是文件夹标签，不是实测光谱或辐照度。ROI 强度也未核实为正式校正后的 Dm8 钙响应。

## 从哪里开始

1. [项目结构](PROJECT_STRUCTURE.md)与[工作流](modeling_pipeline/README.md)：原始实验到群体 RF 的完整路径。
2. [Phase 6.3 报告](docs/PHASE6_3_FLY_POPULATION_VALIDATION.md)：五张独立报告、共识图、四箱轨迹、1000 次完整 null、稳定中心分层和 fly4 影响；[Phase 6.2](docs/PHASE6_2_POPULATION_RF.md)保留基础方法。
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
```

主图 1–5 的版本化副本在 [`docs/phase6_2_figures/`](docs/phase6_2_figures/)；完整逐 ROI、逐 fly、群体数组及来源 manifest 写到 Git 忽略的 `outputs/phase_06/population_rf/`。运行时间依机器而异；可用 `OPENBLAS_NUM_THREADS=2` 控制矩阵计算线程数。

Phase 6.3 的图、表和完整 null 分布副本在 [`docs/phase6_3_figures/`](docs/phase6_3_figures/) 与 [`docs/phase6_3_results/`](docs/phase6_3_results/)；本地计算写到 `outputs/phase_06/fly_population_validation/`。运行前与运行后[全局假设审计](docs/PHASE6_3_ASSUMPTION_AUDIT.md)保留方法边界。项目已完成 6.3 并停止，后续阶段由用户决定。

`Dm8_module/` 与 `simulate/` 是**只读实验来源**，不得编辑、移动或删除。`Results.csv` 的 `MeanN` 列是 ROI 图像平均强度。已保存的数字刺激矩阵与播放逻辑可核验数字命令，不等于实测视网膜刺激。每次新结果都应保留原始行号、时钟依据、source SHA-256 和分析配置。

## 当前项目边界

Phase 6.1 严格单 ROI 检验结果为 `0/236 RF_RELIABLE`；[Phase 6.1b 方法审计](docs/PHASE6_1B_RF_METHOD_AUDIT.md)没有改变这一点。Phase 6.2 回答的是**全记录下五只 fly 的描述性平均结构**，没有把同一数据当独立验证，也没有以 p 值筛选 ROI。历史 Pixel、Ridge、CNN、共享模型和预测型 LOFO 的结果保留在文档中；当前不训练新预测模型。
