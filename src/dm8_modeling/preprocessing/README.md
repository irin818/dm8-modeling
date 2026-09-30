# preprocessing/ 模块说明

Phase 6.1 另有 [`rf_response.py`](rf_response.py)：10 秒 Gaussian 离线基线相减，明确标记 **NON-CAUSAL / OFFLINE RF CHARACTERIZATION ONLY**。`fluorescence.py` 中的 raw、causal EMA、causal block-median 作为 TRAIN RF 对照和未来预测候选；选法见 [Phase 6.1 响应文档](../../../docs/PHASE6_RESPONSE_RECONSTRUCTION.md)。

## 模块目的

把原始 ROI 强度变成显式命名的响应表示，并只在训练段拟合尺度。

## 对应科学问题

如何比较原始强度、去漂移候选而不泄漏晚段信息？

## 输入

AlignedSession.response [frame,ROI]、Zeiss 微秒、global TRAIN mask。

## 输出

ProcessedResponse [eligible frame,ROI] 与 ResponseScaler。

## 数据 shape

payload [约8119,ROI] → eligible [8084,ROI]。

## 单位

raw 为图像强度；EMA 残差仍是强度；候选 ΔF/F 与 z-score 无单位。

## 核心数据对象

ResponseScaler、ProcessedResponse。

## 处理逻辑

baseline.py 估计因果 EMA F0；fluorescence.py 标记 F-F0/候选比值；normalization.py 只在 TRAIN 拟合 mean/std。

## 数学逻辑

z=(F−μ_train)/σ_train；EMA F0(t) 只用当前及过去。

## 核心函数

causal_ema_baseline；causal_ema_residual；candidate_response；fit_response_scaler。

## 可调参数

`configs/phase5_first_round.json` 定义主响应表示、训练段标准化和候选列表；旧 60 秒 EMA 为历史兼容的固定方法。

## 上游依赖

data.AlignedSession；datasets.splits 的 TRAIN。

## 下游依赖

datasets、RF、models。

## 常见错误

时钟不递增、候选值非有限、零方差 ROI、错把 ΔF/F 候选当官方预处理。

## 当前假设

静态尺度只用 TRAIN；因果在线变换可读过去响应。

## 科研限制

F0 候选未经原始成像/neuropil 验证，去漂移可能去掉真实慢动态。

## 对应 tests

tests/preprocessing/test_normalization.py；tests/integration/test_phase5.py。

## 对应 modeling_pipeline stage

05
