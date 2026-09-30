# 可复用源码地图

从 [项目结构](../../PROJECT_STRUCTURE.md) 与 [Stage 主线](../../modeling_pipeline/README.md) 进入，再按本表找到代码。`modeling_pipeline/stage_XX/run.py` 只负责执行顺序，科学计算在这里；原始 `simulate/`、`Dm8_module/` 始终只读。

当前 Phase 6.1 从 `modeling_pipeline/phase_06/run.py` 进入，计算分别在 `preprocessing/rf_response.py`、`rf/characterization.py` 和 `experiments/phase6.py`。下表的 Stage 编号仍显示 Phase 1–5 历史职责，不代表旧预测模型仍是当前默认入口。

| 源码模块 | 职责 | 对应 Stage | 入口 |
|---|---|---|---|
| [workspace](workspace/README.md) | 定位工作区，审计文件角色/哈希 | 01 | `WorkspacePaths`、`scan_data_inventory` |
| [data](data/README.md) | 读取已保存的实验事实、时钟与因果对齐 | 02–04 | `load_stimulus_data`、`load_response_data`、`load_clock_data`、`align_session` |
| [preprocessing](preprocessing/README.md) | 因果响应候选、离线 Li-style RF 响应与训练段尺度 | 05、Phase 6.1 | `candidate_response`、`li_style_relative_response` |
| [features](features/README.md) | 只从刺激构造 X | 06 | `lagged_design`、`build_shared_feature_table` |
| [datasets](datasets/README.md) | 样本、fly/ROI provenance、全局 split | 06–07 | `IndividualDataset`、`IntegratedDataset`、`PopulationDataset` |
| [rf](rf/README.md) | 历史 STA、当前 RF 估计、FDR、中心与对齐 | 08、Phase 6.1 | `characterize_halves`、`align_kernels` |
| [models](models/README.md) | 独立、共享、分层、低秩、历史 CNN 预测 | 09–10 | 各 `fit_*` |
| [evaluation](evaluation/README.md) | 每 ROI/每 fly 指标、可靠性诊断与比较 | 08、11 | `score_columns`、`assess_training_reliability` |
| [experiments](experiments/README.md) | 历史模型矩阵、Stage 调度与当前 Phase 6.1 编排 | 09–12、Phase 6.1 | `run_first_round`、`run_phase6` |
| [io](io/README.md) | JSON/CSV 保存与有哈希的 Stage receipt | 全阶段 | `write_stage_manifest` |
| [cli](cli/README.md) | 用户命令入口，保持旧命令可用 | 全阶段 | `dm8-model pipeline`、`dataset`、`fit` |

每个一级模块 README 描述目的、shape、单位、核心函数、上下游、参数、测试和局限。[MODULE_DEPENDENCY_MAP](MODULE_DEPENDENCY_MAP.md) 给出真实依赖方向。`model.py`、`ridge.py`、`pixel.py`、`cnn.py`、`splits.py`、`pipeline.py`、`audit.py` 是被历史脚本或测试使用的短兼容层；新代码直接导入对应模块。`workspace` 同名 package 已提供公共入口，不再需要额外的 `workspace.py`。

五只 fly 只有一条独立冻结刺激序列；`Results.csv` 为原始 ROI 平均强度。源码设计允许增加新表征或模型，但当前共享模型未达到继续增加复杂度的证据标准。
