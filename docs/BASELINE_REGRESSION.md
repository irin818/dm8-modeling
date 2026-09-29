# 旧结果与当前重跑的回归核对

在改动前保留的本机 `outputs/qc_verified`、`outputs/first_pass`、`outputs/ridge_raw`、`outputs/pixel_raw` 与本任务新生成的 `outputs/regression_*` 比较。脚本 `scripts/compare_baselines.py` 逐层比较五只 fly 的 JSON 字段、模型 NPZ 数组 shape/dtype 和数值；完整机器结果在 `outputs/audit/baseline_regression.json`。新运行使用 `OPENBLAS_NUM_THREADS=1`；比较容差 1e−8，本次实际最大数值差为 **0**。

| 流程 | 五次结果 | 分类 | 说明 |
|---|---|---|---|
| QC | 共同字段完全相同 | READABILITY_ONLY | 旧 QC 文件早于当前已有的来源/配方校验字段；新文件共增加 80 个逐运行 metadata key，旧 key 均保留，值不变 |
| STA raw | 指标及核数组完全相同 | READABILITY_ONLY | 统一分块检查未改变 70/30 边界 |
| Ridge raw | 指标及系数完全相同 | READABILITY_ONLY | 统一分块检查未改变 50/20/30 边界 |
| Pixel raw | 指标、参数、测试预测完全相同 | READABILITY_ONLY | 统一分块检查未改变选点、验证和测试 |

Phase 1 的原始 STA/Ridge 中位成绩见 [PHASE1_REPORT](PHASE1_REPORT.md)。当前五只 fly 的 STA 测试相关中位数依次约 0.005、0.017、−0.014、0.013、0.045，测试 R² 中位数全负；Ridge 测试相关中位数约 0.010、0.015、−0.011、0.015、0.084。像素模型测试相关中位数约 0.021、0.043、−0.005、0.044、0.042，R² 中位数也全负。数字吻合仅证明本次可读性重构未改变旧计算，**不把旧模型弱预测解释为已解决**。

本任务新增的 ROI/RF/候选预处理和 offset 审计没有替换以上模型训练或成绩；因此其解释属于新分析，不伪称“回归前后成绩提升”。
