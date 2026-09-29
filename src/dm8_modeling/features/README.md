# features/ 模块说明

## 模块目的

只从已经保存的刺激构造模型输入 X。

## 对应科学问题

怎样表示当前及过去视觉历史而不使用未来帧？

## 输入

刺激更新 [9000,225] 与 imaging→update index。

## 输出

lagged X [sample,lag×225] 或 binned X [sample,4×225]；公共 feature_table。

## 数据 shape

40 更新、4 个各 10 更新的时间箱 → 900 特征；历史旧模型可用 18/45 lag。

## 单位

数字刺激编码 ±1；箱均值仍是数字命令单位。

## 核心数据对象

FeatureDefinition；numpy feature_table。

## 处理逻辑

lagged.py 拼接当前/过去更新；temporal_basis.py 对互不重叠的过去更新箱求均值。

## 数学逻辑

X_i,b,p=(1/L)Σ_lag S_{u_i-lag,p}，lag≥0。

## 核心函数

lagged_design；binned_design；build_shared_feature_table。

## 可调参数

phase5_first_round.json feature；workflow.json 历史 lag；配方定义空间尺寸/刷新。

## 上游依赖

data.StimulusData。

## 下游依赖

datasets、RF、models。

## 常见错误

update_index 不完整、维度不一致、误用未来更新、错将 display frame 当 update。

## 当前假设

输入采用 row-major 15×15 展平；五次数字刺激相同。

## 科研限制

数字特征不是物理光谱/照度，也没有眼部光学转换。

## 对应 tests

tests/features/test_lagged.py；tests/models/test_legacy_models.py。

## 对应 modeling_pipeline stage

06
