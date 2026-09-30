# Phase 6.2 前的历史预测资源清理记录

本轮先固定 [`HISTORICAL_MODELING_CONCLUSIONS.md`](HISTORICAL_MODELING_CONCLUSIONS.md) 和 [`HISTORICAL_MODELING_RESULTS.csv`](HISTORICAL_MODELING_RESULTS.csv)，再清理实现。保留 Phase 1–6.1b 报告、关键数值、原始来源哈希、当前 RF 管线，以及 Git 历史。`docs/historical_evidence/` 另存了 Pixel/CNN/Phase 5 的关键图和精简数值证据。退役代码可从清理前 Git commit `ba07516` 追溯，但当前安装不会再提供旧预测命令。

## 删除范围和理由

| 区域 | 删除内容 | 理由与保留下来的证据 |
|---|---|---|
| `src/dm8_modeling/models/` | Pixel、Ridge、CNN、共享、分层、低秩、群体预测实现 | 已完成比较，群体 held-out 表现未稳定改善；结论、报告、关键图及 Git 历史保留。 |
| `src/dm8_modeling/cli/` 和根级兼容文件 | 历史预测 CLI、入口、replay wrapper | 只服务于已退役训练/预测，不再作为项目当前入口。 |
| `src/dm8_modeling/evaluation/`、部分 `experiments/`、`datasets/`、`rf/sta.py` | 旧预测评分、模型矩阵、迁移训练、PopulationDataset 与预测型 STA | 当前的对齐、预处理、RF 表征、manifest 不依赖这些模块。 |
| `modeling_pipeline/stage_08_*` 至 `stage_12_*` | 历史预测阶段的 runner 与说明 | Stage 01–07 仍是有效来源/数据链；旧 08–12 结论保留在报告与历史表。 |
| `tests/models/`、`tests/evaluation/`、`tests/integration/`、旧 `tests/rf/test_rf.py` | 仅验证退役实现的测试 | 当前 Stage 01–07、Phase 6.1/6.1b 和新增 Phase 6.2 的测试保留。 |
| `scripts/` 中的旧审计/比较脚本 | 旧预测检查、偏移探索、CNN/Pixel 验证入口 | 保留 `verify_stimulus_provenance.py` 作为独立来源核验。 |
| 被 Git 忽略的旧 `outputs/` | 17 个历史预测/探索目录，795 个文件，总计 124,614,202 字节（约 118.84 MiB），包括旧 checkpoint、weights、缓存与失败 sweep | 删除前已将必要图/数值复制进 `docs/historical_evidence/`；原报告和 Git 历史仍在。未清理 Stage 01–07 与 Phase 6.1/6.1b 的结果。 |

共从 Git 索引删除 **77 个已跟踪文件**。清理前 `src/`、`tests/`、`scripts/`、`modeling_pipeline/` 共有 **162 个**已跟踪文件；本轮新增 Phase 6.2 的入口、实现和测试等 4 个活动文件后为 **89 个**，净减少 **73 个**。剩余 **8 个测试文件、23 个通过的测试用例**；新增 1 个 Phase 6.2 测试文件。原预测代码及模型权重没有重新加入。

仍可运行的链：源文件清单与 SHA-256、数字刺激复核、时钟/帧对齐、ROI 原始强度载入、响应变换、Stage 01–07 数据处理、Phase 6.1/6.1b RF 审计、Phase 6.2 描述性群体 RF。`matplotlib` 是本轮唯一新增运行依赖，用于固定图 1–5 与补图；不再需要旧 CNN 可选 `torch` 依赖。

## 原始数据完整性

清理和 RF 代码只**读取** `Dm8_module/`、`simulate/`，没有主动编辑原始实验数据。会话初始记录 `Dm8_module/` 536 个文件的 SHA-256。结束时 532 个非 `.DS_Store` 实验/来源文件与初始哈希**逐字节一致**。四个 Finder `.DS_Store` 元数据文件中有一个的哈希发生变化（`Dm8_module/.DS_Store`，初始 `f7bd5…`，复查 `8cc93…`）；因此不能声称**整个原始目录**字节完全未变。没有尝试修改或恢复该原始目录元数据。该变化可能使包含 `.DS_Store` 的旧目录级 receipt 失效；实际科学输入文件的逐文件哈希未变。后续来源审计应把操作系统元数据与实验文件分开列示，保留这一事实而不篡改原始目录。

本轮当前分析的 `stage_manifest.json` 记录声明输入/输出的 SHA-256。输出目录被 Git 忽略，报告中的关键图及关键群体/ROI 数值表已复制到 `docs/phase6_2_figures/` 与 `docs/phase6_2_results/` 并纳入版本管理；完整数值可按 [`PHASE6_2_POPULATION_RF.md`](PHASE6_2_POPULATION_RF.md) 的命令从原始源重新生成。
