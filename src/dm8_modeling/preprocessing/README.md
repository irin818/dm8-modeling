# preprocessing/

`rf_response.py` 中的 Li-style 离线响应是 Phase 6.2 固定主表示：从 raw ROI 平均图像强度减去 10 秒 Gaussian 慢基线，反射边界并保留完整 payload。它使用前后时间信息，仅用于**离线描述性 RF**，不能作为在线预测目标。raw 强度是固定敏感性诊断。

`baseline.py`、`fluorescence.py`、`normalization.py` 保留 Stage 05–07 与 Phase 6.1 的因果候选和尺度处理。候选比值不得自动称为正式 ΔF/F；所有表示必须保留原始 `Results.csv` 哈希与时钟/行索引。详见[Phase 6.2 报告](../../../docs/PHASE6_2_POPULATION_RF.md)。
