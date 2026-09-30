# Phase 6.5 pipeline audit 导航

逐步骤的 `INPUT / OUTPUT / SHAPE / UNIT / FORMULA / PARAMETERS / SOURCE FILE / SOURCE FUNCTION / ASSUMPTION` 见 [CURRENT_PIPELINE_DATAFLOW.md](CURRENT_PIPELINE_DATAFLOW.md)。Li 原文证据及未解决细节见 [PHASE6_5_LI_METHOD_SOURCE_AUDIT.md](PHASE6_5_LI_METHOD_SOURCE_AUDIT.md)，26 项逐条差异见 [PHASE6_5_EQUIVALENCE_MATRIX.md](PHASE6_5_EQUIVALENCE_MATRIX.md)。

最重要的源码结论：`experiments/phase63.py:estimate_fly` 在 reverse correlation **之前**对每个 ROI 响应做 zscore。`rf/characterization.py:rf_maps` 随后虽对 RF 做 zscore，却只用该结果找中心；最终 `aligned_bins` 和群体图仍来自未做 RF 后 zscore 的 K。这是明确的 P0 不等价。Phase 6.5 C1 把完整个体 STRF 标准化后才对齐/平均。C2 把时间轴恢复到 40 个逐 update lag。C3 的时间截面选择为未由 Li 文献证实的敏感性，不能被命名为 exact replication。

其余 P0 边界：`Results.csv` 上游 registration/ROI/background/neuropil 未核实；保存的 DLP 数字刺激与 Li 的 UV LED 光物理条件未确认相等；无对应 shifting-bar center localizer。这些问题仅凭重写下游 RF 代码无法解决。
