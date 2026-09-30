# 项目结构：从实验事实到最终解释

第一次阅读请先看 [流程总览](modeling_pipeline/README.md)，再看当前的 [Phase 6.1 结果](docs/PHASE6_1_REPORT.md)。`modeling_pipeline/stage_01_*` 到 `stage_12_*` 是可重播的 Phase 1–5 历史流程；`modeling_pipeline/phase_06/` 是独立的 ACTIVE TRAIN-only RF 流程。深入源码前先看 [源码地图](src/dm8_modeling/README.md)。

| 目录 | 唯一职责 | 是否为原始实验数据 | 是否提交 Git |
|---|---|---|---|
| `simulate/` | 刺激生成、打包、播放、marker-lock 的实验工程副本 | 是，实验来源；只读 | 否 |
| `Dm8_module/` | 五只 fly 的原始记录、刺激包、TTL、Results.csv | 是；只读 | 否 |
| `modeling_pipeline/` | 历史 Stage 01→12 与独立的 Phase 6.1 RF 入口 | 否 | 是 |
| `src/dm8_modeling/` | 可复用的读取、预处理、特征、模型与评价实现 | 否 | 是 |
| `datasets/` | 三类派生数据集的定义与生成 manifest，不放原始文件 | 否 | README 是；生成 manifest 忽略 |
| `configs/` | 可调整的工作流与实验参数 | 否 | 是 |
| `outputs/` | 运行结果、逐阶段 manifest、旧实验保留结果 | 否 | 否 |
| `tests/` | 数据契约、因果性、模型复算与回归测试 | 否 | 是 |
| `scripts/` | 仍有独立用途的审计/验证工具及历史脚本 | 否 | 是 |
| `docs/` | 科研证据、历史阶段报告与最终结论 | 否 | 是 |

`simulate/`、`Dm8_module/` 的位置和内容不变。`datasets/` 只保存派生对象的说明和元数据；真正的 `IndividualDataset`、`IntegratedDataset`、`PopulationDataset` 类型在 `src/dm8_modeling/datasets/`。`outputs/` 原有 `first_pass/`、`ridge_raw/`、`pixel_raw/`、`cnn_comparison/` 等未迁移或删除；新增 `stage_01_*` 至 `stage_12_*` 对应流程结果。旧到新映射见 [REORGANIZATION_MAP](REORGANIZATION_MAP.md)。

当前 Phase 6.1 输出写入忽略的 `outputs/phase_06/response/`、`reliability/` 和 `alignment/`，配置在 `configs/phase6_rf.json`。使用 Stage 07 已验证的前序 manifest，不运行 Stage 09/10 的旧预测模型：

```bash
OPENBLAS_NUM_THREADS=2 .venv/bin/python modeling_pipeline/phase_06/run.py --workspace-root .
```

运行整条流程：

```bash
cd /Users/irin/Documents/dm8_modeling
.venv/bin/dm8-model pipeline run --workspace-root .
```

单独运行 Stage 07 前需要 Stage 06 的有效 manifest：

```bash
.venv/bin/dm8-model pipeline stage 7 --workspace-root .
```

已完成 Stage 06 时可从 Stage 07 接着运行：

```bash
.venv/bin/dm8-model pipeline run --from-stage 7 --workspace-root .
```

运行不会移动或覆盖原始实验文件。任何前序 manifest、配置或其声明的输入/输出哈希不匹配时，下一阶段会明确失败。
