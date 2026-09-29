# 一页看懂 Dm8 工作区

```text
/Users/irin/Documents/dm8_modeling/  ← 工作区根目录，同时是分析 Git 仓库
├── simulate/07E_260530_01/    刺激工程：生成、打包、播放、设备时钟
├── Dm8_module/UV-15Hz/        五只 fly 的实验原始记录；严格只读
├── src/dm8_modeling/          分析与可解释建模 Python 包
│   ├── data/、preprocessing/、datasets/、features/  读取、响应处理与整合
│   ├── models/、evaluation/、experiments/          多 fly 建模与评价
├── configs/                   第五阶段可复算实验配置
├── scripts/、tests/、docs/     核验工具、测试与讲解
└── outputs/                   运行派生结果；Git 忽略
```

`simulate` 和 `Dm8_module` 都位于分析 Git 根目录之下，但由 `.gitignore` 排除；无需复制或嵌套移动。`simulate` 的原始工程行为不由分析仓库修改；`Dm8_module` 的 536 个原文件也不修改。详细目录审计在 [WORKSPACE_AUDIT](WORKSPACE_AUDIT.md)，每个实验文件的逐条信息在本机 `outputs/audit/data_inventory.json`。

```text
simulate 中的配方与生成器
  → 冻结刺激 NPZ → PsychoPy 数字播放 → DLP TTL / marker lock
  → Dm8_module 实验包 + Zeiss TTL + Results.csv
  → data.align_session：成像帧匹配最近的过去刺激更新
  → pipeline.build_model_dataset：过去 lag 个更新组成 X，ROI 均值组成 y
  → STA / Ridge / 像素时域模型与留后时段验证
  → 五 fly 公共刺激特征表 + 带来源索引的整合数据
  → 全局时间切分 + 独立/共享/分层/低秩/群体模型比较
```

**先读：** [刺激代码审计](STIMULUS_CODE_AUDIT.md) → [刺激来源核验](STIMULUS_PROVENANCE.md) → [数据处理逐步讲解](DATA_PIPELINE_WALKTHROUGH.md) → [数据质量和缺口](DATA_AUDIT_REPORT.md) → [重构前后回归](BASELINE_REGRESSION.md)。此前 [完整建模报告](DM8_MODELING_FINAL_REPORT.md) 保留历史模型结论；其关于刺激工程位置的旧表述以本次现场审计为准。

第五阶段请接着读 [整合数据集](INTEGRATED_DATASET.md) → [多 fly 模型](POPULATION_MODELING.md) → [最终预测报告](FINAL_PREDICTIVE_MODEL_REPORT.md)。旧模型入口仍可用；`dm8-model dataset|fit|evaluate` 是新增的统一入口。新实验结果位于本机 Git 忽略的 `outputs/experiments/phase5_first_round/`。
