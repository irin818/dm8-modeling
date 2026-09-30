# Phase 6.1：ACTIVE 响应重建与 TRAIN-only RF 诊断

本目录是当前研究入口；历史 `stage_01_*`–`stage_12_*` 保留原有运行与重播行为。Phase 6.1 **不拟合预测模型**。先验证 Stage 07 的源清单，再运行 6.1A 响应重建、6.1B RF 可靠性、6.1C 中心与对齐准入。新计算从 raw 数据只读重建，不使用 Stage 08 的旧 ROI 白名单，也不读取 TEST 响应作选择。

```bash
OPENBLAS_NUM_THREADS=2 .venv/bin/python modeling_pipeline/phase_06/run.py --workspace-root .
```

| 子阶段 | 输入 | 主要算法 | 输出 |
|---|---|---|---|
| A | raw Results、Zeiss TTL、Phase 5 `fold_a` TRAIN | raw + 分半离线 Li Gaussian + 两个 past-only residual | `outputs/phase_06/response/`：数组、raw SHA-256 provenance、逐 ROI 摘要、manifest |
| B | 同一批 TRAIN A/B 行和过去刺激特征 | reverse correlation、A→B 投影、shift null、BH-FDR、RF z-score | `outputs/phase_06/reliability/`：核 NPZ、逐候选指标、表示比较、manifest |
| C | B 的 TRAIN RF 与预设门槛 | 1D Gaussian 中心、split-half 位移、仅可靠 ROI 的中心对齐 | `outputs/phase_06/alignment/`：中心图、分类、均值 RF、相似度/Gate、manifest |

Phase 6 目前没有 `RF_RELIABLE` ROI；均值 RF 标记为缺失，不以零数组代表真实 RF。Gate A/B 不通过时停止 Phase 6.2。每个 manifest 保存声明输入/输出的 SHA-256 及 Git 提交。阅读顺序：[证据与假设](../../docs/PHASE6_ASSUMPTIONS.md) → [响应重建](../../docs/PHASE6_RESPONSE_RECONSTRUCTION.md) → [RF 可靠性与中心](../../docs/PHASE6_RF_RELIABILITY.md) → [运行报告](../../docs/PHASE6_1_REPORT.md) → `run.py` → `src/dm8_modeling/experiments/phase6.py`。
