# Dm8 建模主线：先看工作流，再看模块

**当前研究入口**：[Phase 6.1 响应与 RF](phase_06/README.md)；下面的 Stage 01–12 是 Phase 1–5 **HISTORICAL** 流程，继续保留完整复算、旧模型重播和教学记录。Phase 6.1 以 Stage 07 的来源与分块为基础，单独做 TRAIN-only RF characterization，尚未训练新预测模型。[Phase 6.1 报告](../docs/PHASE6_1_REPORT.md) 给出 0/236 可靠 ROI 与 Gate 决策。

```text
simulate/ 的刺激设计与播放源码
  ↓
Dm8_module/ 的已保存刺激、Results.csv 与设备时钟
  ↓
01 来源审计 → 02 冻结刺激 → 03 ROI 强度与时钟 → 04 对齐
  ↓
05 响应表示 → 06 单 fly 数据集 → 07 多 fly 整合数据集
  ↓
08 RF 恢复 → 09 单 fly 预测模型 → 10 共享/分层/群体模型
  ↓
11 fly-aware 评价 → 12 最终科研解释
```

| Stage | 科学目的 | 输入 | 处理 | 输出 | 下一阶段 |
|---|---|---|---|---|---|
| [01 来源审计](stage_01_source_audit/README.md) | 确定文件来源 | `simulate/`、`Dm8_module/` | 逐文件清单与哈希 | 原始来源清单 | 02 |
| [02 冻结刺激](stage_02_stimulus/README.md) | 核验数字刺激 | recipe、realized NPZ | seed 与灰度映射检查 | `StimulusData` 摘要 | 03/04 |
| [03 响应与时钟](stage_03_response_and_clocks/README.md) | 明确 y 与时钟 | Results、DLP/Zeiss TTL、flip log | 完整性与单位检查 | `ResponseData`、`ClockData` 摘要 | 04 |
| [04 对齐](stage_04_alignment/README.md) | 建立因果时间对应 | 02+03 | 最近的已显示更新、payload 筛选 | `AlignedSession` 摘要 | 05 |
| [05 响应处理](stage_05_response_processing/README.md) | 固定目标含义与尺度 | 对齐 ROI 强度 | 因果候选、训练段标准化 | `ProcessedResponse` 摘要 | 06 |
| [06 单 fly 数据集](stage_06_individual_dataset/README.md) | 保留个体层级 | 五次对齐会话 | 因果特征、全局 split | 五个 `IndividualDataset` manifest | 07 |
| [07 整合数据集](stage_07_integrated_dataset/README.md) | 建立可追溯长表 | 五个单 fly 数据集 | 公共 X 索引、ROI/帧 provenance | `IntegratedDataset` manifest | 08/10 |
| [08 RF 恢复](stage_08_rf_recovery/README.md) | 训练段响应性诊断 | X、y、split | reverse correlation、shift null | RF/可靠性表 | 09 |
| [09 独立模型](stage_09_individual_models/README.md) | 建立可比预测基线 | 单 fly X/y | 单像素、Ridge | 模型参数与测试指标 | 10 |
| [10 群体模型](stage_10_population_models/README.md) | 检验跨 fly 共享计算 | 09 baseline + 多 fly 数据 | 共享/分层/低秩/群体/留一 fly | 完整模型矩阵 | 11 |
| [11 评价](stage_11_evaluation/README.md) | 保留 fly 层级比较 | 已保存指标 | 成对 ΔR²、跨折方向 | 评价摘要 | 12 |
| [12 最终分析](stage_12_final_analysis/README.md) | 把证据变成可讲结论 | 11 + 科研报告 | 核对停止条件 | 最终分析 manifest | 毕业设计 |

按每个 Stage 的统一阅读路径：**Stage README → Stage `run.py` → `src/dm8_modeling/<module>/README.md` → 源码 → `configs/` → `tests/` → `outputs/stage_XX_*/`**。逐对象的生产/消费关系见 [DATA_FLOW](DATA_FLOW.md)，模型层级见 [MODELING_MAP](MODELING_MAP.md)。Stage `run.py` 只编排源码 API 与保存摘要，不复制核心算法。

Stage 01 可以独立运行；其他阶段要求上一个 Stage 的 `stage_manifest.json` 完成且其声明的输入/输出哈希和工作流配置仍一致。`pipeline stage N` 不会偷偷运行 Stage 1…N−1；`pipeline run` 才按顺序执行。各 Stage 会重新从只读源构建必要的内存对象，且在 Stage README 标明，不依赖不可追溯的缓存。

```bash
cd /Users/irin/Documents/dm8_modeling
.venv/bin/dm8-model pipeline run --workspace-root .
.venv/bin/dm8-model pipeline stage 7 --workspace-root .
.venv/bin/dm8-model pipeline run --from-stage 7 --workspace-root .
```

所有旧输出保留原路径，新 Stage 输出写 `outputs/stage_XX_*/`。五只 fly 共享一条冻结随机序列；多 fly 增加生物重复响应，**不会**增加五倍独立刺激多样性。`Results.csv` 是原始 ROI 平均图像强度，不是已证实的 ΔF/F。旧晚段测试已被历史阶段查看，Stage 10/11 的两折是探索性时间验证。
