# 模型与 RF 的阶段地图

**Phase 1–5 = HISTORICAL / LEGACY BASELINE。Phase 6.1 = ACTIVE RF CHARACTERIZATION。** Phase 6.1 暂不训练新预测模型；只有 RF 可靠性和中心 Gate 通过，才考虑 Phase 6.2 的规范中心刺激数据集。旧模型和数值结果均保留以重播和讲解，不能视作当前默认研究入口。

| 方法 / 路径 | 状态 | 角色与位置 |
|---|---|---|
| 原始 `Results.csv` 强度 | ACTIVE provenance anchor | `data.response`；每个 processed response 保存源 SHA-256 |
| Li-style offline relative response | ACTIVE descriptive RF only | `preprocessing.rf_response`；**NON-CAUSAL**，不能用于 held-out forecasting |
| raw / causal EMA / causal block-median | ACTIVE TRAIN RF comparison | `preprocessing.fluorescence`；未来预测 target 只能从 causal 路径另行确定 |
| Phase 6.1 训练段 reverse correlation | ACTIVE RF estimator | `rf.characterization`；A/B 核、投影、shift null、FDR、中心和对齐诊断 |
| Stage 08 旧 RF 筛查 | HISTORICAL | `evaluation.reliability`；旧 `p<0.05 + split-half>0` 结果保留，但不筛 Phase 6 ROI |
| STA predictive baseline | LEGACY / HISTORICAL BASELINE | `rf.sta.fit_sta_baseline`；旧测试、报告、数值回归和 replay 保留 |
| Ridge STRF、单像素时间核 | LEGACY / HISTORICAL BASELINE | `models/linear/`；单像素仍是毕业设计可解释的历史预测演示 |
| Compact CNN | LEGACY / HISTORICAL BASELINE | `models/neural/compact_cnn.py`；保存模型和重播保留 |
| 绝对坐标 Shared/Hierarchical STRF、shared basis | LEGACY / HISTORICAL NEGATIVE RESULT | `models/population/`；Phase 5 未稳定胜过单 fly 模型 |
| population-average 预测 | LEGACY / HISTORICAL BASELINE | `models/population/population_average.py`；不能当第六只 fly |
| RF-centered canonical stimulus dataset | Phase 6.2，Gate A+B 未通过 | 本轮**没有实现** |
| LN、shared CNN/TCN、Transformer | 长期方向，未激活 | 本轮**不训练、不创建空实现** |

当前 Phase 6.1 的运行入口是 `modeling_pipeline/phase_06/run.py`；Stage 01–12 的 `dm8-model pipeline` 仍按原顺序复算历史结果。详细定义、阈值和结果见 [RF 可靠性](../docs/PHASE6_RF_RELIABILITY.md) 与 [Phase 6.1 报告](../docs/PHASE6_1_REPORT.md)。
