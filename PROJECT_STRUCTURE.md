# 项目结构与阅读路线

```text
simulate/                 刺激设计/播放源码，只读来源
Dm8_module/               五次实验的保存刺激、ROI 表与时钟，只读来源
configs/                  冻结的 RF 与工作流参数
src/dm8_modeling/          读取、对齐、预处理、RF 与输出实现
modeling_pipeline/         Stage 01–07 来源链与 Phase 6 工作入口
tests/                     当前数据链与 RF 单元检查
docs/                      科学报告、历史结论、关键图
outputs/                   可复算的本地派生数据，Git 忽略
```

当前科学主线：

```text
原始实验及保存的数字刺激
    ↓
来源核验 → DLP/Zeiss 时间对应 → ROI 平均强度
    ↓
Li-style 离线响应（raw 诊断）
    ↓
每 ROI 粗时间 RF → 白噪声导出的中心 → 无环绕对齐
    ↓
每 fly 等权 ROI 平均 → 五 fly 等权群体平均
    ↓
径向曲线、留一 fly 检查 → 生物学解释及限制
```

| 位置 | 当前用途 |
|---|---|
| [`modeling_pipeline/stage_01_source_audit/`](modeling_pipeline/stage_01_source_audit/) 至 [`stage_07_integrated_dataset/`](modeling_pipeline/stage_07_integrated_dataset/) | 来源/数据构建的历史可运行阶段；其预测导向 Stage 08–12 已退役。 |
| [`modeling_pipeline/phase_06/`](modeling_pipeline/phase_06/) | Phase 6.1 严格 RF、6.1b 方法审计、6.2 全数据描述性 RF、6.3 各 fly 验证的独立入口。 |
| [`src/dm8_modeling/data/`](src/dm8_modeling/data/) | 保存刺激、ROI 和设备时钟的只读读取及对齐。 |
| [`src/dm8_modeling/preprocessing/`](src/dm8_modeling/preprocessing/) | 原始及 Li-style 离线响应表示。 |
| [`src/dm8_modeling/rf/`](src/dm8_modeling/rf/) | 反向相关、中心估计、掩码对齐、群体/径向汇总。 |
| [`src/dm8_modeling/experiments/`](src/dm8_modeling/experiments/) | 阶段编排、配置、结果及 manifest。 |
| [`docs/PHASE6_2_POPULATION_RF.md`](docs/PHASE6_2_POPULATION_RF.md) | 基础描述性方法、科学结论与图 1–5。 |
| [`docs/PHASE6_3_FLY_POPULATION_VALIDATION.md`](docs/PHASE6_3_FLY_POPULATION_VALIDATION.md) | 最新各 fly、时间箱、完整 null、共性/异质性报告；完成本阶段后停止。 |
| [`docs/HISTORICAL_MODELING_CONCLUSIONS.md`](docs/HISTORICAL_MODELING_CONCLUSIONS.md) | 预测模型的已固定数值结论与停止理由。 |

五只 fly 是生物学重复；236 ROI 是 fly 内测量。五次实验共享一条数字刺激，不能声称五条独立刺激。旧文档中的预测命令和路径属于历史记录，当前安装不再提供已退役模型代码。[清理记录](docs/PHASE6_2_CLEANUP_LOG.md)列出删除与保留的具体范围。
