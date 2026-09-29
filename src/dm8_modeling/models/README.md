# models/ 模块说明

## 模块目的

根据 X 预测 ROI 或群体响应；保持独立与共享模型层级。

## 对应科学问题

单 fly 可预测多少？共享 K 是否稳定优于独立 K？

## 输入

IndividualDataset/PopulationDataset、训练/验证 split、可选共享特征。

## 输出

逐 ROI prediction、系数、共享核/gain/bias、训练验证选择记录。

## 数据 shape

个体 yhat [frame,ROI]；shared K [900]；fly deviation [900]；CNN 输入 [frame,lag,15,15]。

## 单位

预测随目标表示而定：强度或训练 z-score。

## 核心数据对象

IndividualFit、SharedFit、HierarchicalFit、BasisFit、PopulationFit、CNNResult。

## 处理逻辑

linear/ 提供像素和 Ridge；population/ 提供完全共享、部分共享、低秩；neural/ 保留历史 compact CNN。

## 数学逻辑

y_fr=b_fr+g_fr X(K_shared+Δ_f)；个体 Ridge 为 b_fr+Xβ_fr。

## 核心函数

fit_individual_pixel/ridge；fit_shared_strf；fit_hierarchical_strf；fit_shared_basis；fit_population_average。

## 可调参数

phase5_first_round.json 的 alpha、penalty、rank、迭代、权重；旧 CNN 参数在历史 CLI。

## 上游依赖

datasets、features、rf 与纯 evaluation.metrics。

## 下游依赖

experiments、evaluation 报告、CLI replay。

## 常见错误

不同目标的 R² 直接排名、测试选择 hyperparameter、把 ROI 当动物。

## 当前假设

模型在统一时间 fold 上比较；历史 compact CNN 只作为原有对照。

## 科研限制

当前共享模型未稳定提高，故 shared CNN/TCN 和 LN 只标 planned。

## 对应 tests

tests/models/test_legacy_models.py；tests/models/test_cnn.py；tests/integration/test_phase5.py。

## 对应 modeling_pipeline stage

09–10
