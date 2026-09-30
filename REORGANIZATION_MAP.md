# 项目结构变化记录

早期重构将混合 loader、特征、预测器、评价器拆入 `data/`、`features/`、`models/`、`evaluation/` 等模块。Phase 6.2 前，在固定[历史预测结论](docs/HISTORICAL_MODELING_CONCLUSIONS.md)后，旧预测 `models/`、`evaluation/`、`cli/`、兼容 wrapper、Stage 08–12 及只供它们使用的测试/脚本已退役；旧路径可从 Git commit `ba07516` 查到，当前安装不提供旧重播命令。

当前规范路径是：`data/` 读取实验事实 → `preprocessing/` 固定响应 → `features/` 构造过去刺激 → `rf/` 估计、对齐、聚合 → `experiments/phase62.py` 编排 → `io/` 保存结果。Stage 01–07 的来源/数据链与 Phase 6.1/6.1b RF 审计保留。完整文件清理与结果保全见[清理记录](docs/PHASE6_2_CLEANUP_LOG.md)，当前布局见[项目结构](PROJECT_STRUCTURE.md)。
