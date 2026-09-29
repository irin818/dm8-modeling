# evaluation/ 模块说明

## 模块目的

统计逐 ROI/逐 fly 分数、RF 可靠性与跨折对照；不训练模型。

## 对应科学问题

模型是否在同目标、同 fold、多个 fly 上真正改善？

## 输入

保存的预测/真实 y、训练方差、ROI/fly 标识、global split。

## 输出

Pearson r、R²、MSE、normalized MSE、ΔR²、可靠性表与诊断图。

## 数据 shape

per ROI [236]；per fly [5]；跨折两套；图 SVG。

## 单位

r、R² 无单位；MSE 为目标单位平方；normalized MSE 无单位。

## 核心数据对象

ReliabilityResult；summary dict/CSV/JSON。

## 处理逻辑

metrics.py 计算纯分数；comparison.py 做成对 fly-aware 汇总；reliability.py 做训练段 RF 筛查。LOFO 训练移至 experiments.transfer。

## 数学逻辑

R²=1−MSE/Var_test；ΔR²_fr=R²_shared,fr−R²_individual,fr。

## 核心函数

score_columns；summarize_roi_records；write_cross_fold_comparison；assess_training_reliability。

## 可调参数

比较模型集合在 comparison.py；阈值在 phase5_first_round.json；图表由 plots.py。

## 上游依赖

datasets、rf、models 保存的预测。

## 下游依赖

experiments、Stage 11、最终科研报告。

## 常见错误

ROI key mismatch、不同 response target 混比、历史 test 被称盲测。

## 当前假设

fly 是重复单位；相同 stimulus 的各 ROI 不独立。

## 科研限制

两折共享训练前缀，无法给真正独立的跨刺激泛化结论。

## 对应 tests

tests/evaluation/test_metrics.py；tests/integration/test_phase5.py。

## 对应 modeling_pipeline stage

08，11
