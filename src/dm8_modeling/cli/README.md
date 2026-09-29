# cli/ 模块说明

## 模块目的

解析命令与路径，调用已有工作流和科学模块。

## 对应科学问题

新读者如何按 Stage 运行且旧命令不破坏？

## 输入

命令参数、workspace-root、配置文件。

## 输出

终端状态与 outputs/ 派生文件。

## 数据 shape

不承担科学数组；只是参数与路径。

## 单位

CLI 参数保持源模块单位。

## 核心数据对象

WorkflowContext 和历史 CLI 参数对象。

## 处理逻辑

__init__.py 分发 pipeline/dataset/fit/evaluate/旧参数；pipeline.py 检查 Stage 依赖；legacy.py 保留老命令。

## 数学逻辑

无独立算法。

## 核心函数

dm8-model pipeline run/stage；dm8-model dataset；dm8-model fit/evaluate。

## 可调参数

--workspace-root、--from-stage、--config 等；科学默认值来自 configs/。

## 上游依赖

experiments、workspace、io。

## 下游依赖

用户终端、Stage manifests。

## 常见错误

从错误目录运行、缺配置、前序 Stage 未完成、错误覆盖输出目录。

## 当前假设

旧 `dm8-model --model ...`、dm8-predict、dm8-cnn 仍受支持。

## 科研限制

入口兼容不意味着旧晚段测试变成盲测。

## 对应 tests

tests/workspace/test_workflow.py；tests/integration/test_workspace_audit.py。

## 对应 modeling_pipeline stage

全阶段
