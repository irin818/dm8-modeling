# experiments/ 模块说明

当前 [`phase6.py`](phase6.py) 独立编排 TRAIN-only 响应、RF 可靠性和中心 Gate；历史 `runner.py` 仍供 Phase 5 模型重播。[Phase 6.1 报告](../../../docs/PHASE6_1_REPORT.md) 记录为何暂不进入新预测模型。

## 模块目的

统一配置、训练矩阵、LOFO 适配、运行记录和逐阶段顺序。

## 对应科学问题

哪些模型与参数被运行，结果是否可复算？

## 输入

workflow.json、phase5_first_round.json、只读数据集及前序 stage manifest。

## 输出

模型 artifact、registry、cross-fold JSON、Stage manifest。

## 数据 shape

每折 5 fly、236 ROI；Stage 10 两折 22 个模型 artifact。

## 单位

继承目标的强度或 z-score 单位，配置值显式保存。

## 核心数据对象

Phase5Config、WorkflowContext、模型 Fit dataclass。

## 处理逻辑

config.py 校验参数；runner.py 执行矩阵；transfer.py 训练源 fly 并评估目标；workflow.py 调度 Stage；registry.py 保存历史。

## 数学逻辑

模型选择仅用 TRAIN/VALIDATION；TEST 只用于最终评分。

## 核心函数

Phase5Config.load；run_first_round；leave_one_fly_out；run_stage；write_registry。

## 可调参数

configs/workflow.json 与 configs/phase5_first_round.json 是正式可调入口。

## 上游依赖

datasets、models、evaluation、io。

## 下游依赖

cli、Stage 09–12、输出报告。

## 常见错误

缺失前序 manifest、配置不匹配、重复实验编号、输出目录混淆。

## 当前假设

所有飞虫共用一条刺激与 global split；当前结果探索性。

## 科研限制

改变模型算法会使旧数值回归失效，必须另做科学标记。

## 对应 tests

tests/workspace/test_workflow.py；tests/integration/test_phase5.py。

## 对应 modeling_pipeline stage

09–12
