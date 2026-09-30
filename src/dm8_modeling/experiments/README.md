# experiments/

`workflow.py` 维护 Stage 01–07 的来源链；`phase6.py` 是严格单 ROI RF；`rf_method_audit.py` 记录方法/功效检查；`phase62.py` 读取五次完整白噪声记录，固定参数计算每 fly 与群体 RF、径向曲线、留一 fly 图及 manifest。对应入口见 [`phase_06/README.md`](../../../modeling_pipeline/phase_06/README.md)。

Phase 6.2 不做预测模型训练或独立验证。配置见 [`configs/phase6_2_population_rf.json`](../../../configs/phase6_2_population_rf.json)，完整方法与科学边界见[报告](../../../docs/PHASE6_2_POPULATION_RF.md)。

`phase63.py` 独立计算每 fly 的 signed 四箱 RF、中心稳定性分层和从 raw 平移起步的 1000 次完整 null；之后才建立 population、共识/抵消图及空间/时间比较。`rf_validation_plots.py` 只作图。[Phase 6.3 报告](../../../docs/PHASE6_3_FLY_POPULATION_VALIDATION.md)与[运行前后审计](../../../docs/PHASE6_3_ASSUMPTION_AUDIT.md)说明其探索性统计边界。
