# datasets/ 模块说明

## 模块目的

组织个体、整合和群体样本，并绑定来源与全局 split。

## 对应科学问题

五只 fly 如何共享刺激而不丢失生物层级？

## 输入

AlignedSession、ProcessedResponse、公共特征表和 global update split。

## 输出

IndividualDataset、IntegratedDataset、PopulationDataset、GlobalStimulusSplit；metadata manifest。

## 数据 shape

个人 X [8084,900]；逻辑整合 X [1907824,900]，物理表 [8961,900]。

## 单位

X 数字刺激均值；raw y 图像强度；z-score 无单位；时间微秒。

## 核心数据对象

IndividualDataset、IndexedFeatureMatrix、IntegratedDataset、PopulationDataset、GlobalStimulusSplit。

## 处理逻辑

individual.py 保留 fly/ROI；integrated.py 以公共 X 表索引长表；population.py 聚合训练定义 ROI；splits.py 在刺激更新轴 purge。

## 数学逻辑

observation=(fly,ROI,time)→X_update→y；train/val/test 历史窗口互不交叠。

## 核心函数

load_individual_datasets；build_integrated_dataset；build_population_dataset；GlobalStimulusSplit.labels。

## 可调参数

phase5_first_round.json 的 bins、updates_per_bin、fold 更新边界。

## 上游依赖

data、features、preprocessing。

## 下游依赖

RF、models、evaluation、experiments。

## 常见错误

五份刺激不一致、原 Results 行缺失、split history overlap、大 X 意外物化。

## 当前假设

5 fly 是生物重复，同一个 frozen stimulus 不是 5 条独立刺激。

## 科研限制

236 ROI 不等于 236 fly；只有一个条件，缺少外部新刺激验证。

## 对应 tests

tests/datasets/test_integrated.py；tests/integration/test_phase5.py。

## 对应 modeling_pipeline stage

06–07，10
