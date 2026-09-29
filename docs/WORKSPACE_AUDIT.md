# WORKSPACE_AUDIT：当前目录与边界（2026-09-30）

本页记录整理**之前**的实际目录，不移动或重命名任何原件。证据状态只用 `DIRECTLY_OBSERVED`、`DERIVED`、`ESTIMATED`、`INFERRED`、`UNRESOLVED`。

```text
/Users/irin/Documents/dm8_modeling/     ← 分析 Git 仓库，同时是工作区根目录
├── simulate/07E_260530_01/             ← 刺激工程副本：源码 + 历史生成产物
├── Dm8_module/UV-15Hz/fly1..fly5/      ← 五次实验原件，严格只读
├── src/dm8_modeling/                    ← 正式分析库
├── scripts/、tests/、docs/              ← 命令、验证、说明
├── outputs/                             ← 分析派生文件，Git 忽略
├── .venv/、.git/                         ← 环境及仓库元数据
└── README.md、pyproject.toml、AGENTS.md  ← 项目入口和规则
```

| 目录 | 作用 | 扫描规模 | 处理方式 | 证据 |
|---|---|---:|---|---|
| 根目录 Git 仓库 | Dm8 分析与建模源码 | `git rev-parse --show-toplevel` 指向此目录 | 原地使用，无须再套一层 `dm8-modeling/` | DIRECTLY_OBSERVED |
| `simulate/07E_260530_01/` | 05E 生成器、05L 操作流程、05H 播放与 marker lock 等；同时含 `package_library/`、`fly_runs/` 历史产物 | 约 4.8 GiB；排除缓存后约 4,320 文件 | 只读审计，不并入分析包、不移动 | DIRECTLY_OBSERVED |
| `Dm8_module/` | 本次五只 fly 的实验记录 | 536 个磁盘文件，其中 4 个 `.DS_Store`；实验有效文件 532 个，约 421 MiB | 严格只读，不复制到 Git | DIRECTLY_OBSERVED |
| `outputs/` | QC、模型权重、预测、图表、日志 | 约 56 MiB，可重建 | Git 忽略 | DIRECTLY_OBSERVED |
| `src/`、`scripts/`、`tests/`、`docs/` | 分析实现、命令、测试、解释 | 已被当前 Git 跟踪 | 任务分支中维护 | DIRECTLY_OBSERVED |
| `.venv/`、缓存、`.DS_Store` | 本机生成内容 | 与研究输入无关 | 保留在本机并忽略 | DIRECTLY_OBSERVED |

`simulate/` 和 `Dm8_module/` 在初查时显示为分析仓库的未跟踪目录。为避免误把 5 GiB 刺激工程和实验原件加入 Git，分析仓库 `.gitignore` 现明确忽略这两个**本地工作区目录**。这只改变 Git 收录行为，不改动目录内任何文件。`alife_study_exp/` 不在本次更正后的工作区；旧文档把它当作刺激源码的说法应由本次 provenance 审计取代。

## 初步关系与实际调用证据

```text
simulate/07E_260530_01/05L_operator_training_handoff/
    operator profile + run_stage05i_prepare_package.py
    ↓ 调用 05E stimulus_contract.generate_package
    package_library/<package_id>/stim_realized.npz
    ↓ 05L microscope play / 05H PsychoPy playback
Dm8_module/UV-15Hz/fly*/<run>/
    stimulus_package/ + playback/ + capture/ + analysis_marker_lock/
    zeiss_ttl_<run>.csv + Results.csv
    ↓ src/dm8_modeling/data.py
aligned stimulus history X + raw ROI mean intensity y
```

本地 `simulate` 副本目录名为 `07E_260530_01`，五次六月运行日志与配方原路径写的是 Windows `07E_260529_02`；**源码版本完全相同尚未证明**。不过，使用本地 05E `generate_package` 读取每次实验保存的 `stim_recipe.json`，已重算五次各自 `stim_realized.npz` 的 8 个数组，形状、类型及逐值均一致（详见后续 provenance 报告）。这是功能级对应；不能将本机副本冒充运行当天的确切源码快照。

工作区已基本达到逻辑上“刺激工程 + 不可变实验记录 + 分析仓库”的结构。因分析 Git 根目录**就是**工作区根目录，若再机械新建一个 `dm8-modeling/` 子目录，将移动仓库和现有路径，当前没有必要。
