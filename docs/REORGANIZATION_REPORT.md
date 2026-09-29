# Dm8 工作流与源码模块重构报告

**任务性质：STRUCTURAL_REFACTOR。**基线是 `origin/main` 的 `d24c7e6`，同时合入当时尚未并入 main 的 Phase 5 分支 `f7e30d0`，以保留五 fly 模型成果。新分支为 `codex/workflow-module-reorganization`。本报告中的数值来自本机 2026-09-30 重跑；生成的清单和详细比较在 Git 忽略的 `outputs/reorganization/`。完整科研结论仍以 `FINAL_PREDICTIVE_MODEL_REPORT.md` 为准。

## 1. 重构前 tree

```text
dm8_modeling/
├── simulate/                 # 只读刺激工程副本
├── Dm8_module/               # 只读五 fly 实验记录
├── src/dm8_modeling/
│   ├── workspace.py, model.py, ridge.py, pixel.py, cnn.py
│   ├── pipeline.py, splits.py, cli.py, phase5_cli.py, audit.py
│   └── data/, preprocessing/, datasets/, features/, models/, evaluation/, experiments/
├── scripts/                  # 独立验证和历史分析
├── tests/                    # 四个根级测试文件
├── configs/phase5_first_round.json
├── outputs/                  # 旧实验结果
└── docs/                     # 科研报告
```

## 2. 重构后 tree

```text
dm8_modeling/
├── README.md, PROJECT_STRUCTURE.md, REORGANIZATION_MAP.md
├── simulate/, Dm8_module/    # 原位置、只读、Git 忽略
├── modeling_pipeline/
│   ├── README.md, DATA_FLOW.md, MODELING_MAP.md
│   └── stage_01_.../ … stage_12_.../  # 每段 README + run.py
├── src/dm8_modeling/
│   ├── README.md, MODULE_DEPENDENCY_MAP.md
│   ├── workspace/, data/, preprocessing/, datasets/, features/, rf/
│   └── models/, evaluation/, experiments/, io/, cli/
├── datasets/individual/, integrated/, population/  # 教学 README + 忽略的 manifest
├── configs/workflow.json, phase5_first_round.json, README.md
├── outputs/stage_01_.../ … outputs/stage_12_.../ # 生成，Git 忽略
├── tests/workspace/, data/, preprocessing/, datasets/, features/, rf/
│   └── models/, evaluation/, integration/
├── scripts/README.md + 原有工具
└── docs/                    # 科研报告与本报告
```

## 3. 根目录职责

| 目录 | 职责 |
|---|---|
| `simulate/` | 实验刺激 generation、packaging、playback 与 marker-lock 的只读来源 |
| `Dm8_module/` | 五只 fly 的原始记录，包含 frozen 刺激、Results.csv、TTL 与实验元数据 |
| `modeling_pipeline/` | 按科研顺序解释 WHY、对象合同与执行顺序 |
| `src/dm8_modeling/` | 可复用的数据、RF、预测和评价实现 |
| `datasets/` | 派生数据对象的清单和说明，不复制原始记录 |
| `configs/` | 工作流路径与 Phase 5 实际模型配置 |
| `outputs/` | 本机生成结果、旧结果、stage receipts，不提交 Git |
| `tests/` | 科学不变量与兼容回归 |
| `scripts/` | 仍可运行的独立审计和历史脚本 |
| `docs/` | 科研证据、结果解释与迁移报告 |

## 4–6. 十二个 Stage 的输入、输出、源码

| Stage | 输入 | 处理/输出 | src owner |
|---|---|---|---|
| 01 来源审计 | 两只读根、workflow config | 536 个实验文件清单、223 个 Python 源文件索引；manifest 哈希 760 个输入 | `workspace.inventory`、`io.stage_manifest` |
| 02 冻结刺激 | recipe、realized NPZ | 五个 `StimulusData` 的 seed/灰度核验摘要 | `data.stimulus` |
| 03 响应与时钟 | Results、DLP/Zeiss TTL、flip | `ResponseData`、`ClockData` 的数量/单位摘要 | `data.response`、`data.clocks` |
| 04 时间对齐 | 02+03 原始事实 | 最近已呈现更新的 `AlignedSession` 摘要 | `data.alignment` |
| 05 响应表示 | payload ROI 强度、训练 split | 因果候选/训练尺度摘要 | `preprocessing` |
| 06 单 fly 数据集 | 五个对齐会话、统一特征/切分 | 五个 `IndividualDataset` manifest | `features.temporal_basis`、`datasets.individual/splits` |
| 07 整合数据集 | 五个个体数据集 | 1,907,824 条可追溯逻辑观测、公共 X 索引及 manifest | `datasets.integrated` |
| 08 RF | 个体 X/y 的训练段 | 236 ROI 可靠性 CSV、五份 `[900,ROI]` RF 核 NPZ | `rf.sta/null_tests`、`evaluation.reliability` |
| 09 独立模型 | 五个个体数据集、全局 fold | 两折独立单像素/Ridge 参数与指标 | `models.linear.individual`、`experiments.runner` |
| 10 共享/群体模型 | 相同五 fly 数据与配置 | 共享、fly 偏差、低秩、群体、LOFO 的 22 个参数包/两折比较 | `models.population`、`experiments.runner/transfer` |
| 11 评价 | Stage 10 保存指标 | 不重训的 fly-aware 成对评价 JSON | `evaluation.comparison` |
| 12 最终分析 | 评价摘要、最终科研报告 | 停止决策与解释清单 | `experiments.workflow`、`io.stage_manifest` |

各段 README 给出输入路径、shape、单位、公式、参数、测试与调试；各 `run.py` 仅编排源码 API。`pipeline stage N` 要求前一 manifest 存在且 config、输入、输出哈希有效；`pipeline run` 顺序执行；`--from-stage N` 从已有前置结果继续。

## 7. 旧 src → 新 src

完整逐项映射见根目录 [`REORGANIZATION_MAP.md`](../REORGANIZATION_MAP.md)。主要拆分：`workspace.py` → `workspace/paths.py` 与 `inventory.py`；`model.py` → `features/lagged.py`、`preprocessing/fluorescence.py`、`rf/sta.py`、`evaluation/legacy_metrics.py`；`ridge.py` → `features/temporal_basis.py` 与 `models/linear/binned_strf.py`；`pixel.py` → `models/linear/pixel_temporal.py` 与 `rf/null_tests.py`；`cli.py` → `cli/`；`pipeline.py` → `datasets/legacy_model_dataset.py`。

## 8–10. 模块职责、上游/下游及测试

| 模块 | 上游 → 本层 → 下游 | 主要测试 |
|---|---|---|
| workspace | 文件系统 → 路径/元数据清单 → data/Stage 01 | `tests/workspace/test_workflow.py`、`tests/integration/test_workspace_audit.py` |
| data | 原始包 → 刺激/ROI/时钟/对齐对象 → preprocessing/datasets | `tests/data/test_alignment.py`、`tests/integration/test_workspace_audit.py` |
| preprocessing | 对齐强度、TRAIN split → 因果 F0/尺度 → datasets/models | `tests/preprocessing/test_normalization.py`、integration |
| features | frozen 刺激、更新索引 → 只含当前/过去的 X → datasets/models | `tests/features/test_lagged.py` |
| datasets | data + features + split → 个体/整合/群体对象 → rf/models | `tests/datasets/test_integrated.py`、integration |
| rf | TRAIN X/y → STA、shift null → 诊断/模型解释 | `tests/rf/test_rf.py`、旧模型测试 |
| models | 数据集 → 预测参数/ŷ → evaluation | `tests/models/`、`tests/integration/test_phase5.py` |
| evaluation | 预测与目标、训练 RF → 指标/诊断 → experiments/report | `tests/evaluation/test_metrics.py`、integration |
| experiments | configs + datasets + models → 矩阵/登记/Stage 调度 → CLI | `tests/integration/test_phase5.py`、workspace |
| io | 派生对象 → JSON/CSV/receipt → Stage 校验 | `tests/workspace/test_workflow.py` |
| cli | 用户参数 → 调用 experiments/旧兼容入口 → outputs | 旧重跑、全 pipeline 实际运行 |

一级模块均有含目的、shape、单位、公式、参数、错误、限制、Stage 映射的 README；模块依赖方向见 `src/dm8_modeling/MODULE_DEPENDENCY_MAP.md`。

## 11–15. 数据集、配置、输出、测试和文档

- `datasets/individual/`：一只 fly/run 一份 `[frame,ROI]` 目标；`datasets/integrated/`：按 fly/ROI/frame 展开的逻辑观测，实际 X 只保存 `[8961,900]` 公共表与索引；`datasets/population/`：每 fly 的训练段选定 ROI 标准化均值。三种对象不可混用。生成 manifest 忽略于 Git。
- `configs/workflow.json`：源根、结果根、工作流展示默认值；`configs/phase5_first_round.json`：实际两折、4×10 时间特征、响应、RF 筛查阈值、模型惩罚、seed。实验配方中的 9000、15×15、120/15 Hz 是原始事实，不由分析配置改写。
- `outputs/stage_01_*` 至 `stage_12_*`：每段都有 `stage_manifest.json`、UTC 时间、状态、输入/输出 SHA-256、完整 workflow config 与运行时 Git SHA。Stage 01 输入包括 536 个原始文件与 223 个刺激 Python 文件。旧 `outputs/qc_verified/`、`first_pass/`、`ridge_raw/`、`pixel_raw/`、`cnn_comparison/`、`experiments/phase5_first_round/` 均原位保留。
- `tests/` 分九类，每类有 README。32 个测试保护 seed/显示更新区别、帧连续、TTL 单调、因果对齐、payload 排他边界、完整历史、全局 split purge、训练段尺度、观测 provenance、模型保存/重播等。
- `docs/` 保留科研报告；工作流教学位于 `modeling_pipeline/`，源码教学位于 `src/dm8_modeling/**/README.md`，数据对象解释位于顶层 `datasets/README.md`。

## 16. scripts 审计

无脚本移动或删除，因为旧报告直接引用路径。`verify_stimulus_provenance.py`、`compare_baselines.py`、`validate_pixel_model.py`、`check_common_mode.py` 保持独立工具；`audit_response_timing_rf.py`、`audit_cross_fly_rf.py`、`audit_timing_offset.py` 保留为历史分析。每项 A/D 分类与原因见 [`scripts/README.md`](../scripts/README.md)。

## 17. 消除的重复实现

旧 `model.py`、`ridge.py`、`pixel.py`、`cnn.py`、`workspace.py`、`pipeline.py` 和 `splits.py` 现为轻量兼容转发。EMA residual 复用 `preprocessing.baseline.causal_ema_baseline`；Phase 5 RF 筛查统一调用 `rf.sta.estimate_reverse_correlation`；跨 fly 训练从 `evaluation.cross_fly` 移到 `experiments.transfer`；Stage 11 用纯 `compare_cross_fold` 读取 Stage 10 结果，避免覆盖前一阶段输出。旧单 fly STA 和历史审计路径保留其原数学与数值兼容，不以新算法替换旧报告。

## 18. 已减少的 hard-code

`data.stimulus.load_stimulus_data` 从每个 `stim_recipe.json` 读取 `stimulus_update_count` 与 `grid_rows × grid_cols`，不再在 loader 固定 9000/225。Phase 5 的 RF 筛查阈值从 `configs/phase5_first_round.json` 传给训练段筛查。模型的 225/15×15 维、一些旧 CLI 的 15 Hz/lag 和历史 null 参数仍反映本次固定实验与兼容计算；本次没有在结构重构中把它们改成跨实验泛化算法。

## 19. Compatibility wrappers

保留根级 `workspace.py`、`model.py`、`ridge.py`、`pixel.py`、`cnn.py`、`pipeline.py`、`splits.py`、`audit.py`、`phase5_cli.py`、`evaluation/cross_fly.py`，及旧 `dm8-model`、`dm8-predict`、`dm8-cnn`、`dm8-cnn-predict` 命令。旧模型 replay 的源 SHA 和预测一致性检查照常运行。

## 20. BUG_FIX 记录

本次结构迁移初稿把 `cli/legacy.py` 的审计导入写成 `.audit`，进入 `cli/` 包后会尝试导入不存在的 `dm8_modeling.cli.audit`，导致旧 `--audit` 命令失败。已改为 `..evaluation.audit`。**科学影响：无**；修复前没有产生新审计结果，修复后四份审计文件与重构前逐字节相同。没有修改 raw 记录或模型公式。

## 21. Tests / checks

- `.venv/bin/python -m unittest discover -s tests -q`：**32 passed**。
- `.venv/bin/python -m compileall -q src/dm8_modeling modeling_pipeline`：通过。
- `dm8-model pipeline run --workspace-root .`：**01→12 全部 complete**。
- 五只 fly 的 `dm8-cnn-predict` 保存模型重播：五次均通过保存预测/真实值/时间戳核对。
- 旧审计命令重跑：五只 fly 成功；四份对应 CSV/JSON 与旧结果逐字节相同。
- `dm8-model dataset describe-integrated`、`dm8-model evaluate` 旧多 fly 命令通过；`dm8-predict` 用 fly1/Mean29 保存的像素模型独立重播 2,413 个测试帧（r=0.493，R²=0.235）。
- Markdown 内部相对链接、Stage README 所指具体测试路径与 `git diff --check` 在交付前再次核验。

## 22. Baseline regression

`scripts/compare_baselines.py` 报告 QC、STA、Ridge、Pixel 均为 `READABILITY_ONLY`，五只 fly JSON 字段与 NPZ 数组在 1e−8 容差内一致，实际最大差为 0。Stage 10 与旧完整 Phase 5 比较：两折 summary + cross-fold 共 1,026 个数字字段，最大绝对差 `8.88e−16`；22 份模型参数包在 1e−8 容差内一致；22 份指标 CSV 的 2,429 个浮点单元格有末位差异，最大 `2.84e−14`，无超容差变化。Git SHA/dirty 状态变化是运行元数据，不是模型数值变化。旧 Phase 5 的额外历史日志/手动输出文件未复制进新 Stage 10。

旧 EMA residual 与统一 F0 实现在 fly1 的 `8119×42` 原始强度上逐元素**完全一致**（最大差 0）。

## 23. 原始实验文件不变

旧 `outputs/audit/data_inventory.json` 与新 Stage 01 清单比较：**536/536 条相对路径和 SHA-256 完全相同**。旧 Phase 5 与新 Stage 07 的 5 fly × 7 个关键源文件哈希也完全相同。`simulate/` 与 `Dm8_module/` 均由 `.gitignore` 排除；所有 Stage 只读源，结果只写 `datasets/` 的派生清单与 `outputs/`。刺激工程源码的精确六月版本仍有历史来源限制，Stage 01 只证明本机工程副本当前文件身份，不把它误称为原运行版本。

## 科学解释与下一步

这个目录现在可以按 **Stage README → Stage run.py → 源模块 README → 实现 → config → tests → outputs** 阅读。当前可以解释和重播的主线仍是原始 ROI 平均强度目标上的因果单像素/Ridge 对照；五 fly 共享模型未稳定优于独立模型。测试是同一条冻结刺激的历史探索性时间分块，不是新的独立刺激或盲测，也没有物理波长/辐照度校准。
