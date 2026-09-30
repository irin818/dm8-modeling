# 当前 RF 与历史模型地图

项目当前处于 **描述性神经生理分析** 阶段。正式入口为 [Phase 6.2](phase_06/README.md)，旧预测实验的科学结论保存在[历史报告](../docs/HISTORICAL_MODELING_CONCLUSIONS.md)，实现已退役。

| 层级 | 当前作用 | 源码 / 证据 |
|---|---|---|
| 保存的数字刺激与设备时间 | 确定每个成像帧最近的已显示更新 | `data/stimulus.py`、`data/clocks.py`、`data/alignment.py` |
| ROI 平均强度 | 尚未证明为正式校正钙信号的响应来源 | `data/response.py`、原始 `Results.csv` SHA-256 |
| Li-style 离线响应 | 固定的主 RF 响应；raw 作敏感性诊断 | `preprocessing/rf_response.py` |
| 每 ROI 低方差 RF | 40 更新/4×10 箱的带符号反向相关 | `rf/characterization.py`、`experiments/phase62.py` |
| RF 中心与群体图 | 白噪声导出中心、无环绕对齐、fly 内及 fly 间等权 | `rf/population.py`、[Phase 6.2 报告](../docs/PHASE6_2_POPULATION_RF.md) |
| 严格单 ROI RF | Phase 6.1 的独立历史问题：0/236 `RF_RELIABLE` | [Phase 6.1 报告](../docs/PHASE6_1_REPORT.md) |
| 预测模型 | STA、Pixel、Ridge、CNN、共享、分层、低秩、population-average、预测型 LOFO 均为历史结果 | [历史总结](../docs/HISTORICAL_MODELING_CONCLUSIONS.md)、Git 历史 |

当前分析**不以 R²、预测 benchmark 或模型复杂度为进度指标**。Phase 6.2 的留一 fly 是平均 RF 对个别动物的稳定性检查，不训练预测器，也不构成独立验证。仅在环绕方向与各 fly 的预设描述性门槛成立时才会拟合 DoG；本轮门槛未通过。
