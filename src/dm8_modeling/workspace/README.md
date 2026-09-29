# workspace/ 模块说明

## 模块目的

定位并审计分析工作区，不修改实验源。

## 对应科学问题

这些文件从哪里来，哪些是可用于建模的来源？

## 输入

工作区根、simulate/、Dm8_module/ 路径。

## 输出

解析状态、文件角色、SHA-256 清单；输出写 outputs/。

## 数据 shape

文件级元数据；不返回响应样本矩阵。

## 单位

大小 bytes；哈希 hex；CSV 范围保留源单位。

## 核心数据对象

WorkspacePaths；inventory 条目 dict。

## 处理逻辑

paths.py 验证根与五次 Results；inventory.py 按格式扫描 CSV/NPZ/JSON/PNG。

## 数学逻辑

h_i=SHA256(file_i)，内容变化会使 Stage manifest 失效。

## 核心函数

WorkspacePaths.resolve；scan_data_inventory；write_inventory。

## 可调参数

configs/workflow.json: data_root、stimulus_code_root、output_root。

## 上游依赖

原始文件系统。

## 下游依赖

Stage 01；data.discover_sessions；io.stage_manifest。

## 常见错误

路径不存在、CSV 列不齐、NPZ 损坏、误把忽略目录当实验源。

## 当前假设

实验源只读，工作区路径可迁移。

## 科研限制

清单识别角色不证明每个历史工程副本是采集时精确版本。

## 对应 tests

tests/workspace/test_workflow.py；tests/integration/test_workspace_audit.py。

## 对应 modeling_pipeline stage

01
