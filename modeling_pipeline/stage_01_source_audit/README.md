# Stage 01 · 来源审计

## 1. 这一阶段为什么存在？

辨认实验刺激源码、五次记录的完整文件角色与不可变来源。

## 2. 上一阶段提供了什么？

simulate/ 与 Dm8_module/；无需前序结果。

## 3. 实际读取哪些文件？

simulate/**/*.py；Dm8_module/**/*（只读）。

## 4. 输入数据对象是什么？

路径/文件元数据记录，无模型数组。

## 5. 输入 shape / axis / units 是什么？

路径、文件大小、SHA-256 与 CSV/NPZ/JSON 元数据；无响应数组输出。

## 6. 这一阶段进行什么处理？

对每个实验文件分类、读取元数据并生成清单，同时索引刺激工程 Python 文件。

## 7. 为什么这样处理？

没有可审计来源就不能解释之后的 stimulus 和 y。

## 8. 数学逻辑是什么？

h_i = SHA256(file_i)；文件身份由内容哈希而非文件名推定。

## 9. 实际调用哪些 src 模块？

workspace/inventory.py: scan_data_inventory, write_inventory；io/stage_manifest.py 对实验文件和刺激源码逐文件记录 SHA-256。

## 10. 数据 shape 如何变化？

原始约 536 个文件 → 同数目的元数据记录。

## 11. 输出是什么？

data_inventory.json、data_inventory.md、stimulus_source_index.json、stage_manifest.json；写入 outputs/stage_01_source_audit/。

## 12. 输出提供给哪个 Stage？

Stage 02、03 的来源文件核对。

## 13. 哪些参数可以修改？

data_root、stimulus_code_root 在 configs/workflow.json；改变会切换被审计的文件集合。

## 14. 哪些东西不能随便修改？

禁止改动 Dm8_module/、simulate/，也不能把原始文件复制入 src/。

## 15. 当前科学限制是什么？

存在跨机器路径与历史版本不完整的问题；来源索引不证明本机 simulate 是六月运行时的精确代码版本。

## 16. 如何运行？

Stage 01 无前置阶段，直接执行：

```bash
cd /Users/irin/Documents/dm8_modeling
.venv/bin/dm8-model pipeline stage 1 --workspace-root .
```

## 17. 如何检查结果是否正确？

文件数、解析状态和哈希齐全；Stage manifest 为 complete。

## 18. 如何调试？

先查路径、权限、损坏文件及 data_inventory.json 的 parse_error。

## 19. 对应哪些 tests？

tests/integration/test_workspace_audit.py；tests/workspace/test_workflow.py
