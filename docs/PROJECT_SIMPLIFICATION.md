# 项目精简：删除依据与保留依据

本轮在 12 个 Stage、11 个源码职责层和原有命令结构不变的前提下，清理了只占文件名但不提供行为的代码文件。`simulate/` 与 `Dm8_module/` 只读，旧输出和保存模型仍可重播。这里说明每一类文件为什么删除或保留；首次重构的历史快照见 [REORGANIZATION_REPORT](REORGANIZATION_REPORT.md)。

## 已删除的 16 个代码文件

| 文件 | 数量 | 删除依据 |
|---|---:|---|
| `modeling_pipeline/__init__.py` 与 12 个 `stage_*/__init__.py` | 13 | Stage 由 `experiments.workflow.run_stage` 按 `run.py` 文件路径加载，工作流目录不在 `src/` 的安装包发现范围内。这些文件只有一句文档字符串；删除后 `dm8-model pipeline run/stage` 仍工作。 |
| `src/dm8_modeling/workspace.py` | 1 | 同名 `workspace/` package 优先被 Python 导入，实际入口是 `workspace/__init__.py`；这个文件无法被正常的 `import dm8_modeling.workspace` 选中。 |
| `src/dm8_modeling/phase5_cli.py` | 1 | 仅导入 `cli.dataset.main` 和 `MODELS`，没有 `pyproject.toml` 命令入口、调用点或独立执行逻辑；正式 `dm8-model dataset/fit/evaluate` 保留。 |
| `src/dm8_modeling/evaluation/cross_fly.py` | 1 | 仅转发 `experiments.transfer.leave_one_fly_out`，仓库中无调用点；源码和文档统一指向负责训练的 `experiments.transfer`。 |

## 仍需保留的短文件

- **源码包的 `__init__.py`**：当前 `pyproject.toml` 使用 `setuptools.find_packages(where="src")`。这些文件标记可安装的包边界，包括只含一行说明的 `models/population/__init__.py` 等。删除会让相应包从安装结果消失。实测当前可发现 15 个包。
- **测试子目录的 `__init__.py`**：项目使用 `python -m unittest discover -s tests`。在同样的临时目录结构中，没有子目录 `__init__.py` 时发现 0 项，有该文件时发现 1 项；删除它们会静默漏测。
- **`model.py`、`ridge.py`、`pixel.py`、`cnn.py`、`pipeline.py`、`splits.py`、`audit.py`**：历史脚本、旧测试或模型重播仍从这些路径导入。它们只转发到唯一真实实现，没有重复算法。新的 CLI 实现已直接导入 canonical 模块。
- **每个 Stage 的 `run.py`**：它展示本阶段输入、调用和输出，是阅读路径的必要一环；每个 Stage 的 19 节 README 延续既定教学结构。

## 代码和配置如何变得更简单

1. 12 个 Stage `run.py` 删除重复的 `if __name__ == "__main__"` 解析器和未使用导入；独立运行统一通过 `dm8-model pipeline stage N --workspace-root .`。保留每段内的前置 manifest 校验；调度器不再重复校验一次。
2. `workflow.json` 只保存来源/输出根与 Phase 5 配置路径。Stage 05 与后续模型阶段统一从 `phase5_first_round.json` 读取响应表示和训练标准化；删除未被模型使用的重复响应、特征和 reporting 字段。
3. `data/`、`datasets/`、`features/`、`preprocessing/` 的 package 导入表删去重复的 `__all__` 清单，保留相同的显式导入名称。旧 CLI、CNN/pixel 重播和 RF 诊断直接导入真正实现模块，不经过兼容转发层。
4. 原始算法、全局 split、测试边界、目标单位、模型参数和保存格式保持不变。没有为计划中的 LN、shared CNN/TCN 新建空壳文件。

## 验证结果

- 32 项单元/集成测试通过，Python 编译与依赖检查通过。
- `dm8-model pipeline run --workspace-root .` 的 Stage 01–12 全部完成，12 个 manifest 的声明哈希全部校验通过。
- 旧 QC/STA/Ridge/Pixel 重跑均为 `READABILITY_ONLY`；四份旧审计 CSV/JSON 逐字节相同。
- 旧 Phase 5 与 Stage 10：1,026 个 JSON 数字字段最大差 `8.88e-16`；22 份模型参数包最大差 `8.88e-16`；指标 CSV 最大差 `2.84e-14`，没有超过 `1e-8` 容差的变化。
- 五只 fly 的保存 CNN 模型和 fly1/Mean29 的像素模型可独立重播；`dataset describe-integrated` 与 `evaluate` 旧命令正常。
- 原始 `Dm8_module/` 的 536 个文件相对路径和 SHA-256 与之前的独立清单完全一致。`simulate/` 未写入，仍由 Git 忽略。

生成的日志、清单和比较 JSON 在本机 Git 忽略的 `outputs/reorganization/`。五只 fly 仍共享一条冻结刺激；本轮只提高可读性和维护性，不改变模型的科研结论。
