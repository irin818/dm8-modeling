# 重构迁移图：旧入口到工作流与源码 owner

本次是 **STRUCTURAL_REFACTOR**。`simulate/` 和 `Dm8_module/` 始终保持原位置和只读；旧 `outputs/` 也保持原位置，避免旧报告与 replay 路径失效。新阅读入口是 `modeling_pipeline/README.md`，新结果写 `outputs/stage_01_*` 至 `outputs/stage_12_*`。兼容 wrapper 仅转发，不保留第二套核心实现。

| 旧路径/职责 | 新 canonical owner | 兼容状态 / Stage |
|---|---|---|
| `src/dm8_modeling/workspace.py` | `workspace/paths.py`、`workspace/inventory.py` | wrapper 保留；01 |
| `src/dm8_modeling/data/` 中的混合 loader | `data/stimulus.py`、`response.py`、`clocks.py`、`alignment.py`、`schema.py` | 数据子模块直接使用；02–04 |
| `src/dm8_modeling/model.py` 中的 lagged feature | `features/lagged.py` | wrapper 保留；06 |
| `model.py` 中的 EMA residual | `preprocessing/baseline.py`、`fluorescence.py` | wrapper 保留；05 |
| `model.py` 中的 STA/rank-one | `rf/sta.py` | wrapper 保留；08 |
| `model.py` 中的旧 scoring helper | `evaluation/legacy_metrics.py` | wrapper 保留；09/11 |
| `src/dm8_modeling/ridge.py` 的时间 bin 特征 | `features/temporal_basis.py` | wrapper 保留；06/09 |
| `ridge.py` 的旧 Ridge STRF | `models/linear/binned_strf.py` | wrapper 保留；09 |
| `src/dm8_modeling/pixel.py` 的像素预测器 | `models/linear/pixel_temporal.py` | wrapper 保留；09 |
| `pixel.py` 的 circular-shift / FDR | `rf/null_tests.py` | wrapper 保留；08/11 |
| `src/dm8_modeling/cnn.py` | `models/neural/compact_cnn.py` | wrapper 保留；旧 CNN 对照 |
| `src/dm8_modeling/pipeline.py` | `datasets/legacy_model_dataset.py` | wrapper 保留；旧 CLI |
| `src/dm8_modeling/splits.py` | `datasets/legacy_splits.py`；新全局 split 在 `datasets/splits.py` | wrapper 保留；06/07 |
| `src/dm8_modeling/evaluation/cross_fly.py` 中的模型训练 | `experiments/transfer.py` | wrapper 保留；10 |
| `src/dm8_modeling/audit.py` | `evaluation/audit.py`、`diagnostics.py`、`rf_quality.py` | wrapper 保留；03/08/11 |
| `src/dm8_modeling/cli.py` | `cli/__init__.py`、`legacy.py`、`pipeline.py`、`dataset.py` | `dm8-model` 保留旧命令并新增 workflow；01–12 |
| `src/dm8_modeling/phase5_cli.py` | `cli/dataset.py` | wrapper 保留；06–11 |
| `tests/test_model.py`、`test_cnn.py` | `tests/models/` | 同样的 unittest discovery |
| `tests/test_phase5.py`、`test_workspace_audit.py` | `tests/integration/` | 同样的 unittest discovery |

`src/dm8_modeling/predict_cli.py`、`cnn_cli.py`、`cnn_predict_cli.py` 保持历史入口以确保保存模型可以重播。`models/linear/individual.py` 和 `models/population/` 原本已有明确职责，本次保留其数学实现。计划中的 smooth STRF、LN、shared CNN/TCN 只在模型地图注明，没有创建空算法文件。

## 输出与脚本

| 旧结果 | 新 Stage 对应 | 处理 |
|---|---|---|
| `outputs/audit/`、`outputs/qc_verified/` | 01、03、08、11 | 原位保留，旧科研报告继续引用 |
| `outputs/first_pass/` | 08、09 | 原位保留，与重构回归比较 |
| `outputs/ridge_raw/`、`outputs/pixel_raw/` | 09 | 原位保留，模型 replay 不断链 |
| `outputs/cnn_comparison/` | 09 的历史神经网络对照 | 原位保留 |
| `outputs/experiments/phase5_first_round/` | 06–11 | 原位保留，Stage 09/10 各自产生新结果 |

`scripts/` 的 A/D 分类与保留原因见 [`scripts/README.md`](scripts/README.md)。当前没有脚本被删除、移动或归档：多份既有报告直接引用原路径，保持原位比增加 `scripts/archive/` 更安全。`docs/` 继续保存科研报告；流程教学移到 `modeling_pipeline/`，源码教学位于各一级模块 README，派生数据元数据在 `datasets/`。可调参数入口见 `configs/README.md`。

## 重构与科学结果边界

旧 Phase 1–4 的特征、模型和评价数学未作为本次重构对象修改。`data.stimulus` 从原配方读取更新数与网格大小，替代局部的 9000/225 常量；当前五次原配方均为 9000 × 15 × 15。EMA residual 复用统一 `preprocessing.baseline.causal_ema_baseline`。科学结果是否一致以 [`docs/REORGANIZATION_REPORT.md`](docs/REORGANIZATION_REPORT.md) 的重跑对照为准。
