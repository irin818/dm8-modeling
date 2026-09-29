# rf/ 模块说明

## 模块目的

估计 receptive field 并提供刺激响应零模型。

## 对应科学问题

当前刺激是否在 ROI 中留下可检测且有空间/时间结构的关联？

## 输入

训练段 X、ROI 强度、对齐时钟；历史 STA 也需要测试段作评估。

## 输出

BaselineResult 的 STA [lag,15,15,ROI]、rank-one 核；Phase 5 训练两半与验证诊断核 `[900,ROI]`；shift p 与 FDR q。

## 数据 shape

STA 默认 lag45×15×15×ROI；Phase5 诊断核 [900,ROI]。

## 单位

核：强度×数字刺激/样本；p/q 无单位。

## 核心数据对象

BaselineResult；null-test arrays。

## 处理逻辑

sta.py 训练 reverse correlation、独立测试；null_tests.py circular shift 与 BH；低秩分解描述时空可分性。

## 数学逻辑

K=X_trainᵀ(y_train−ȳ)/n；rank-one 能量=σ1²/Σσq²。

## 核心函数

estimate_reverse_correlation；fit_sta_baseline（旧单 fly baseline）；_shift_p_values；_bh_q_values。

## 可调参数

workflow.json sta_lag_updates；null shift exclusion 保留旧实验值。

## 上游依赖

data、features、datasets、preprocessing。

## 下游依赖

evaluation.reliability、models 的 RF 解释与历史 CLI。

## 常见错误

把 shift p 当充分生理证据、把 rank-one 能量当预测能力、时钟错位。

## 当前假设

测试结果历史已查看，RF 和预测结果必须分开解释。

## 科研限制

缺少同 ROI 独立重复试次，无法测正式 noise ceiling。

## 对应 tests

tests/rf/test_rf.py；tests/models/test_legacy_models.py。

## 对应 modeling_pipeline stage

08
