# 活动源码地图

| 模块 | 当前职责 |
|---|---|
| `workspace/` | 工作区定位、来源清单与哈希 |
| `data/` | 只读加载数字刺激、ROI 表、时钟并对齐 |
| `preprocessing/` | raw 与 Li-style 离线 RF 响应；保留旧数据链需用的因果表示 |
| `features/` | 从当前及过去数字刺激构造滞后/分箱特征 |
| `datasets/` | Stage 06–07 的单 fly/整合来源对象 |
| `rf/` | Phase 6.1 严格 RF 诊断与 Phase 6.2 掩码对齐、群体/径向统计 |
| `experiments/` | 阶段配置、调度、全数据 Phase 6.2 编排 |
| `io/` | CSV/JSON/NPZ 相关输出及哈希 manifest |

当前运行入口为 [`modeling_pipeline/phase_06/run_population.py`](../../modeling_pipeline/phase_06/run_population.py)。模块依赖见 [MODULE_DEPENDENCY_MAP](MODULE_DEPENDENCY_MAP.md)；科学方法及数值见 [Phase 6.2 报告](../../docs/PHASE6_2_POPULATION_RF.md)。旧预测模型、评价器、CLI 及兼容 wrapper 已在固定历史结论后退役。
