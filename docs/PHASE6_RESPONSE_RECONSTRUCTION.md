# Phase 6.1A：两条响应处理路径

Phase 6.1 只读取 `Results.csv` 的 `MeanN` 及 Zeiss frame-out 时间代理。原始 `F(t)` 永远是 provenance anchor。每个派生响应在 `outputs/phase_06/response/fly*_provenance.json` 记录源路径及 SHA-256、变换、参数、因果标记、科学用途和 TRAIN 原始行范围；不覆盖源文件。每 fly 的 `*_train_responses.npz` 保存四种响应及两半 TRAIN 行号，`response_summary.csv` 给出逐 ROI 的 raw/processed TRAIN 均值、标准差和零值比例。

| 表示 | 操作 | 时间性质 | 用途 |
|---|---|---|---|
| `raw` | `F(t)` 原样复制 | 当前帧 | 原始锚点、RF 对照、未来预测候选 |
| `li_style_rf_relative` | `F(t) - Gaussian_10s(F)(t)` | **NON-CAUSAL / OFFLINE RF CHARACTERIZATION ONLY** | 描述性 RF、中心及对齐；严禁作为后段预测的预处理 |
| `causal_ema_residual_60s` | `F(t) - EMA_60s(F)(t)` | 当前及过去 | RF 比较、未来预测候选 |
| `causal_block_median_residual_60s` | 当前强度减去先前 60 秒的分块 median 基线 | 当前及过去 | RF 比较、未来预测候选 |

论文的 RF 方法先用约 10 秒标准差的 Gaussian 低通估计慢基线，再相减得到 relative response；**不是除以基线的 ΔF/F**。本实现按 Zeiss TTL 的中位帧间隔将秒转换为 Gaussian 宽度，先检查帧间隔与中位数的最大偏差不超过 5%。核截断为 3σ，边界反射；每个 TRAIN 半段**独立**处理并丢弃距半段边缘 3σ 内的行。这样 A 的 RF 不会从 B、VALIDATION 或 TEST 响应借到未来信息。已保存的五次记录帧间隔中位数约 73.899 ms，抖动远低于 5%。该离散实现是 Li 方法逻辑的可复现近似，未声称逐行复现论文软件。

Phase 5 的 `fold_a` TRAIN 定义继续使用。先在 TRAIN 更新编号中点两侧各留 40 个 stimulus update 的间隔，再做 Gaussian 边缘裁剪；A/B 最终特征历史互不重叠。四种表示使用同一批 A/B 成像行。因果候选在同一 fly 的连续记录上按时间顺序计算，但只把 TRAIN 行提供给 RF 比较；改变未来 TEST 响应不会改变任何 TRAIN 输出。没有按测试 R² 调任何基线时间常数。

**表示选择规则在运行前写入** `configs/phase6_rf.json`：每种表示对每 fly 的有效 ROI 分别求 TRAIN split-half RF 相关与 A→B 投影相关的中位数，再先在 fly 内平均两项、后跨五只 fly 平均。只有比 raw 至少高 0.02，才选用最佳非 raw 表示；否则保守记录 raw。RF 表示可包含离线 Li 路径；未来预测表示只在 raw/两个 causal 候选中选择。两项选择均只用 TRAIN；它们是 Phase 6.1 暂定决策，不是模型成绩。

重跑：

```bash
OPENBLAS_NUM_THREADS=2 .venv/bin/python modeling_pipeline/phase_06/run.py --workspace-root .
```

参见 [假设登记](PHASE6_ASSUMPTIONS.md)、[可靠性方法](PHASE6_RF_RELIABILITY.md)、[结果报告](PHASE6_1_REPORT.md)。
