# 当前 RF 与历史模型地图

项目当前处于 **描述性神经生理分析** 阶段。正式入口为 [Phase 6 工作入口](phase_06/README.md)，最新完成 [Phase 6.4 Gaussian / DoG 结构比较](../docs/PHASE6_4_GAUSSIAN_DOG_TEST.md)。旧预测实验的科学结论保存在[历史报告](../docs/HISTORICAL_MODELING_CONCLUSIONS.md)，实现已退役。

| 层级 | 当前作用 | 源码 / 证据 |
|---|---|---|
| 保存的数字刺激与设备时间 | 确定每个成像帧最近的已显示更新 | `data/stimulus.py`、`data/clocks.py`、`data/alignment.py` |
| ROI 平均强度 | 尚未证明为正式校正钙信号的响应来源 | `data/response.py`、原始 `Results.csv` SHA-256 |
| Li-style 离线响应 | 固定的主 RF 响应；raw 作敏感性诊断 | `preprocessing/rf_response.py` |
| 每 ROI 低方差 RF | 40 更新/4×10 箱的带符号反向相关 | `rf/characterization.py`、`experiments/phase62.py` |
| RF 中心与群体图 | 白噪声导出中心、无环绕对齐、fly 内及 fly 间等权 | `rf/population.py`、[Phase 6.2 报告](../docs/PHASE6_2_POPULATION_RF.md) |
| 各 fly 与群体内部验证 | 同一估计器，1000 次 raw 共同平移后重做 RF/中心/对齐；符号共识、时间箱、稳定中心分层 | `rf/validation.py`、`experiments/phase63.py`、[Phase 6.3 报告](../docs/PHASE6_3_FLY_POPULATION_VALIDATION.md) |
| 冻结 RF 的空间结构比较 | 1000 步旋转投影、M0–M3、径向敏感性、LOFO 与旧 null；不重提 RF | `rf/dog.py`、`phase_06/run_dog_test.py`、[Phase 6.4 报告](../docs/PHASE6_4_GAUSSIAN_DOG_TEST.md) |
| 严格单 ROI RF | Phase 6.1 的独立历史问题：0/236 `RF_RELIABLE` | [Phase 6.1 报告](../docs/PHASE6_1_REPORT.md) |
| 预测模型 | STA、Pixel、Ridge、CNN、共享、分层、低秩、population-average、预测型 LOFO 均为历史结果 | [历史总结](../docs/HISTORICAL_MODELING_CONCLUSIONS.md)、Git 历史 |

当前分析**不以 R²、预测 benchmark 或模型复杂度为进度指标**。Phase 6.2 的留一 fly 是平均 RF 的描述性稳定性检查。Phase 6.4 为检验“是否确需第二反号空间分量”而比较 DoG：群体 M3 未优于 M1，第二分量不可辨识；留一 fly 只检验冻结图形参数对新 fly 的泛化，不预测原始响应。6.4 完成后停止。
