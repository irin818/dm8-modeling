# 模块依赖方向与 Stage 对照

```text
workspace ──┐
data ───────┼─→ preprocessing ─→ datasets ←─ features
            │                       │
            └───────────────────────┼─→ rf / evaluation diagnostics
                                    └─→ models ─→ experiments ─→ cli
                                         │             │
                                         └─→ evaluation.metrics
io ←────────────────────────────────────── experiments / Stage runners
```

实际依赖规则：

1. `data` 只读已保存事实，不能导入 `models`、`cli` 或修改原文件。
2. `features` 只构造刺激特征，不训练响应模型；`datasets` 引用 `data` 和 `features`，保留来源索引。
3. `preprocessing` 的尺度来自训练段；在线因果候选可使用当前/过去信号，必须显式标记。
4. `rf` 的 STA/零模型估计与 `models` 的预测任务分开。模型可调用 `evaluation.metrics` 的纯指标函数；`evaluation` 的核心指标不导入模型。需要**训练**源 fly 模型的 LOFO 位于 `experiments.transfer`，旧 `evaluation.cross_fly` 只是兼容导入。
5. `experiments` 管理配置、Stage 顺序和模型矩阵；`cli` 只解析参数并调用它，不把算法复制到命令入口。
6. `io` 保存派生元数据。原始 `Dm8_module/`、`simulate/` 无写入路径。

| Stage | 源码 owner | 主要输出 |
|---|---|---|
| 01 | `workspace.paths`、`workspace.inventory` | 文件清单 |
| 02 | `data.stimulus` | `StimulusData` |
| 03 | `data.response`、`data.clocks` | `ResponseData`、`ClockData` |
| 04 | `data.alignment` | `AlignedSession` |
| 05 | `preprocessing.baseline/fluorescence/normalization` | `ProcessedResponse`/scaler |
| 06 | `features.lagged/temporal_basis`、`datasets.individual/splits` | `IndividualDataset` |
| 07 | `datasets.integrated` | `IntegratedDataset` |
| 08 | `rf.sta/null_tests`、`evaluation.reliability` | RF/可靠性 |
| 09 | `models.linear`、`models.neural.compact_cnn`（历史） | 独立预测 |
| 10 | `models.population`、`datasets.population`、`experiments.transfer` | 共享/分层/群体模型 |
| 11 | `evaluation.metrics/comparison` | fly-aware 对比 |
| 12 | `experiments.workflow`、`io.stage_manifest` | 最终 receipt |

未实现的 smooth STRF、LN、共享 CNN/TCN 只在 [模型地图](../../modeling_pipeline/MODELING_MAP.md) 标为 PLANNED，不创建没有行为的空实现。旧路径到新路径见 [迁移图](../../REORGANIZATION_MAP.md)。
