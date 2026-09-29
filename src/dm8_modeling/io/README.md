# io/ 模块说明

## 模块目的

保存小型派生表与有 SHA-256 的逐阶段收据，不写原始目录。

## 对应科学问题

一个结果究竟由哪个输入、配置和 Git 版本产生？

## 输入

输入/输出文件路径、workflow config、Git checkout。

## 输出

stage_manifest.json、JSON/CSV 派生摘要。

## 数据 shape

manifest 为 JSON object；表格为每 ROI/每 fly 行。

## 单位

哈希 hex；timestamp UTC；数值沿用来源目标单位。

## 核心数据对象

Stage manifest dict。

## 处理逻辑

tables.py 明确写 JSON/CSV；stage_manifest.py 哈希输入输出并验证前序文件未改变。

## 数学逻辑

receipt=(hash(inputs),config,hash(outputs),git SHA,status)。

## 核心函数

write_stage_manifest；verify_stage_manifest；save_json；save_csv。

## 可调参数

workflow.json 指定输出根；保存 schema version 固定。

## 上游依赖

各 Stage run.py、experiments。

## 下游依赖

下一 Stage 的 require_previous、复现实验审计。

## 常见错误

前序输出被覆盖、输入内容变化、配置漂移、无 Git checkout。

## 当前假设

只允许写派生目录；绝不将原始数组写入 datasets/。

## 科研限制

manifest 确保文件完整性，不自动证明科学解释正确。

## 对应 tests

tests/workspace/test_workflow.py。

## 对应 modeling_pipeline stage

01–12
